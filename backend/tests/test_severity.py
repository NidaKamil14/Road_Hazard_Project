"""
Unit tests for the Road Hazard Severity Engine (backend.services.severity).
"""

import unittest
from backend.schemas.detection import BoundingBox
from backend.services.severity import (
    compute_relative_area,
    calculate_size_component,
    calculate_severity,
    HAZARD_BASE_WEIGHTS,
    AREA_SMALL_THRESHOLD,
    AREA_LARGE_THRESHOLD,
)


class TestSeverityEngine(unittest.TestCase):

    def test_compute_relative_area_standard(self):
        # 100x100 box in a 1000x1000 image -> 10,000 / 1,000,000 = 0.01 (1%)
        box = BoundingBox(x1=100.0, y1=100.0, x2=200.0, y2=200.0)
        rel_area = compute_relative_area(box, image_width=1000, image_height=1000)
        self.assertAlmostEqual(rel_area, 0.01, places=4)

    def test_compute_relative_area_scale_invariance(self):
        # A 10% width x 10% height box on 800x800 vs 1600x1600
        box1 = BoundingBox(x1=0.0, y1=0.0, x2=80.0, y2=80.0)
        area1 = compute_relative_area(box1, 800, 800)

        box2 = BoundingBox(x1=0.0, y1=0.0, x2=160.0, y2=160.0)
        area2 = compute_relative_area(box2, 1600, 1600)

        self.assertAlmostEqual(area1, area2, places=4)
        self.assertAlmostEqual(area1, 0.01, places=4)

    def test_compute_relative_area_edge_cases(self):
        # None box or 0 dimensions defaults safely to 0.04
        self.assertEqual(compute_relative_area(None, 800, 800), 0.04)
        box = BoundingBox(x1=10.0, y1=10.0, x2=20.0, y2=20.0)
        self.assertEqual(compute_relative_area(box, 0, 800), 0.04)
        self.assertEqual(compute_relative_area(box, 800, -10), 0.04)

        # Inverted box (x2 < x1)
        inv_box = BoundingBox(x1=50.0, y1=50.0, x2=20.0, y2=20.0)
        self.assertEqual(compute_relative_area(inv_box, 800, 800), 0.0)

    def test_calculate_size_component(self):
        # Small < 0.02
        self.assertEqual(calculate_size_component(0.01), 0.33)
        # Medium 0.02 - 0.10
        self.assertEqual(calculate_size_component(0.05), 0.66)
        self.assertEqual(calculate_size_component(0.10), 0.66)
        # Large > 0.10
        self.assertEqual(calculate_size_component(0.15), 1.00)

    def test_large_pothole_high_severity(self):
        # Large pothole (15% area) with high confidence (0.90)
        box = BoundingBox(x1=0.0, y1=0.0, x2=400.0, y2=300.0) # 120,000 / 800,000 = 0.15
        level, score = calculate_severity(
            hazard_type="pothole",
            confidence=0.90,
            bounding_box=box,
            image_width=1000,
            image_height=800
        )
        self.assertEqual(level, "High")
        self.assertGreaterEqual(score, 0.70)

    def test_large_waterlogging_high_severity(self):
        # Large waterlogged zone (> 10% area) with 0.85 confidence
        box = BoundingBox(x1=0.0, y1=0.0, x2=500.0, y2=400.0)
        level, score = calculate_severity(
            hazard_type="waterlogging",
            confidence=0.85,
            bounding_box=box,
            image_width=1000,
            image_height=1000
        )
        self.assertEqual(level, "High")
        self.assertGreaterEqual(score, 0.70)

    def test_medium_road_crack(self):
        # Medium road crack (4% area) with 0.75 confidence
        box = BoundingBox(x1=100.0, y1=100.0, x2=300.0, y2=300.0) # 40,000 / 1,000,000 = 0.04
        level, score = calculate_severity(
            hazard_type="road_crack",
            confidence=0.75,
            bounding_box=box,
            image_width=1000,
            image_height=1000
        )
        # base: 0.67 * 0.50 = 0.335
        # conf: 0.75 * 0.30 = 0.225
        # size: 0.66 * 0.20 = 0.132
        # total: ~0.692 -> Medium
        self.assertEqual(level, "Medium")
        self.assertGreaterEqual(score, 0.40)
        self.assertLess(score, 0.70)

    def test_small_low_confidence_hazard(self):
        # Small construction barrier (0.5% area) with 0.25 confidence
        box = BoundingBox(x1=0.0, y1=0.0, x2=50.0, y2=50.0) # 2,500 / 1,000,000 = 0.0025
        level, score = calculate_severity(
            hazard_type="construction_barrier",
            confidence=0.25,
            bounding_box=box,
            image_width=1000,
            image_height=1000
        )
        # base: 0.67 * 0.50 = 0.335
        # conf: 0.25 * 0.30 = 0.075
        # size: 0.33 * 0.20 = 0.066
        # total: ~0.476 -> Medium, but with low base or 0.1 conf:
        self.assertIn(level, ["Low", "Medium"])

        # Very low confidence test
        level_low, score_low = calculate_severity(
            hazard_type="construction_barrier",
            confidence=0.05,
            bounding_box=box,
            image_width=1000,
            image_height=1000
        )
        self.assertEqual(level_low, "Low")
        self.assertLess(score_low, 0.40)

    def test_robustness_none_and_out_of_range(self):
        # None values and out of range inputs
        level, score = calculate_severity(
            hazard_type="unknown_hazard",
            confidence=1.5, # should clamp to 1.0
            bounding_box=None,
            image_width=None,
            image_height=None
        )
        self.assertIn(level, ["Low", "Medium", "High"])
        self.assertTrue(0.0 <= score <= 1.0)


if __name__ == "__main__":
    unittest.main()
