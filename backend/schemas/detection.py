from typing import List, Optional
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Bounding box coordinates in absolute pixel units."""
    x1: float = Field(..., description="Top-left X coordinate in pixels")
    y1: float = Field(..., description="Top-left Y coordinate in pixels")
    x2: float = Field(..., description="Bottom-right X coordinate in pixels")
    y2: float = Field(..., description="Bottom-right Y coordinate in pixels")


class DetectionItem(BaseModel):
    """Single detected road hazard object."""
    class_id: int = Field(..., description="Class identifier (0: pothole, 1: road_crack, 2: waterlogging, 3: construction_barrier)")
    class_name: str = Field(..., description="Human-readable hazard class name")
    confidence: float = Field(..., description="Detection confidence score [0.0 - 1.0]")
    bounding_box: BoundingBox = Field(..., description="Bounding box coordinates")


class DetectionResponse(BaseModel):
    """Full detection response for an uploaded image."""
    success: bool = Field(..., description="Whether inference completed successfully")
    total_detections: int = Field(..., description="Total number of hazards detected above confidence threshold")
    inference_time_ms: float = Field(..., description="YOLO model forward-pass time in milliseconds")
    image_width: int = Field(..., description="Original image width in pixels")
    image_height: int = Field(..., description="Original image height in pixels")
    annotated_image_url: Optional[str] = Field(None, description="URL or relative path to the generated annotated image")
    detections: List[DetectionItem] = Field(default_factory=list, description="List of detected hazard items")


class HealthResponse(BaseModel):
    """System health check and loaded model metadata."""
    status: str = Field(..., description="Health status (e.g. 'ok')")
    model: str = Field(..., description="Model architecture descriptor")
    model_path: str = Field(..., description="File path to the loaded model checkpoint")
    device: str = Field(..., description="Execution compute device (cuda / cpu)")
    classes: List[str] = Field(..., description="Active hazard class ontology names")
    database: Optional[str] = Field("disconnected", description="Database connection status ('connected' or 'disconnected')")
