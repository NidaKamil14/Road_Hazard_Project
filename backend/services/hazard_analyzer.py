"""
Road Hazard Route Spatial Analyzer.
Analyzes road hazards along candidate driving routes using PostGIS spatial operations,
computes proximity-decay hazard penalties, and balances distance vs. safety cost.
"""

import json
from typing import Any, Dict, List, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.schemas.routing import (
    GeoJSONLineString,
    RouteHazardDetail,
    RouteItem,
)
from backend.services.routing import OSRMRoute


def calculate_proximity_factor(distance: float, radius: float) -> float:
    """Calculate linear proximity decay factor [0.0 - 1.0].
    Hazards right on the path (distance = 0) have factor 1.0.
    Hazards at or beyond radius have factor 0.0.
    """
    if radius <= 0.0:
        return 0.0
    safe_dist = max(0.0, float(distance))
    factor = max(0.0, 1.0 - (safe_dist / float(radius)))
    return round(factor, 4)


def calculate_hazard_penalty(priority_score: float, proximity_factor: float) -> float:
    """Calculate individual hazard penalty using existing priority score and proximity factor."""
    safe_priority = max(0.0, min(100.0, float(priority_score) if priority_score is not None else 50.0))
    penalty = (safe_priority / 100.0) * proximity_factor
    return round(penalty, 4)


def query_hazards_near_route(
    route_geometry: Dict[str, Any],
    radius_meters: float,
    db: Session,
) -> List[RouteHazardDetail]:
    """Execute PostGIS spatial query finding active hazards within radius_meters of route geometry.
    Uses ST_DWithin and ST_Distance on ::geography for accurate meter-based spatial search.
    """
    geojson_str = json.dumps(route_geometry)

    query = text("""
        SELECT 
            h.id,
            h.hazard_type,
            h.severity,
            h.priority_score,
            h.priority_level,
            h.priority_reason,
            h.confidence,
            h.latitude,
            h.longitude,
            ST_Distance(
                h.location::geography,
                ST_SetSRID(ST_GeomFromGeoJSON(:route_geojson), 4326)::geography
            ) AS distance_meters
        FROM hazards h
        WHERE h.status = 'active'
          AND h.location IS NOT NULL
          AND ST_DWithin(
                h.location::geography,
                ST_SetSRID(ST_GeomFromGeoJSON(:route_geojson), 4326)::geography,
                :radius_meters
          )
        ORDER BY distance_meters ASC;
    """)

    results = db.execute(
        query,
        {
            "route_geojson": geojson_str,
            "radius_meters": float(radius_meters),
        },
    ).fetchall()

    hazard_details: List[RouteHazardDetail] = []
    for r in results:
        hazard_details.append(
            RouteHazardDetail(
                id=r.id,
                hazard_type=r.hazard_type,
                severity=r.severity,
                priority_score=round(float(r.priority_score), 1) if r.priority_score is not None else 50.0,
                priority_level=r.priority_level or "Medium",
                confidence=round(float(r.confidence), 2),
                latitude=round(float(r.latitude), 6),
                longitude=round(float(r.longitude), 6),
                distance_from_route=round(float(r.distance_meters), 1),
            )
        )

    return hazard_details


def evaluate_single_route(
    route_id: int,
    osrm_route: OSRMRoute,
    hazards: List[RouteHazardDetail],
    radius_meters: float,
) -> Dict[str, Any]:
    """Evaluate hazard metrics for a single route candidate."""
    critical_count = 0
    high_count = 0
    total_penalty = 0.0

    for h in hazards:
        # Tiers check
        if h.priority_level == "Critical" or h.priority_score >= 75.0:
            critical_count += 1
        elif h.priority_level == "High" or h.priority_score >= 50.0:
            high_count += 1

        # Proximity decay and penalty
        prox = calculate_proximity_factor(h.distance_from_route, radius_meters)
        penalty = calculate_hazard_penalty(h.priority_score, prox)
        total_penalty += penalty

    dist_km = round(osrm_route.distance_meters / 1000.0, 2)
    dur_min = round(osrm_route.duration_seconds / 60.0, 1)
    risk_score = round(total_penalty, 2)

    return {
        "route_id": route_id,
        "distance_meters": osrm_route.distance_meters,
        "distance_km": dist_km,
        "duration_minutes": dur_min,
        "hazard_count": len(hazards),
        "critical_hazard_count": critical_count,
        "high_priority_hazard_count": high_count,
        "hazard_risk_score": risk_score,
        "geometry": osrm_route.geometry,
        "hazards": hazards,
    }


