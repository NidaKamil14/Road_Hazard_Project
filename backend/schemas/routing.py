from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class Coordinates(BaseModel):
    """WGS84 geographic coordinates."""
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees [-90 to 90]")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees [-180 to 180]")


class RouteRequest(BaseModel):
    """Request payload for hazard-aware route recommendation."""
    origin: Coordinates = Field(..., description="Starting point coordinates")
    destination: Coordinates = Field(..., description="Destination point coordinates")
    hazard_radius_meters: float = Field(
        default=50.0,
        ge=10.0,
        le=500.0,
        description="Search buffer radius around the route line in meters [10.0 - 500.0]",
    )
    safety_weight: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description=(
            "Balance between distance (0.0 = shortest route) and safety (1.0 = safest route). "
            "Default 0.7 strongly prioritizes safety while still considering distance."
        ),
    )


class GeoJSONLineString(BaseModel):
    """GeoJSON LineString format compatible with Leaflet and standard GIS tooling.
    Coordinates are formatted strictly as [longitude, latitude] pairs.
    """
    type: str = Field(default="LineString", description="GeoJSON geometry type")
    coordinates: List[List[float]] = Field(
        ...,
        description="Array of [longitude, latitude] coordinate pairs",
    )


class RouteHazardDetail(BaseModel):
    """Details of a specific road hazard located within the route's safety buffer."""
    id: int = Field(..., description="Hazard database ID")
    hazard_type: str = Field(..., description="Hazard category name (pothole, road_crack, etc.)")
    severity: str = Field(..., description="Severity tier (Low, Medium, High)")
    priority_score: float = Field(..., description="Maintenance priority score [0.0 - 100.0]")
    priority_level: str = Field(..., description="Priority level (Low, Medium, High, Critical)")
    confidence: float = Field(..., description="Detection confidence certainty [0.0 - 1.0]")
    latitude: float = Field(..., description="Hazard WGS84 latitude")
    longitude: float = Field(..., description="Hazard WGS84 longitude")
    distance_from_route: float = Field(
        ...,
        description="Perpendicular geodesic distance from the route path in meters",
    )

    model_config = ConfigDict(from_attributes=True)


class RouteItem(BaseModel):
    """Evaluated driving route with hazard risk assessment and normalized cost."""
    route_id: int = Field(..., description="Sequential candidate route index (1-based)")
    distance_km: float = Field(..., description="Total driving distance in kilometers")
    duration_minutes: float = Field(..., description="Estimated travel duration in minutes")
    hazard_count: int = Field(..., description="Total number of active hazards within safety buffer")
    critical_hazard_count: int = Field(..., description="Count of Critical priority hazards")
    high_priority_hazard_count: int = Field(..., description="Count of High priority hazards")
    hazard_risk_score: float = Field(
        ...,
        description="Aggregated proximity-decay hazard risk score for this route",
    )
    route_cost: float = Field(
        ...,
        description="Normalized combined cost balancing relative distance and relative hazard risk",
    )
    is_recommended: bool = Field(..., description="Whether this route is selected as the recommended choice")
    geometry: GeoJSONLineString = Field(..., description="GeoJSON LineString with [lon, lat] coordinate pairs")
    hazards: List[RouteHazardDetail] = Field(
        default_factory=list,
        description="List of detected hazards along this route path",
    )


class RouteRecommendationResponse(BaseModel):
    """Complete response payload for hazard-aware route recommendation."""
    success: bool = Field(default=True, description="Whether routing evaluation completed successfully")
    recommended_route: RouteItem = Field(..., description="Best candidate route minimizing combined cost")
    alternatives: List[RouteItem] = Field(
        default_factory=list,
        description="Other evaluated candidate routes, if available from OSRM",
    )
    recommendation_reason: str = Field(
        ...,
        description="Deterministic explainable reason detailing why the recommended route was selected",
    )
    safety_weight_used: float = Field(..., description="Safety weight used in the cost evaluation")
    hazard_radius_meters_used: float = Field(..., description="Hazard search radius in meters used for spatial buffering")
