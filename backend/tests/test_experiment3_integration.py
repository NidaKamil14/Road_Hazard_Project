"""
Integration Tests for Experiment 3 Model, FastAPI Endpoints, Database, and Routing.
Tests end-to-end API workflows with real FastAPI application, PostGIS hazard persistence,
and route recommendations.
"""

import os
import sys
from pathlib import Path
import pytest
import cv2
from fastapi.testclient import TestClient

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure required environment variables
os.environ["SESSION_SECRET_KEY"] = "road_hazard_intelligence_secret_key_32_chars_min_length"
os.environ["SESSION_COOKIE_SECURE"] = "false"

from backend.main import app
from backend.database import SessionLocal, check_db_status, get_db
from backend.models.hazard import Hazard
from backend.services.detector import RoadHazardDetector


@pytest.fixture(autouse=True)
def clean_dependency_overrides():
    """Ensure tests run against real PostgreSQL/PostGIS, not test_auth's in-memory SQLite."""
    prev = app.dependency_overrides.pop(get_db, None)
    yield
    if prev is not None:
        app.dependency_overrides[get_db] = prev


@pytest.fixture(scope="module")
def real_pothole_image():
    """Load a real pothole image from the Experiment 3 test dataset."""
    img_path = PROJECT_ROOT / "Datasets/experiment3_dataset/merged_dataset/images/test/RDD_China_Drone_001555.jpg"
    assert img_path.exists(), f"Test image missing: {img_path}"
    with open(img_path, "rb") as f:
        return f.read(), img_path.name


# ==============================================================================
# 1. LIFESPAN & HEALTH ENDPOINT INTEGRATION TESTS
# ==============================================================================

def test_integration_lifespan_model_loading():
    """Verify that detector is loaded once into app.state during application lifespan."""
    with TestClient(app) as client:
        # Check that app.state.detector was initialized
        detector = getattr(app.state, "detector", None)
        assert detector is not None, "Detector was not loaded into app.state on startup"
        assert isinstance(detector, RoadHazardDetector)
        assert "experiment3_yolo11s_800/weights/best.pt" in detector.model_path.replace("\\", "/")


def test_integration_health_endpoint():
    """Verify GET /health reports model YOLO11s, best.pt path, 4 classes, and DB status."""
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["model"] == "YOLO11s"
        assert "experiment3_yolo11s_800/weights/best.pt" in data["model_path"].replace("\\", "/")
        assert data["classes"] == [
            "pothole",
            "road_crack",
            "waterlogging",
            "construction_barrier",
        ]
        assert "database" in data
        assert data["database"] in ["connected", "disconnected", "not_configured"]


# ==============================================================================
# 2. DETECTION API ENDPOINT INTEGRATION TESTS
# ==============================================================================

def test_integration_detect_image_endpoint(real_pothole_image):
    """Verify POST /detect/image with real test set road image upload."""
    img_bytes, filename = real_pothole_image
    with TestClient(app) as client:
        files = {"file": (filename, img_bytes, "image/jpeg")}
        response = client.post("/detect/image?conf=0.25&iou=0.45", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total_detections"] >= 1
        assert data["inference_time_ms"] > 0
        assert data["image_width"] > 0
        assert data["image_height"] > 0
        assert data["annotated_image_url"] is not None

        detected_names = [d["class_name"] for d in data["detections"]]
        assert "pothole" in detected_names


# ==============================================================================
# 3. DATABASE / POSTGIS COMPATIBILITY INTEGRATION TESTS
# ==============================================================================

def test_integration_database_hazard_persistence():
    """Verify that all 4 Experiment 3 hazard classes can be represented in PostGIS."""
    if check_db_status() != "connected":
        pytest.skip("PostgreSQL / PostGIS database is not currently connected.")

    with TestClient(app) as client:
        classes_to_test = [
            ("pothole", 0),
            ("road_crack", 1),
            ("waterlogging", 2),
            ("construction_barrier", 3),
        ]
        created_hazard_ids = []

        try:
            for htype, cid in classes_to_test:
                payload = {
                    "hazard_type": htype,
                    "class_id": cid,
                    "confidence": 0.88,
                    "latitude": 18.5204,
                    "longitude": 73.8567,
                    "image_width": 800,
                    "image_height": 800,
                    "x1": 100.0,
                    "y1": 100.0,
                    "x2": 200.0,
                    "y2": 200.0,
                    "status": "active",
                }
                res = client.post("/hazards", json=payload)
                assert res.status_code == 201, f"Failed to persist {htype}: {res.text}"
                hdata = res.json()
                assert hdata["hazard_type"] == htype
                assert hdata["class_id"] == cid
                assert hdata["severity"] in ["Low", "Medium", "High"]
                assert 0.0 <= hdata["priority_score"] <= 100.0
                created_hazard_ids.append(hdata["id"])

            # Verify querying back
            res_query = client.get("/hazards?limit=10")
            assert res_query.status_code == 200

        finally:
            # Clean up created test hazards so we leave no side effects
            if created_hazard_ids:
                db = SessionLocal()
                try:
                    for hid in created_hazard_ids:
                        h = db.query(Hazard).filter(Hazard.id == hid).first()
                        if h:
                            db.delete(h)
                    db.commit()
                finally:
                    db.close()


# ==============================================================================
# 4. ROUTE RECOMMENDATION COMPATIBILITY INTEGRATION TESTS
# ==============================================================================

def test_integration_route_recommendation():
    """Verify POST /route/recommend generates routes and scores hazard risk."""
    with TestClient(app) as client:
        payload = {
            "origin": {"latitude": 18.5204, "longitude": 73.8567},
            "destination": {"latitude": 18.5310, "longitude": 73.8470},
            "hazard_radius_meters": 50.0,
            "safety_weight": 0.7,
        }
        res = client.post("/route/recommend", json=payload)
        # OSRM public server may be 200 (success) or 503 (if network/rate limited)
        assert res.status_code in [200, 503]
        if res.status_code == 200:
            data = res.json()
            assert data["success"] is True
            assert "recommended_route" in data
            assert "alternatives" in data
            assert "recommendation_reason" in data
            rec = data["recommended_route"]
            assert rec["distance_km"] > 0
            assert rec["duration_minutes"] > 0
            assert isinstance(rec["geometry"]["coordinates"], list)
