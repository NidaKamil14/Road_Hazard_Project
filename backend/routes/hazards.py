from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2.elements import WKTElement
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.hazard import Hazard
from backend.schemas.detection import BoundingBox
from backend.schemas.hazard import (
    HazardCreate,
    HazardListResponse,
    HazardResponse,
    HazardStatusUpdate,
    PriorityHazardItem,
    PriorityHazardsResponse,
)
from backend.services.priority import calculate_priority_score
from backend.services.severity import calculate_severity

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
        priority_score=round(float(h.priority_score), 1) if h.priority_score is not None else 50.0,
        priority_level=h.priority_level or "Medium",
        priority_reason=h.priority_reason,
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
    """Persist a road hazard record with PostGIS spatial location, calculated severity, and priority score."""
    # 1. Severity calculation (if not explicitly provided, calculate via Severity Engine)
    if hazard_in.severity is not None:
        severity_val = hazard_in.severity.value
    else:
        severity_val, _ = calculate_severity(
            hazard_type=hazard_in.hazard_type.value,
            confidence=hazard_in.confidence,
            bounding_box=hazard_in.bounding_box,
            image_width=hazard_in.image_width,
            image_height=hazard_in.image_height,
        )

    # 2. Priority calculation (0 - 100 score, level, and explainable reason)
    p_score, p_level, p_reason = calculate_priority_score(
        hazard_type=hazard_in.hazard_type.value,
        severity=severity_val,
        confidence=hazard_in.confidence,
        latitude=hazard_in.latitude,
        longitude=hazard_in.longitude,
    )

    # 3. PostGIS geometry: POINT(longitude latitude) with SRID 4326
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
        severity=severity_val,
        priority_score=p_score,
        priority_level=p_level,
        priority_reason=p_reason,
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
    "/priority",
    response_model=PriorityHazardsResponse,
    summary="Get active hazards ordered by highest maintenance priority",
)
def get_priority_hazards(
    limit: int = Query(20, ge=1, le=100, description="Number of top-priority hazards to return"),
    status: Optional[str] = Query("active", description="Filter by status (default: active)"),
    hazard_type: Optional[str] = Query(None, description="Filter by hazard category"),
    priority_level: Optional[str] = Query(None, description="Filter by priority level (Low, Medium, High, Critical)"),
    min_priority_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Filter by minimum priority score"),
    db: Session = Depends(get_db),
):
    """Dedicated endpoint returning urgent road hazards sorted by highest maintenance priority.
    Designed specifically for Authority dispatch and municipal repair scheduling.
    """
    query = db.query(Hazard)
    if status:
        query = query.filter(Hazard.status == status.strip().lower())
    if hazard_type:
        query = query.filter(Hazard.hazard_type == hazard_type.strip().lower())
    if priority_level:
        query = query.filter(Hazard.priority_level == priority_level.strip().capitalize())
    if min_priority_score is not None:
        query = query.filter(Hazard.priority_score >= min_priority_score)

    records = query.order_by(Hazard.priority_score.desc()).limit(limit).all()

    items = [
        PriorityHazardItem(
            id=h.id,
            hazard_type=h.hazard_type,
            severity=h.severity,
            priority_score=round(float(h.priority_score), 1) if h.priority_score is not None else 50.0,
            priority_level=h.priority_level or "Medium",
            priority_reason=h.priority_reason,
            confidence=h.confidence,
            latitude=h.latitude,
            longitude=h.longitude,
            status=h.status,
            detected_at=h.detected_at,
        )
        for h in records
    ]

    return PriorityHazardsResponse(
        count=len(items),
        hazards=items,
    )


@router.get(
    "",
    response_model=HazardListResponse,
    summary="List stored hazards with optional filtering, sorting, and pagination",
)
def list_hazards(
    hazard_type: Optional[str] = Query(None, description="Filter by hazard category (pothole, road_crack, waterlogging, construction_barrier)"),
    severity: Optional[str] = Query(None, description="Filter by severity level (Low, Medium, High)"),
    priority_level: Optional[str] = Query(None, description="Filter by priority tier (Low, Medium, High, Critical)"),
    status: Optional[str] = Query(None, description="Filter by status (active, resolved)"),
    sort_by_priority: bool = Query(False, description="Sort by highest priority score first instead of newest"),
    limit: int = Query(50, ge=1, le=500, description="Maximum records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """Retrieve stored road hazards with coordinates, severity, and priority for map and table consumption."""
    query = db.query(Hazard)

    if hazard_type:
        query = query.filter(Hazard.hazard_type == hazard_type.strip().lower())
    if severity:
        query = query.filter(Hazard.severity == severity.strip().capitalize())
    if priority_level:
        query = query.filter(Hazard.priority_level == priority_level.strip().capitalize())
    if status:
        query = query.filter(Hazard.status == status.strip().lower())

    total_count = query.count()

    if sort_by_priority:
        query = query.order_by(Hazard.priority_score.desc())
    else:
        query = query.order_by(Hazard.detected_at.desc())

    records = query.offset(offset).limit(limit).all()

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
