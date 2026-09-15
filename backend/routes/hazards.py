from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2.elements import WKTElement
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.hazard import Hazard
from backend.schemas.detection import BoundingBox
from backend.schemas.hazard import (
    HazardCreate,
    HazardListResponse,
    HazardResponse,
    HazardStatusUpdate,
)
from backend.services.priority import compute_priority_score

router = APIRouter(prefix="", tags=["Hazards"])


def _hazard_to_response(h: Hazard) -> HazardResponse:
    """Convert an internal SQLAlchemy Hazard model instance into a clean Pydantic HazardResponse."""
    bbox = None
    if h.x1 is not None and h.y1 is not None and h.x2 is not None and h.y2 is not None:
        bbox = BoundingBox(x1=h.x1, y1=h.y1, x2=h.x2, y2=h.y2)

    return HazardResponse(
        id=h.id,
        hazard_type=h.hazard_type,
        class_id=h.class_id,
        confidence=h.confidence,
        severity=h.severity,
        priority_score=h.priority_score,
        latitude=h.latitude,
        longitude=h.longitude,
        image_path=h.image_path,
        annotated_image_path=h.annotated_image_path,
        bounding_box=bbox,
        image_width=h.image_width,
        image_height=h.image_height,
        detected_at=h.detected_at,
        status=h.status,
    )


@router.post(
    "",
    response_model=HazardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a new detected road hazard",
)
def create_hazard(hazard_in: HazardCreate, db: Session = Depends(get_db)):
    """Persist a road hazard record with PostGIS spatial location and priority score."""
    # Compute priority score based on severity (Low: 1, Medium: 2, High: 3)
    p_score = compute_priority_score(hazard_in.severity.value)

    # PostGIS geometry: POINT(longitude latitude) with SRID 4326
    # Strictly longitude first, latitude second
    wkt_point = f"POINT({hazard_in.longitude} {hazard_in.latitude})"
    geom_location = WKTElement(wkt_point, srid=4326)

    x1 = hazard_in.bounding_box.x1 if hazard_in.bounding_box else None
    y1 = hazard_in.bounding_box.y1 if hazard_in.bounding_box else None
    x2 = hazard_in.bounding_box.x2 if hazard_in.bounding_box else None
    y2 = hazard_in.bounding_box.y2 if hazard_in.bounding_box else None

    db_hazard = Hazard(
        hazard_type=hazard_in.hazard_type.value,
        class_id=hazard_in.class_id,
        confidence=hazard_in.confidence,
        severity=hazard_in.severity.value,
        priority_score=p_score,
        latitude=hazard_in.latitude,
        longitude=hazard_in.longitude,
        location=geom_location,
        image_path=hazard_in.image_path,
        annotated_image_path=hazard_in.annotated_image_path,
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
        image_width=hazard_in.image_width,
        image_height=hazard_in.image_height,
        status=hazard_in.status.value,
    )

    try:
        db.add(db_hazard)
        db.commit()
        db.refresh(db_hazard)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist hazard in database: {str(e)}",
        )

    return _hazard_to_response(db_hazard)


@router.get(
    "",
    response_model=HazardListResponse,
    summary="List stored hazards with optional filtering and pagination",
)
def list_hazards(
    hazard_type: Optional[str] = Query(None, description="Filter by hazard category (pothole, road_crack, waterlogging, construction_barrier)"),
    severity: Optional[str] = Query(None, description="Filter by severity level (Low, Medium, High)"),
    status: Optional[str] = Query(None, description="Filter by status (active, resolved)"),
    limit: int = Query(50, ge=1, le=500, description="Maximum records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """Retrieve stored road hazards with coordinate locations formatted for map consumption."""
    query = db.query(Hazard)

    if hazard_type:
        query = query.filter(Hazard.hazard_type == hazard_type.strip().lower())
    if severity:
        query = query.filter(Hazard.severity == severity.strip().capitalize())
    if status:
        query = query.filter(Hazard.status == status.strip().lower())

    total_count = query.count()
    records = query.order_by(Hazard.detected_at.desc()).offset(offset).limit(limit).all()

    return HazardListResponse(
        total=total_count,
        limit=limit,
        offset=offset,
        hazards=[_hazard_to_response(h) for h in records],
    )


@router.get(
    "/{hazard_id}",
    response_model=HazardResponse,
    summary="Get a single hazard by ID",
)
def get_hazard(hazard_id: int, db: Session = Depends(get_db)):
    """Retrieve a specific hazard by primary key ID."""
    hazard = db.query(Hazard).filter(Hazard.id == hazard_id).first()
    if not hazard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hazard with ID {hazard_id} not found.",
        )
    return _hazard_to_response(hazard)


@router.patch(
    "/{hazard_id}/status",
    response_model=HazardResponse,
    summary="Update hazard workflow status",
)
def update_hazard_status(
    hazard_id: int,
    status_in: HazardStatusUpdate,
    db: Session = Depends(get_db),
):
    """Update hazard status between 'active' and 'resolved'."""
    hazard = db.query(Hazard).filter(Hazard.id == hazard_id).first()
    if not hazard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hazard with ID {hazard_id} not found.",
        )

    hazard.status = status_in.status.value
    try:
        db.commit()
        db.refresh(hazard)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update hazard status: {str(e)}",
        )

    return _hazard_to_response(hazard)


@router.delete(
    "/{hazard_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a hazard record",
)
def delete_hazard(hazard_id: int, db: Session = Depends(get_db)):
    """Explicitly delete a hazard record by ID."""
    hazard = db.query(Hazard).filter(Hazard.id == hazard_id).first()
    if not hazard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hazard with ID {hazard_id} not found.",
        )

    try:
        db.delete(hazard)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete hazard record: {str(e)}",
        )

    return {
        "success": True,
        "message": f"Hazard with ID {hazard_id} deleted successfully.",
        "id": hazard_id,
    }
