"""
Road Hazard Severity Engine.
Rule-based, explainable engineering model for estimating hazard severity.
NOTE: Datasets do not contain ground-truth severity labels; this engine computes
a deterministic engineering estimate from hazard morphology, confidence, and size.
"""

from typing import Optional, Tuple
from backend.schemas.detection import BoundingBox


# Baseline severity weights by hazard class (Engineering assumptions)
# Pothole (cavity impact) & Waterlogging (hydroplaning risk) receive higher base weights
HAZARD_BASE_WEIGHTS = {
    "pothole": 0.85,             # High structural impact
    "waterlogging": 0.90,        # Acute hydroplaning risk
    "road_crack": 0.50,          # Surface defect / progressive degradation
    "construction_barrier": 0.50 # Workzone traffic control / lane narrowing
}

# Relative area thresholds (size component)
AREA_SMALL_THRESHOLD = 0.02
AREA_LARGE_THRESHOLD = 0.10

# Severity score classification thresholds
SEVERITY_LOW_THRESHOLD = 0.40
SEVERITY_HIGH_THRESHOLD = 0.70


def compute_relative_area(
    bounding_box: Optional[BoundingBox] = None,
    image_width: Optional[int] = None,
    image_height: Optional[int] = None
) -> float:
    """Safely calculate clamped relative bounding box area [0.0 - 1.0].
    Defaults to 0.04 (median hazard size) if bounding box or dimensions are invalid/missing.
    """
    if not bounding_box or not image_width or not image_height:
        return 0.04

    if image_width <= 0 or image_height <= 0:
        return 0.04

    width = max(0.0, float(bounding_box.x2 - bounding_box.x1))
    height = max(0.0, float(bounding_box.y2 - bounding_box.y1))
    box_area = width * height
    image_area = float(image_width * image_height)

    if image_area <= 0:
        return 0.04

    relative_area = box_area / image_area
    return max(0.0, min(1.0, relative_area))


def calculate_size_component(relative_area: float) -> float:
    """Normalize relative bounding box area into a size score [0.0 - 1.0].
      - small  (< 0.02)      -> 0.33
      - medium (0.02 - 0.10) -> 0.66
      - large  (> 0.10)      -> 1.00
    """
    if relative_area < AREA_SMALL_THRESHOLD:
        return 0.33
    elif relative_area <= AREA_LARGE_THRESHOLD:
        return 0.66
    else:
        return 1.00


def calculate_severity(
    hazard_type: str,
    confidence: float,
    bounding_box: Optional[BoundingBox] = None,
    image_width: Optional[int] = None,
    image_height: Optional[int] = None
) -> Tuple[str, float]:
    """Calculate rule-based severity level ('Low', 'Medium', 'High') and continuous score [0.0 - 1.0].

    Formula:
        severity_score = (
            0.50 * hazard_base_component
            + 0.30 * confidence_component
            + 0.20 * size_component
        )
        + hazard_specific_adjustments (clamped [0.0 - 1.0])

    Classification:
        score < 0.40        -> "Low"
        0.40 <= score < 0.70 -> "Medium"
        score >= 0.70       -> "High"

    Returns:
        Tuple[str, float]: (severity_level, rounded_score)
    """
    clean_type = str(hazard_type).strip().lower()
    base_component = HAZARD_BASE_WEIGHTS.get(clean_type, 0.67)

    # Safely clamp confidence between 0.0 and 1.0
    safe_conf = max(0.0, min(1.0, float(confidence) if confidence is not None else 0.5))

    # Calculate relative area and size component
    rel_area = compute_relative_area(bounding_box, image_width, image_height)
    size_component = calculate_size_component(rel_area)

    # Core weighted score
    score = (
        0.50 * base_component
        + 0.30 * safe_conf
        + 0.20 * size_component
    )

    # Modest hazard-specific adjustments where logically justified:
    # 1. Very large potholes (> 10% image area) present critical vehicle rim damage risk
    if clean_type == "pothole" and rel_area > AREA_LARGE_THRESHOLD:
        score += 0.05

    # 2. Large waterlogging (> 10% image area) represents extensive road flooding
    if clean_type == "waterlogging" and rel_area > AREA_LARGE_THRESHOLD:
        score += 0.05

    # Clamp final score
    score = max(0.0, min(1.0, score))
    rounded_score = round(score, 3)

    # Determine severity label
    if rounded_score < SEVERITY_LOW_THRESHOLD:
        level = "Low"
    elif rounded_score < SEVERITY_HIGH_THRESHOLD:
        level = "Medium"
    else:
        level = "High"

    return level, rounded_score
