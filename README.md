# 🛣️ Road Hazard Intelligence System

An intelligent, end-to-end computer vision and spatial intelligence platform for automated road hazard detection, risk-aware route recommendation, and municipal infrastructure maintenance. Powered by **YOLO11s (trained at 800×800)**, **FastAPI**, **PostgreSQL + PostGIS**, and **OSRM**.

---

## 📌 Project Overview

Road safety, vehicular damage prevention, and municipal repair scheduling require automated detection of critical road hazards. This system integrates deep learning inference with geospatial analytics to detect, prioritize, and safely route around four primary hazard categories:

| Class ID | Hazard Category | Description | Source Dataset | Production Ontology |
| :---: | :--- | :--- | :--- | :--- |
| **0** | **Pothole** | Structural cavities, depressions, and surface ruptures | RDD2022 | `pothole` |
| **1** | **Road Crack** | Longitudinal, transverse, and alligator cracks | RDD2022 | `road_crack` |
| **2** | **Waterlogging** | Standing water pools, puddles, and roadway flooding | FloodDET | `waterlogging` |
| **3** | **Construction Barrier** | Traffic cones, safety barrels, and active workzone barriers | Roadwork Cones | `construction_barrier` |

---

## 🏗️ End-to-End System Architecture

```text
       User Upload (Image)
               ↓
    FastAPI Inference Service (Port 5000: POST /detect/image)
               ↓
    YOLO11s Experiment 3 Detector (800×800, Tensor Processing on CUDA)
               ↓
  Rule-Based Severity Engine (Low / Medium / High)
               ↓
  Maintenance Priority Engine (0–100 Score, Low / Medium / High / Critical)
               ↓
  PostgreSQL + PostGIS Database (geometry(Point, 4326))
               ↓
  Hazard-Aware Routing Engine (OSRM + PostGIS ST_DWithin Proximity Decay)
               ↓
  Frontend Dashboard & Interactive Leaflet Map (Port 8000)
  ├── User Detection Portal (detect.html)
  ├── Spatial Map & Route Planning (map.html)
  └── Municipal Authority Portal (index.html, admin-dashboard.html)
```

---

## 📊 Authoritative Model: Experiment 3 (YOLO11s at 800×800)

The production checkpoint is fine-tuned on the merged and class-balanced dataset at **800×800 resolution**:

* **Authoritative Checkpoint:** `runs/detect/experiment3_yolo11s_800/weights/best.pt`
* **Architecture:** YOLO11s (~9.46M parameters, 21.7 GFLOPs)
* **Input Resolution:** 800 × 800
* **Test Evaluation Metrics:**
  * **mAP@50:** **73.14%**
  * **mAP@50-95:** **49.62%**
  * **Precision:** **78.73%**
  * **Recall:** **68.57%**

### Model Evolution History
* **Baseline (YOLO11n, 640×640):** mAP@50: 61.70%, mAP@50-95: 34.93%
* **Experiment 2 (YOLO11s, 800×800):** Initial scale-up validation
* **Experiment 3 (YOLO11s, 800×800 — Final):** Clean balanced ontology, peak test mAP@50: **73.14%**

Detailed evaluations and training logs are preserved in [`reports/`](reports/).

---

## 📁 Repository Structure

