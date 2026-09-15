from sqlalchemy import Column, Integer, Float, String, DateTime, func
from geoalchemy2 import Geometry
from backend.database import Base


class Hazard(Base):
    """SQLAlchemy model representing a detected road hazard stored in PostgreSQL with PostGIS."""

    __tablename__ = "hazards"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    hazard_type = Column(String(50), nullable=False, index=True)
    class_id = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=False)
    severity = Column(String(20), nullable=False, default="Medium")
    
    # Priority Engine fields (0 - 100 score, level, and deterministic reason)
    priority_score = Column(Float, nullable=False, default=50.0)
    priority_level = Column(String(20), nullable=False, default="Medium", index=True)
    priority_reason = Column(String(255), nullable=True)

    # Coordinates in decimal degrees (WGS 84)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # PostGIS spatial geometry: POINT(longitude latitude) with SRID 4326
    # Note: PostGIS POINT order is strictly (longitude latitude) / (X Y)
    location = Column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=True),
        nullable=True,
    )

    # Image references and bounding box geometry
    image_path = Column(String(500), nullable=True)
    annotated_image_path = Column(String(500), nullable=True)
    x1 = Column(Float, nullable=True)
    y1 = Column(Float, nullable=True)
    x2 = Column(Float, nullable=True)
    y2 = Column(Float, nullable=True)
    image_width = Column(Integer, nullable=True)
    image_height = Column(Integer, nullable=True)

    # Metadata & workflow status
    detected_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    status = Column(String(20), nullable=False, default="active", index=True)

    def __repr__(self):
        return (
            f"<Hazard(id={self.id}, type='{self.hazard_type}', conf={self.confidence:.2f}, "
            f"severity='{self.severity}', priority={self.priority_score:.1f} ({self.priority_level}), "
            f"lat={self.latitude}, lon={self.longitude}, status='{self.status}')>"
        )
