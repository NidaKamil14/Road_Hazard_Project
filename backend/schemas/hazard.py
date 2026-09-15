from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.schemas.detection import BoundingBox


class HazardType(str, Enum):
    POTHOLE = "pothole"
    ROAD_CRACK = "road_crack"
    WATERLOGGING = "waterlogging"
    CONSTRUCTION_BARRIER = "construction_barrier"


class SeverityLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class PriorityLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class HazardStatus(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"


CLASS_ID_MAP = {
    0: HazardType.POTHOLE,
    1: HazardType.ROAD_CRACK,
    2: HazardType.WATERLOGGING,
    3: HazardType.CONSTRUCTION_BARRIER,
}
TYPE_TO_CLASS_ID = {v.value: k for k, v in CLASS_ID_MAP.items()}


class HazardBase(BaseModel):
    """Base validation attributes for a road hazard."""
    hazard_type: HazardType = Field(..., description="Hazard category name")
    class_id: int = Field(..., ge=0, le=3, description="Class ID (0: pothole, 1: road_crack, 2: waterlogging, 3: construction_barrier)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence [0.0 - 1.0]")
    severity: Optional[SeverityLevel] = Field(default=None, description="Hazard severity. If omitted, calculated automatically by the Severity Engine.")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 latitude coordinate")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 longitude coordinate")
    image_path: Optional[str] = Field(None, description="Path or URL to original image")
    annotated_image_path: Optional[str] = Field(None, description="Path or URL to annotated detection image")
    bounding_box: Optional[BoundingBox] = Field(None, description="Bounding box pixel coordinates")
    image_width: Optional[int] = Field(None, ge=1, description="Source image width")
    image_height: Optional[int] = Field(None, ge=1, description="Source image height")
    status: HazardStatus = Field(default=HazardStatus.ACTIVE, description="Lifecycle status")

    @model_validator(mode="after")
    def validate_class_consistency(self):
        expected_type = CLASS_ID_MAP.get(self.class_id)
        if expected_type and self.hazard_type != expected_type:
            raise ValueError(
                f"Mismatch between class_id ({self.class_id}) and hazard_type ('{self.hazard_type.value}'). "
                f"Expected '{expected_type.value}'."
            )
        return self


class HazardCreate(HazardBase):
    """Input payload to record a new road hazard."""
    pass


class HazardStatusUpdate(BaseModel):
    """Payload to update hazard workflow status."""
    status: HazardStatus = Field(..., description="New hazard lifecycle status ('active' or 'resolved')")


class HazardResponse(BaseModel):
    """Clean representation of a stored road hazard for Leaflet/React consumption."""
    id: int
    hazard_type: str
    class_id: int
    confidence: float
    severity: str
    priority_score: float = Field(..., description="Calculated maintenance priority score [0.0 - 100.0]")
    priority_level: str = Field(..., description="Priority tier: Low, Medium, High, Critical")
    priority_reason: Optional[str] = Field(None, description="Deterministic, explainable justification for the priority score")
    latitude: float
    longitude: float
    image_path: Optional[str] = None
    annotated_image_path: Optional[str] = None
    bounding_box: Optional[BoundingBox] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    detected_at: datetime
    status: str

    model_config = ConfigDict(from_attributes=True)


class HazardListResponse(BaseModel):
    """Paginated collection of road hazard records."""
    total: int
    limit: int
    offset: int
    hazards: List[HazardResponse]


class PriorityHazardItem(BaseModel):
    """Summary item optimized for the Authority maintenance dashboard."""
    id: int
    hazard_type: str
    severity: str
    priority_score: float
    priority_level: str
    priority_reason: Optional[str] = None
    confidence: float
    latitude: float
    longitude: float
    status: str
    detected_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PriorityHazardsResponse(BaseModel):
    """Dedicated response for high-priority road hazards."""
    count: int
    hazards: List[PriorityHazardItem]
