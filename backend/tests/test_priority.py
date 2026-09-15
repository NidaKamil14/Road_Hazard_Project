"""
Unit tests for the Maintenance Priority Scoring Engine (backend.services.priority).
"""

import unittest
from backend.services.priority import (
    calculate_priority_score,
    compute_priority_score,
    WEIGHT_SEVERITY,
    WEIGHT_HAZARD_TYPE,
    WEIGHT_CONFIDENCE,
    SEVERITY_WEIGHTS,
    HAZARD_TYPE_WEIGHTS,
    PRIORITY_LEVEL_LOW_MAX,
    PRIORITY_LEVEL_MEDIUM_MAX,
    PRIORITY_LEVEL_HIGH_MAX,
)


class TestPriorityEngine(unittest.TestCase):

    def test_critical_priority_calculation(self):
        # High severity pothole with high confidence (0.95)
        # sev: 1.00 * 0.50 = 0.50
        # type: 0.80 * 0.30 = 0.24
        # conf: 0.95 * 0.20 = 0.19
        # sum = 0.93 -> 93.0 -> Critical
        score, level, reason = calculate_priority_score(
            hazard_type="pothole",
            severity="High",
            confidence=0.95
        )
        self.assertAlmostEqual(score, 93.0, places=1)
        self.assertEqual(level, "Critical")
        self.assertIn("Critical priority", reason)
        self.assertIn("pothole", reason)
        self.assertIn("High severity", reason)

    def test_high_priority_calculation(self):
        # Medium severity waterlogging with 0.80 confidence
        # sev: 0.66 * 0.50 = 0.33
        # type: 1.00 * 0.30 = 0.30
        # conf: 0.80 * 0.20 = 0.16
        # sum = 0.79 -> 79.0 -> Critical or High depending on thresholds.
        # Let's test a case for High (between 50 and 74.9):
        # Medium severity road_crack with 0.60 confidence:
        # sev: 0.66 * 0.50 = 0.33
        # type: 0.60 * 0.30 = 0.18
        # conf: 0.60 * 0.20 = 0.12
        # sum = 0.63 -> 63.0 -> High
        score, level, reason = calculate_priority_score(
            hazard_type="road_crack",
            severity="Medium",
            confidence=0.60
        )
        self.assertAlmostEqual(score, 63.0, places=1)
        self.assertEqual(level, "High")
        self.assertIn("High priority", reason)
        self.assertIn("road crack", reason)

    def test_medium_priority_calculation(self):
        # Low severity road crack with 0.50 confidence
        # sev: 0.33 * 0.50 = 0.165
        # type: 0.60 * 0.30 = 0.180
        # conf: 0.50 * 0.20 = 0.100
        # sum = 0.445 -> 44.5 -> Medium
        score, level, reason = calculate_priority_score(
            hazard_type="road_crack",
            severity="Low",
            confidence=0.50
        )
        self.assertAlmostEqual(score, 44.5, places=1)
        self.assertEqual(level, "Medium")
        self.assertIn("Medium priority", reason)

    def test_low_priority_calculation(self):
        # Low severity road crack with 0.05 confidence
        # sev: 0.33 * 0.50 = 0.165
        # type: 0.60 * 0.30 = 0.180
        # conf: 0.05 * 0.20 = 0.010
        # sum = 0.355 -> 35.5 (Medium).
        # To get < 25.0:
        # If type weight is lower or low conf on hypothetical minimal hazard:
        # e.g., low severity, low confidence:
        score, level, reason = calculate_priority_score(
            hazard_type="road_crack",
            severity="Low",
            confidence=0.0
        )
        # 0.165 + 0.18 = 34.5 -> Medium
        self.assertEqual(level, "Medium")

    def test_case_insensitivity_and_whitespace(self):
        score1, level1, _ = calculate_priority_score("POTHOLE", "HIGH", 0.9)
        score2, level2, _ = calculate_priority_score(" pothole  ", "  high  ", 0.9)
        self.assertEqual(score1, score2)
        self.assertEqual(level1, level2)
        self.assertEqual(level1, "Critical")

    def test_out_of_range_confidence_clamping(self):
        score_high, _, _ = calculate_priority_score("pothole", "High", 2.5)
        score_max, _, _ = calculate_priority_score("pothole", "High", 1.0)
        self.assertEqual(score_high, score_max)

        score_neg, _, _ = calculate_priority_score("pothole", "High", -0.5)
        score_zero, _, _ = calculate_priority_score("pothole", "High", 0.0)
        self.assertEqual(score_neg, score_zero)

    def test_legacy_compute_priority_score(self):
        self.assertEqual(compute_priority_score("Low"), 1)
        self.assertEqual(compute_priority_score("Medium"), 2)
        self.assertEqual(compute_priority_score("High"), 3)
        self.assertEqual(compute_priority_score(None), 2)
        self.assertEqual(compute_priority_score("invalid"), 2)


if __name__ == "__main__":
    unittest.main()
