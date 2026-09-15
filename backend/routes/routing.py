"""
Hazard-Aware Routing API Endpoints.
Provides route recommendations that balance travel distance with road hazard avoidance.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.routing import (
    RouteItem,
    RouteRecommendationResponse,
    RouteRequest,
)
from backend.services.hazard_analyzer import (
    compute_normalized_costs_and_rank,
    evaluate_single_route,
    query_hazards_near_route,
)
from backend.services.routing import (
    OSRMError,
    OSRMNoRouteFoundError,
    OSRMRoute,
    OSRMServiceUnavailableError,
    RoutingService,
)

router = APIRouter(tags=["Routing"])
routing_service = RoutingService()


@router.post(
    "/recommend",
    response_model=RouteRecommendationResponse,
    summary="Recommend safest driving route considering road hazards",
    status_code=status.HTTP_200_OK,
)
def recommend_route(
    payload: RouteRequest,
    db: Session = Depends(get_db),
):
    """Obtain driving routes between origin and destination, query active road hazards
    within the configured buffer radius using PostGIS, and recommend the best route
    balancing travel distance and hazard risk.
    """
    # 1. Query candidate routes from OSRM
    try:
        candidate_osrm_routes: List[OSRMRoute] = routing_service.get_candidate_routes(
            origin_lon=payload.origin.longitude,
            origin_lat=payload.origin.latitude,
            destination_lon=payload.destination.longitude,
            destination_lat=payload.destination.latitude,
        )
    except OSRMServiceUnavailableError as err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Routing service is temporarily unavailable: {err}",
        )
    except OSRMNoRouteFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        )
    except OSRMError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch candidate routes: {str(err)}",
        )

    # 2. For each candidate route, perform PostGIS spatial search and evaluate hazard risk
    evaluated_routes = []
    for idx, osrm_route in enumerate(candidate_osrm_routes, start=1):
        try:
            hazards = query_hazards_near_route(
                route_geometry=osrm_route.geometry,
                radius_meters=payload.hazard_radius_meters,
                db=db,
            )
            evaluated = evaluate_single_route(
                route_id=idx,
                osrm_route=osrm_route,
                hazards=hazards,
                radius_meters=payload.hazard_radius_meters,
            )
            evaluated_routes.append(evaluated)
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Spatial analysis failed on candidate route {idx}: {str(err)}",
            )

    # 3. Compute normalized costs, rank routes, and generate explainable reason
    ranked_route_items, reason = compute_normalized_costs_and_rank(
        evaluated_routes=evaluated_routes,
        safety_weight=payload.safety_weight,
    )

    recommended_route = next(r for r in ranked_route_items if r.is_recommended)
    alternatives = [r for r in ranked_route_items if not r.is_recommended]

    return RouteRecommendationResponse(
        success=True,
        recommended_route=recommended_route,
        alternatives=alternatives,
        recommendation_reason=reason,
        safety_weight_used=payload.safety_weight,
        hazard_radius_meters_used=payload.hazard_radius_meters,
    )
