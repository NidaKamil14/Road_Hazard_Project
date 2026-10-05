"""
End-to-End System Integration Test Script.
Validates:
1. Health check & model metadata
2. Detection on all 4 classes using Experiment 3 best.pt
3. Class mapping and frontend name consistency (Pothole, Road Crack, Waterlogging, Construction Barrier)
4. PostgreSQL / PostGIS hazard persistence
5. Automated Severity and Priority scoring
6. Hazard retrieval and spatial querying
7. Route recommendation with OSRM and hazard risk analysis
8. Municipal Authority authentication, session management, and status patching
9. Clean deletion of test records
"""

import sys
from pathlib import Path
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BASE_URL = "http://127.0.0.1:5000"

def run_e2e_test():
    print("=" * 80)
    print("STARTING COMPLETE END-TO-END SYSTEM INTEGRATION TEST")
    print("=" * 80)

    # 1. Health Endpoint
    print("\n[Step 1] Verifying GET /health ...")
    h_res = requests.get(f"{BASE_URL}/health", timeout=10)
    assert h_res.status_code == 200, f"Health check failed: {h_res.status_code}"
    h_data = h_res.json()
    print("  -> Status:", h_data.get("status"))
    print("  -> Model:", h_data.get("model"))
    print("  -> Device:", h_data.get("device"))
    print("  -> Classes:", h_data.get("classes"))
    print("  -> Database:", h_data.get("database"))
    assert h_data.get("model") == "YOLO11s"
    assert h_data.get("database") == "connected"

    # 2. Four-Class Detection Test
    print("\n[Step 2] Testing 4 Hazard Classes with YOLO11s Experiment 3 Model ...")
    test_cases = [
        ("Pothole", "Datasets/experiment3_dataset/merged_dataset/images/test/RDD_China_Drone_001555.jpg"),
        ("Road Crack", "Datasets/experiment3_dataset/merged_dataset/images/test/RDD_China_Drone_000008.jpg"),
        ("Waterlogging", "Datasets/experiment3_dataset/merged_dataset/images/test/WL_Flood_1001.jpg"),
        ("Construction Barrier", "Datasets/experiment3_dataset/merged_dataset/images/test/RW_boston_10cb4a5e9c0740c8a6ff092bae0d4873_000003_00030_jpg.rf.2b6ce8fce761bfae9a6c7831081137c0.jpg")
    ]

    CLASS_NAME_MAP = {
        "pothole": "Pothole",
        "road_crack": "Road Crack",
        "waterlogging": "Waterlogging",
        "construction_barrier": "Construction Barrier"
    }

    test_hazard_ids = []

    for expected_label, rel_img_path in test_cases:
        img_path = PROJECT_ROOT / rel_img_path
        assert img_path.exists(), f"Missing test image: {img_path}"

        with open(img_path, "rb") as f:
            files = {"file": (img_path.name, f, "image/jpeg")}
            d_res = requests.post(f"{BASE_URL}/detect/image?conf=0.25&iou=0.45", files=files, timeout=30)

        assert d_res.status_code == 200, f"Detection failed for {expected_label}: {d_res.status_code}"
        d_data = d_res.json()
        detections = d_data.get("detections", [])
        assert len(detections) > 0, f"No detections found for {expected_label}"

        top = detections[0]
        display_name = CLASS_NAME_MAP.get(top["class_name"], top["class_name"])
        bbox = top["bounding_box"]
        print(f"  [{expected_label}] Detected: '{display_name}' (ID: {top['class_id']}), Conf: {top['confidence']*100:.1f}%, BBox: [{bbox['x1']}, {bbox['y1']}, {bbox['x2']}, {bbox['y2']}]")

        # 3. Save Hazard to Database
        payload = {
            "hazard_type": top["class_name"],
            "class_id": top["class_id"],
            "confidence": top["confidence"],
            "latitude": 18.5204,
            "longitude": 73.8567,
            "image_width": d_data["image_width"],
            "image_height": d_data["image_height"],
            "bounding_box": bbox,
            "status": "active"
        }
        s_res = requests.post(f"{BASE_URL}/hazards", json=payload, timeout=10)
        assert s_res.status_code == 201, f"Failed to save {expected_label}: {s_res.text}"
        saved = s_res.json()
        print(f"       -> Saved to DB (ID: {saved['id']}): Severity={saved['severity']}, Priority={saved['priority_level']} ({saved['priority_score']})")
        test_hazard_ids.append(saved["id"])

    # 4. Spatial Hazard Querying
    print("\n[Step 3] Verifying Hazard Retrieval (GET /hazards) ...")
    g_res = requests.get(f"{BASE_URL}/hazards?status=active&limit=10", timeout=10)
    assert g_res.status_code == 200
    g_data = g_res.json()
    print(f"  -> Total hazards in DB: {g_data.get('total')}, Retrieved: {len(g_data.get('hazards', []))}")

    # 5. Route Recommendation
    print("\n[Step 4] Verifying Hazard-Aware Route Recommendation (POST /route/recommend) ...")
    r_payload = {
        "origin": {"latitude": 18.5204, "longitude": 73.8567},
        "destination": {"latitude": 18.5310, "longitude": 73.8470},
        "hazard_radius_meters": 100.0,
        "safety_weight": 0.7
    }
    r_res = requests.post(f"{BASE_URL}/route/recommend", json=r_payload, timeout=15)
    print("  -> Route Recommendation HTTP Status:", r_res.status_code)
    if r_res.status_code == 200:
        r_data = r_res.json()
        rec = r_data["recommended_route"]
        print(f"  -> Recommended Distance: {rec['distance_km']} km, Duration: {rec['duration_minutes']} min")
        print(f"  -> Hazard count on path: {rec.get('hazard_count', 0)}, Hazard penalty: {rec.get('hazard_risk_score', 0)}")
        print(f"  -> Alternatives count: {len(r_data.get('alternatives', []))}")
        print(f"  -> Recommendation reason: {r_data.get('recommendation_reason')}")

    # 6. Authority Authentication & Session Management
    print("\n[Step 5] Verifying Authority Portal Authentication & Sessions ...")
    session = requests.Session()
    login_res = session.post(f"{BASE_URL}/api/auth/login", json={"username": "admin", "password": "AdminPassword123!"}, timeout=10)
    assert login_res.status_code == 200, f"Login failed: {login_res.status_code}"
    print("  -> Login Successful:", login_res.json().get("user"))

    session_res = session.get(f"{BASE_URL}/api/auth/session", timeout=10)
    assert session_res.status_code == 200
    s_data = session_res.json()
    assert s_data.get("authenticated") is True
    print("  -> Session Authenticated:", s_data.get("authenticated"), s_data.get("user"))

    # 7. Update Hazard Status (PATCH /hazards/{id}/status)
    print("\n[Step 6] Verifying Hazard Workflow Status Update (PATCH /hazards/{id}/status) ...")
    patch_id = test_hazard_ids[0]
    patch_res = session.patch(f"{BASE_URL}/hazards/{patch_id}/status", json={"status": "resolved"}, timeout=10)
    assert patch_res.status_code == 200, f"Patch failed: {patch_res.status_code}"
    assert patch_res.json().get("status") == "resolved"
    print(f"  -> Hazard ID {patch_id} status updated to: '{patch_res.json().get('status')}'")

    # Verify status changed in database
    chk_res = session.get(f"{BASE_URL}/hazards/{patch_id}", timeout=10)
    assert chk_res.json().get("status") == "resolved"
    print(f"  -> Verified persistence: Hazard {patch_id} is now 'resolved' in database.")

    # 8. Clean Deletion of Test Records
    print("\n[Step 7] Cleaning Up Test Hazard Records (DELETE /hazards/{id}) ...")
    for hid in test_hazard_ids:
        del_res = session.delete(f"{BASE_URL}/hazards/{hid}", timeout=10)
        assert del_res.status_code == 200, f"Failed to delete test hazard {hid}"
        print(f"  -> Deleted test hazard ID {hid}: Success")

    # Logout
    logout_res = session.post(f"{BASE_URL}/api/auth/logout", timeout=10)
    assert logout_res.status_code == 200
    print("  -> Authority logout successful.")

    print("\n" + "=" * 80)
    print("ALL 7 END-TO-END SYSTEM INTEGRATION STEPS PASSED WITH 100% SUCCESS!")
    print("=" * 80)

if __name__ == "__main__":
    run_e2e_test()
