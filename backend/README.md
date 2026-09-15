# Road Hazard Intelligence System — FastAPI & PostGIS Backend

This is the production AI backend for the **Road Hazard Intelligence System**. It combines high-performance computer vision inference powered by **YOLO11s (trained at 800×800)** with geospatial database persistence powered by **PostgreSQL + PostGIS**.

Supported Hazards:
- **Class 0:** `pothole`
- **Class 1:** `road_crack`
- **Class 2:** `waterlogging`
- **Class 3:** `construction_barrier`

---

## 1. System Requirements & Prerequisites

- **Python:** 3.10+ (Python 3.11 recommended)
- **PostgreSQL:** Version 14+ (e.g., PostgreSQL 18)
- **PostGIS:** Version 3.0+
- **GPU:** NVIDIA CUDA-enabled GPU (optional, auto-detects and falls back to CPU)

---

## 2. PostgreSQL & PostGIS Setup

### A. Enable PostGIS Extension
Before running table migrations, ensure the PostGIS extension is enabled in your PostgreSQL database:

```sql
-- Connect to PostgreSQL as superuser
psql -U postgres

-- Create the application database
CREATE DATABASE road_hazard_db;

-- Connect to the database
\c road_hazard_db

-- Enable PostGIS spatial extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Verify PostGIS installation
SELECT PostGIS_Full_Version();
```

---

## 3. Environment Configuration

Copy the example environment file to `.env`:

```bash
cp backend/.env.example backend/.env
```

Configure your PostgreSQL credentials in `backend/.env`:

```dotenv
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/road_hazard_db
MODEL_PATH=runs/detect/experiment2_yolo11s_800/weights/best.pt
```

*(Note: Never commit your actual database password to version control).*

---

## 4. Install Dependencies

Install all required deep learning, API, and geospatial database packages:

```bash
pip install -r backend/requirements.txt
```

---

## 5. Database Initialization

Run the automated, non-destructive database initialization script:

```bash
python backend/init_db.py
```

This script:
1. Tests database connectivity.
2. Checks and enables the `postgis` extension.
3. Creates the `hazards` table and PostGIS spatial index without dropping existing data.
4. Verifies spatial geometry columns.

---

## 6. Starting the Backend Server

Start FastAPI with Uvicorn:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Interactive Swagger Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 7. Architecture Note: Inference vs. Persistence

> [!NOTE]
> **YOLO inference (`POST /detect/image`) is decoupled from hazard persistence (`POST /hazards`).**
> When an image is uploaded for detection, the model runs inference and returns detected bounding boxes and confidences immediately. The frontend or operator workflow explicitly decides which hazards to persist into the database (with geolocation coordinates and metadata).

---

## 8. API Endpoints Reference

### A. Health & Monitoring

#### `GET /health`
Returns model operational status, compute device, active classes, and database connectivity.

**Example Response:**
```json
{
  "status": "ok",
  "model": "YOLO11s",
  "model_path": "F:\\Road_Hazards\\runs\\detect\\experiment2_yolo11s_800\\weights\\best.pt",
  "device": "cuda:0 (NVIDIA RTX PRO 2000 Blackwell)",
  "classes": [
    "pothole",
    "road_crack",
    "waterlogging",
    "construction_barrier"
  ],
  "database": "connected"
}
```

---

### B. Computer Vision Inference

#### `POST /detect/image`
Upload an image (JPEG, PNG, WEBP, BMP) for automated detection.

**Query Parameters:**
- `conf` (float, default: `0.25`): Confidence threshold filter `[0.01 - 1.0]`.
- `iou` (float, default: `0.45`): NMS IoU threshold `[0.01 - 1.0]`.

---

### C. Hazard Spatial Database CRUD

#### 1. `POST /hazards` — Create Road Hazard Record
Stores a detected road hazard with PostGIS spatial location and priority score.

**Example Request:**
```bash
curl -X POST http://127.0.0.1:8000/hazards \
  -H "Content-Type: application/json" \
  -d '{
    "hazard_type": "pothole",
    "class_id": 0,
    "confidence": 0.82,
    "severity": "High",
    "latitude": 18.5204,
    "longitude": 73.8567,
    "status": "active"
  }'
```

**Example Response:**
```json
{
  "id": 1,
  "hazard_type": "pothole",
  "class_id": 0,
  "confidence": 0.82,
  "severity": "High",
  "priority_score": 3,
  "latitude": 18.5204,
  "longitude": 73.8567,
  "image_path": null,
  "annotated_image_path": null,
  "bounding_box": null,
  "image_width": null,
  "image_height": null,
  "detected_at": "2026-09-15T10:30:00.000000Z",
  "status": "active"
}
```

---

#### 2. `GET /hazards` — List Hazards (Map/Dashboard Ready)
Returns stored hazards with latitude, longitude, and priority score, ready for Leaflet map markers.

**Query Parameters:**
- `hazard_type` (optional): Filter by type (`pothole`, `road_crack`, `waterlogging`, `construction_barrier`).
- `severity` (optional): Filter by severity (`Low`, `Medium`, `High`).
- `status` (optional): Filter by status (`active`, `resolved`).
- `limit` (int, default `50`): Pagination limit `[1 - 500]`.
- `offset` (int, default `0`): Pagination offset.

**Example Request:**
```bash
curl -X GET "http://127.0.0.1:8000/hazards?hazard_type=pothole&status=active"
```

**Example Response:**
```json
{
  "total": 1,
  "limit": 50,
  "offset": 0,
  "hazards": [
    {
      "id": 1,
      "hazard_type": "pothole",
      "class_id": 0,
      "confidence": 0.82,
      "severity": "High",
      "priority_score": 3,
      "latitude": 18.5204,
      "longitude": 73.8567,
      "status": "active"
    }
  ]
}
```

---

#### 3. `GET /hazards/{id}` — Get Single Hazard
Returns the complete record for a specific hazard ID.

---

#### 4. `PATCH /hazards/{id}/status` — Update Status
Update workflow lifecycle status between `"active"` and `"resolved"`.

**Example Request:**
```bash
curl -X PATCH http://127.0.0.1:8000/hazards/1/status \
  -H "Content-Type: application/json" \
  -d '{"status": "resolved"}'
```

---

#### 5. `DELETE /hazards/{id}` — Delete Hazard
Explicitly removes a hazard record.

---

## 9. Priority Scoring Logic

The initial baseline priority score is calculated using an isolated service (`backend/services/priority.py`):
- `Low` severity → Priority score `1`
- `Medium` severity → Priority score `2`
- `High` severity → Priority score `3`

This module is designed to be seamlessly swapped with multi-variable algorithms (incorporating traffic flow, road classification, and hazard surface area) in future iterations.
