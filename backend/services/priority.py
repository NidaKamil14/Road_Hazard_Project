"""
Road Hazard Maintenance Priority Scoring Engine.
Modular, explainable calculation of municipal road maintenance priority.
Combines severity, hazard type, and detection confidence into a 0-100 score,
priority level (Low, Medium, High, Critical), and deterministic priority reason.

NOTE: These weights are an initial engineering model, NOT ML-learned weights.
"""

from typing import Optional, Tuple, Union

# Component weights (Sum to 1.00)
WEIGHT_SEVERITY = 0.50
WEIGHT_HAZARD_TYPE = 0.30
WEIGHT_CONFIDENCE = 0.20

# Severity score multipliers
SEVERITY_WEIGHTS = {
    "low": 0.33,
    "medium": 0.66,
    "high": 1.00
}

# Hazard type weights reflecting public safety & mobility disruption
HAZARD_TYPE_WEIGHTS = {
    "waterlogging": 1.00,        # Complete road impassability / acute flooding
    "pothole": 0.80,             # Direct mechanical vehicle impact / accident hazard
    "construction_barrier": 0.70,# Active workzone lane constriction
    "road_crack": 0.60           # Progressive degradation / medium-term maintenance
}

# Priority Level Thresholds (0 - 100 scale)
PRIORITY_LEVEL_LOW_MAX = 25.0
PRIORITY_LEVEL_MEDIUM_MAX = 50.0
PRIORITY_LEVEL_HIGH_MAX = 75.0


def calculate_priority_score(
    hazard_type: str,
    severity: str,
    confidence: float,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
) -> Tuple[float, str, str]:
    """Calculate maintenance priority score (0-100), level, and explainable reason.

    Formula:
        priority_score = (
            0.50 * severity_component
            + 0.30 * hazard_type_component
            + 0.20 * confidence
        ) * 100

    Thresholds:
        0.0  - 24.9 -> Low
        25.0 - 49.9 -> Medium
        50.0 - 74.9 -> High
        75.0 - 100.0 -> Critical

    Returns:
        Tuple[float, str, str]: (priority_score, priority_level, priority_reason)
    """
    clean_type = str(hazard_type).strip().lower()
    clean_sev = str(severity).strip().lower()

    # Component lookups
    sev_comp = SEVERITY_WEIGHTS.get(clean_sev, 0.66)
    type_comp = HAZARD_TYPE_WEIGHTS.get(clean_type, 0.70)
    safe_conf = max(0.0, min(1.0, float(confidence) if confidence is not None else 0.5))

    # Calculate 0-100 score
    raw_score = (
        WEIGHT_SEVERITY * sev_comp
        + WEIGHT_HAZARD_TYPE * type_comp
        + WEIGHT_CONFIDENCE * safe_conf
    ) * 100.0

    score = max(0.0, min(100.0, raw_score))
    rounded_score = round(score, 1)

    # Classify priority level
    if rounded_score < PRIORITY_LEVEL_LOW_MAX:
        level = "Low"
    elif rounded_score < PRIORITY_LEVEL_MEDIUM_MAX:
        level = "Medium"
    elif rounded_score < PRIORITY_LEVEL_HIGH_MAX:
        level = "High"
    else:
        level = "Critical"

    # Generate deterministic, explainable priority reason
    conf_desc = "high" if safe_conf >= 0.75 else ("moderate" if safe_conf >= 0.40 else "low")
    formatted_type = clean_type.replace("_", " ")
    formatted_sev = clean_sev.capitalize()

    if level == "Critical":
        reason = f"Critical priority: {formatted_sev} severity {formatted_type} with {conf_desc} detection certainty ({safe_conf:.2f})."
    elif level == "High":
        reason = f"High priority: {formatted_sev} severity {formatted_type} requiring prompt maintenance intervention."
    elif level == "Medium":
        reason = f"Medium priority: {formatted_sev} severity {formatted_type} scheduled for standard road monitoring."
    else:
        reason = f"Low priority: Minor {formatted_sev} severity {formatted_type} with {conf_desc} confidence."

    return rounded_score, level, reason


def compute_priority_score(severity: Union[str, None]) -> int:
    """Legacy backward-compatible helper returning an integer tier [1, 2, 3]."""
    if not severity:
        return 2
    normalized = str(severity).strip().capitalize()
    mapping = {"Low": 1, "Medium": 2, "High": 3}
    return mapping.get(normalized, 2)
