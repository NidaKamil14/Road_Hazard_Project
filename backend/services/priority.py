"""
Road Hazard Priority Scoring Service.
Modular implementation to calculate maintenance priority scores.
Can be extended with multi-factor algorithms (traffic density, weather, cavity volume).
"""

from typing import Union


def compute_priority_score(severity: Union[str, None]) -> int:
    """Calculate an integer maintenance priority score from hazard severity.

    Placeholder mapping:
      - Low    -> 1
      - Medium -> 2
      - High   -> 3

    Returns:
        int: Priority score between 1 (lowest) and 3 (highest).
    """
    if not severity:
        return 2

    normalized = str(severity).strip().capitalize()
    mapping = {
        "Low": 1,
        "Medium": 2,
        "High": 3,
    }
    return mapping.get(normalized, 2)