```text
Road_Hazards/
├── backend/
│   ├── main.py                     # FastAPI application & lifespan loader
│   ├── database.py                 # SQLAlchemy engine & PostGIS connection
│   ├── init_db.py                  # Database & PostGIS initialization script
│   ├── create_admin.py             # Administrator account creation script
│   ├── models/
│   │   ├── hazard.py               # PostGIS Point hazard model
│   │   └── admin.py                # Admin user authentication model
│   ├── routes/
│   │   ├── hazards.py              # CRUD & spatial hazard endpoints
│   │   ├── routing.py              # Hazard-aware route recommendation
│   │   └── auth.py                 # Session authentication routes
│   ├── schemas/                    # Pydantic request/response schemas
│   ├── services/
│   │   ├── detector.py             # RoadHazardDetector (YOLO11s wrapper)
│   │   ├── severity.py             # Rule-based Severity Engine
│   │   ├── priority.py             # Maintenance Priority Scoring Engine
│   │   ├── routing.py              # OSRM driving service client
│   │   └── hazard_analyzer.py      # Spatial buffer decay & route penalty
│   └── tests/                      # Automated test suite (63/63 passing)
├── frontend/
│   ├── index.html                  # Access Gateway (Public & Authority portal)
│   ├── detect.html                 # Public detection & image analysis interface
│   ├── map.html                    # Leaflet map & hazard-aware routing interface
│   ├── admin-dashboard.html        # Municipal Authority dashboard & summary
│   ├── admin-reports.html          # Paginated hazard report queue
│   ├── admin-report-details.html   # Report detail view & status management
│   ├── app.js                      # Detection logic & database integration
│   ├── map.js                      # Spatial rendering & route polyline visualizer
│   ├── auth.js                     # Session management & gateway logic
│   ├── admin.js                    # Authority workflows & PATCH status
│   └── styles.css                  # UI design system & responsive styling
├── runs/
│   └── detect/
│       └── experiment3_yolo11s_800/# Production model weights & plots
│           └── weights/best.pt     # Authoritative trained model checkpoint
├── configs/
│   └── data.yaml                   # YOLO dataset split & class ontology config
├── reports/                        # Comprehensive test & evaluation reports
│   ├── final_end_to_end_testing_report.txt
│   ├── final_pre_submission_audit_report.txt
│   └── experiment3_integration_testing_report.txt
├── requirements.txt                # Root Python dependencies
└── README.md                       # Master system documentation
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+ (Python 3.11 / 3.14 compatible)
- PostgreSQL 14+ with PostGIS 3.0+ extension
- NVIDIA CUDA GPU (optional, auto-detects GPU or CPU)

### 2. Environment Configuration
Create `backend/.env` based on `backend/.env.example`:

```dotenv
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/road_hazard_db
MODEL_PATH=runs/detect/experiment3_yolo11s_800/weights/best.pt
OSRM_BASE_URL=https://router.project-osrm.org
SESSION_SECRET_KEY=your_generated_32_character_secret_key
SESSION_COOKIE_SECURE=false
```

### 3. Database Initialization & Admin Setup
```bash
# Initialize PostGIS extension and create database tables
python backend/init_db.py

# Create a municipal administrator account
python backend/create_admin.py --username admin
```

### 4. Running the Backend (Port 5000)
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 5000 --reload
```
- API Health Check: [http://127.0.0.1:5000/health](http://127.0.0.1:5000/health)
- Swagger Documentation: [http://127.0.0.1:5000/docs](http://127.0.0.1:5000/docs)

### 5. Running the Frontend (Port 8000)
```bash
python -m http.server 8000 --directory frontend
```
- User Detection Portal: [http://127.0.0.1:8000/detect.html](http://127.0.0.1:8000/detect.html)
- Interactive Map & Routing: [http://127.0.0.1:8000/map.html](http://127.0.0.1:8000/map.html)
- Access Gateway / Authority: [http://127.0.0.1:8000/index.html](http://127.0.0.1:8000/index.html)

---

## 🧪 Automated Test Suite

Run the full automated test suite:
```bash
pytest backend/tests/ -v
```

**Verification Results:**
- **Unit Tests:** 46 / 46 PASSED
- **Integration Tests:** 17 / 17 PASSED
- **Total:** **63 / 63 PASSED (100% Success Rate)**

To execute the live end-to-end system flow test:
```bash
python backend/tests/test_e2e_flow.py
```

---

## 📜 Key Backend API Contracts

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Model status, compute device, class list, and DB connection |
| `POST` | `/detect/image` | YOLO11s image inference at 800×800 with bounding boxes & confidence |
| `POST` | `/hazards` | Persist detected hazard with PostGIS geometry, severity, and priority |
| `GET` | `/hazards` | List active/resolved hazards with spatial bounding and pagination |
| `GET` | `/hazards/priority` | Dedicated municipal repair queue sorted by priority score |
| `PATCH` | `/hazards/{id}/status` | Update workflow lifecycle status (`active` / `resolved`) |
| `DELETE` | `/hazards/{id}` | Remove hazard record |
| `POST` | `/route/recommend` | OSRM candidate routes evaluated against PostGIS hazard buffer |
| `POST` | `/api/auth/login` | Municipal authority session authentication |
| `GET` | `/api/auth/session` | Validate active authority session |
| `POST` | `/api/auth/logout` | Terminate session and clear cookie |

---

## 🛠️ Technology Stack
* **AI & Computer Vision:** Ultralytics YOLO11s, PyTorch, OpenCV, CUDA
* **API Backend:** FastAPI, Starlette Session Middleware, Uvicorn, Pydantic v2
* **Geospatial Database:** PostgreSQL, PostGIS, SQLAlchemy 2.0, GeoAlchemy2, psycopg v3
* **Routing Engine:** Open Source Routing Machine (OSRM) driving API
* **Security & Auth:** Argon2 password hashing (pwdlib), HTTP-only cookies
* **Frontend Web App:** Semantic HTML5, Vanilla JavaScript, Leaflet.js, CSS Design Tokens
* **Testing:** Pytest, HTTPX, FastAPI TestClient

---

## 📜 License
This project is open-sourced under the MIT License for educational and research purposes.
