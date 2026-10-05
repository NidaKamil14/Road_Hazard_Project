"""
Unit Tests for Experiment 3 Model, Class Mapping, and Schema Compatibility.
Tests model initialization, YOLO11s parameter scale, class dictionaries,
inference response formatting, and routing hazard scoring.
"""

import os
import sys
from pathlib import Path
import pytest
import numpy as np
import cv2

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.detector import RoadHazardDetector
from backend.schemas.detection import (
    BoundingBox,
    DetectionItem,
    DetectionResponse,
    HealthResponse,
)
from backend.services.priority import calculate_priority_score
from backend.services.severity import calculate_severity
from backend.services.hazard_analyzer import (
    calculate_hazard_penalty,
    calculate_proximity_factor,
)


@pytest.fixture(scope="module")
def detector():
    """Instantiate RoadHazardDetector with Experiment 3 checkpoint."""
    return RoadHazardDetector()


@pytest.fixture(scope="module")
def test_image_bytes():
    """Generate a clean synthetic road image in memory (800x800)."""
    img = np.full((800, 800, 3), 60, dtype=np.uint8)
    cv2.line(img, (400, 0), (400, 800), (255, 255, 255), 4)
    cv2.circle(img, (400, 400), 40, (20, 20, 20), -1)
    _, encoded = cv2.imencode(".jpg", img)
    return encoded.tobytes()


# ==============================================================================
# 1. MODEL LOADING & CHECKPOINT UNIT TESTS
# ==============================================================================

def test_unit_model_checkpoint_path(detector):
    """Verify that detector is configured with the Experiment 3 best.pt checkpoint."""
    assert os.path.exists(detector.model_path), f"Checkpoint missing: {detector.model_path}"
    norm_path = detector.model_path.replace("\\", "/")
    assert "experiment3_yolo11s_800/weights/best.pt" in norm_path, (
        f"Expected Experiment 3 weights, found: {detector.model_path}"
    )


def test_unit_model_architecture(detector):
    """Verify that the model architecture is YOLO11s (~9.46M parameters)."""
    assert hasattr(detector.model, "model")
    param_count = sum(p.numel() for p in detector.model.model.parameters())
    # YOLO11s has ~9,460,000 parameters
    assert 9_000_000 < param_count < 10_500_000, (
        f"Expected YOLO11s parameter scale (~9.46M), got {param_count}"
    )


# ==============================================================================
# 2. CLASS MAPPING UNIT TESTS
# ==============================================================================

def test_unit_class_mapping(detector):
    """Verify that class IDs 0-3 map exactly to the 4 required project hazard classes."""
    expected_mapping = {
        0: "pothole",
        1: "road_crack",
        2: "waterlogging",
        3: "construction_barrier",
    }
    assert len(detector.class_names) == 4, (
        f"Expected exactly 4 classes, found: {len(detector.class_names)}"
    )
    for cid, name in expected_mapping.items():
        assert detector.class_names.get(cid) == name, (
            f"Class ID {cid} expected '{name}', but got '{detector.class_names.get(cid)}'"
        )


# ==============================================================================
# 3. YOLO INFERENCE & RESPONSE FORMAT UNIT TESTS
# ==============================================================================

def test_unit_inference_pipeline(detector, test_image_bytes):
    """Verify that YOLO inference executes cleanly on image bytes and returns valid schema."""
    response = detector.predict_image(
        image_bytes=test_image_bytes,
        filename="test_road.jpg",
        conf_threshold=0.25,
        iou_threshold=0.45,
    )
    assert isinstance(response, DetectionResponse)
    assert response.success is True
    assert response.image_width == 800
    assert response.image_height == 800
    assert response.inference_time_ms > 0
    assert isinstance(response.detections, list)

    for item in response.detections:
        assert isinstance(item, DetectionItem)
        assert item.class_id in [0, 1, 2, 3]
        assert item.class_name in ["pothole", "road_crack", "waterlogging", "construction_barrier"]
        assert 0.0 <= item.confidence <= 1.0
        assert isinstance(item.bounding_box, BoundingBox)
        assert 0.0 <= item.bounding_box.x1 <= item.bounding_box.x2 <= 800.0
        assert 0.0 <= item.bounding_box.y1 <= item.bounding_box.y2 <= 800.0


def test_unit_health_metadata(detector):
    """Verify HealthResponse structure and metadata."""
    health = detector.get_health()
    assert isinstance(health, HealthResponse)
    assert health.status == "ok"
    assert health.model == "YOLO11s"
    assert "experiment3_yolo11s_800" in health.model_path.replace("\\", "/")
    assert health.classes == [
        "pothole",
        "road_crack",
        "waterlogging",
        "construction_barrier",
    ]


# ==============================================================================
# 4. ROUTING HAZARD SCORING & ENGINE COMPATIBILITY UNIT TESTS
# ==============================================================================

@pytest.mark.parametrize("hazard_class, expected_base_score", [
    ("pothole", 85.0),
    ("road_crack", 60.0),
    ("waterlogging", 85.0),
    ("construction_barrier", 70.0),
])
def test_unit_hazard_priority_compatibility(hazard_class, expected_base_score):
    """Verify that all 4 Experiment 3 hazard classes are recognized by PriorityEngine."""
    score, level, reason = calculate_priority_score(
        hazard_type=hazard_class,
        confidence=0.85,
        severity="Medium",
    )
    assert 0.0 <= score <= 100.0
    assert level in ["Low", "Medium", "High", "Critical"]
    assert len(reason) > 0


def test_unit_routing_penalty_calculation():
    """Verify that hazard penalty calculation works with Experiment 3 class priority scores."""
    # Hazard directly on route (dist = 0m, radius = 50m)
    prox_on_path = calculate_proximity_factor(distance=0.0, radius=50.0)
    assert prox_on_path == 1.0

    # High priority hazard on route (score = 90.0) -> penalty = 0.90
    penalty = calculate_hazard_penalty(priority_score=90.0, proximity_factor=prox_on_path)
    assert penalty == 0.90

    # Hazard at the boundary of buffer (dist = 50m, radius = 50m) -> penalty = 0.0
    prox_at_boundary = calculate_proximity_factor(distance=50.0, radius=50.0)
    assert prox_at_boundary == 0.0
    assert calculate_hazard_penalty(priority_score=90.0, proximity_factor=prox_at_boundary) == 0.0