def compute_normalized_costs_and_rank(
    evaluated_routes: List[Dict[str, Any]],
    safety_weight: float = 0.7,
) -> Tuple[List[RouteItem], str]:
    """Calculate normalized distance and hazard components, select the recommended route,
    and generate a deterministic explanation.

    Formula:
        distance_component = distance / max_distance
        hazard_component = hazard_risk / max_hazard_risk  (0.0 if max_hazard_risk == 0)
        route_cost = distance_component + safety_weight * hazard_component
    """
    if not evaluated_routes:
        raise ValueError("No evaluated candidate routes provided for ranking.")

    max_dist = max(r["distance_meters"] for r in evaluated_routes)
    max_risk = max(r["hazard_risk_score"] for r in evaluated_routes)

    # Compute normalized cost for each candidate
    for r in evaluated_routes:
        dist_comp = (r["distance_meters"] / max_dist) if max_dist > 0 else 1.0
        haz_comp = (r["hazard_risk_score"] / max_risk) if max_risk > 0 else 0.0

        raw_cost = dist_comp + float(safety_weight) * haz_comp
        r["route_cost"] = round(raw_cost, 3)

    # Best route is lowest cost; tie-break on lower risk, then shorter distance
    sorted_candidates = sorted(
        evaluated_routes,
        key=lambda x: (x["route_cost"], x["hazard_risk_score"], x["distance_meters"]),
    )
    recommended_id = sorted_candidates[0]["route_id"]

    # Build final RouteItem instances
    route_items: List[RouteItem] = []
    for r in evaluated_routes:
        is_rec = (r["route_id"] == recommended_id)
        route_items.append(
            RouteItem(
                route_id=r["route_id"],
                distance_km=r["distance_km"],
                duration_minutes=r["duration_minutes"],
                hazard_count=r["hazard_count"],
                critical_hazard_count=r["critical_hazard_count"],
                high_priority_hazard_count=r["high_priority_hazard_count"],
                hazard_risk_score=r["hazard_risk_score"],
                route_cost=r["route_cost"],
                is_recommended=is_rec,
                geometry=GeoJSONLineString(
                    type="LineString",
                    coordinates=r["geometry"].get("coordinates", []),
                ),
                hazards=r["hazards"],
            )
        )

    # Generate explainable recommendation reason
    rec_item = next(item for item in route_items if item.is_recommended)
    reason = generate_recommendation_reason(rec_item, route_items)

    return route_items, reason


def generate_recommendation_reason(recommended: RouteItem, all_routes: List[RouteItem]) -> str:
    """Deterministic, explainable rationale for the selected recommendation."""
    total_hazards_all = sum(r.hazard_count for r in all_routes)

    if total_hazards_all == 0:
        return "Recommended as the shortest available route because no stored hazards were found near the candidate routes."

    if len(all_routes) == 1:
        if recommended.hazard_count == 0:
            return "Recommended as the direct route with no hazards detected along the path."
        return f"Recommended as the only available drivable route ({recommended.hazard_count} hazards detected along the path)."

    shortest = min(all_routes, key=lambda x: x.distance_km)

    if recommended.route_id == shortest.route_id:
        other_alts = [r for r in all_routes if r.route_id != recommended.route_id]
        max_alt_hazards = max(r.hazard_count for r in other_alts)
        if recommended.hazard_count == 0:
            return "Recommended as both the safest and shortest route available."
        return (
            f"Recommended as the shortest route with minimal hazard risk "
            f"({recommended.hazard_count} hazard(s) vs {max_alt_hazards} in alternative)."
        )

    # Recommended route is longer than shortest route to avoid hazards
    extra_km = round(recommended.distance_km - shortest.distance_km, 1)
    if shortest.critical_hazard_count > recommended.critical_hazard_count:
        crit_diff = shortest.critical_hazard_count - recommended.critical_hazard_count
        return (
            f"Recommended for road safety to avoid {crit_diff} Critical priority hazard(s) "
            f"present along the shortest path, with an additional {extra_km} km travel distance."
        )

    return (
        f"Recommended for lower hazard risk ({recommended.hazard_count} hazard(s) "
        f"vs {shortest.hazard_count} in shortest path) despite a {extra_km} km longer travel distance."
    )
