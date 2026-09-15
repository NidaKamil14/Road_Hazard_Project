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
Stores a detected road hazard with PostGIS spatial location, automated or explicit severity, and priority scoring. If `severity` is omitted, the engine automatically calculates rule-based severity from `hazard_type`, `confidence`, `bounding_box`, `image_width`, and `image_height`.

**Example Request:**
```bash
curl -X POST http://127.0.0.1:8000/hazards \
  -H "Content-Type: application/json" \
  -d '{
    "hazard_type": "pothole",
    "class_id": 0,
    "confidence": 0.88,
    "latitude": 18.5204,
    "longitude": 73.8567,
    "status": "active",
    "bounding_box": {
      "x1": 150.0,
      "y1": 200.0,
      "x2": 450.0,
      "y2": 500.0
    },
    "image_width": 1000,
    "image_height": 800
  }'
```

**Example Response:**
```json
{
  "id": 1,
  "hazard_type": "pothole",
  "class_id": 0,
  "confidence": 0.88,
  "severity": "High",
  "priority_score": 86.5,
  "priority_level": "Critical",
  "priority_reason": "Critical priority: High severity pothole with high detection certainty (0.88).",
  "latitude": 18.5204,
  "longitude": 73.8567,
  "image_path": null,
  "annotated_image_path": null,
  "bounding_box": {
    "x1": 150.0,
    "y1": 200.0,
    "x2": 450.0,
    "y2": 500.0
  },
  "image_width": 1000,
  "image_height": 800,
  "detected_at": "2026-09-15T10:30:00.000000Z",
  "status": "active"
}
```

---

#### 2. `GET /hazards` — List Hazards (Map/Dashboard Ready)
Returns stored hazards with latitude, longitude, severity, priority score, and priority level.

**Query Parameters:**
- `hazard_type` (optional): Filter by type (`pothole`, `road_crack`, `waterlogging`, `construction_barrier`).
- `severity` (optional): Filter by severity (`Low`, `Medium`, `High`).
- `priority_level` (optional): Filter by priority level (`Low`, `Medium`, `High`, `Critical`).
- `status` (optional): Filter by status (`active`, `resolved`).
- `sort_by_priority` (bool, default `false`): If `true`, sorts descending by `priority_score`.
- `limit` (int, default `50`): Pagination limit `[1 - 500]`.
- `offset` (int, default `0`): Pagination offset.

---

#### 3. `GET /hazards/priority` — Priority Ranked Maintenance Queue
Dedicated municipal work-order queue returning road hazards sorted strictly by `priority_score DESC`.

**Query Parameters:**
- `limit` (int, default `50`): Maximum hazards to return `[1 - 500]`.
- `min_priority_score` (float, optional): Minimum priority score filter `[0.0 - 100.0]`.
- `priority_level` (optional): Filter by priority level (`Low`, `Medium`, `High`, `Critical`).
- `hazard_type` (optional): Filter by hazard category.
- `status` (string, default `"active"`): Defaults to active hazards.

**Example Response:**
```json
{
  "total": 1,
  "limit": 50,
  "hazards": [
    {
      "id": 1,
      "hazard_type": "pothole",
      "severity": "High",
      "confidence": 0.88,
      "priority_score": 86.5,
      "priority_level": "Critical",
      "priority_reason": "Critical priority: High severity pothole with high detection certainty (0.88).",
      "latitude": 18.5204,
      "longitude": 73.8567,
      "status": "active",
      "detected_at": "2026-09-15T10:30:00.000000Z"
    }
  ]
}
```

---

#### 4. `GET /hazards/{id}` — Get Single Hazard
Returns the complete record for a specific hazard ID.

---

#### 5. `PATCH /hazards/{id}/status` — Update Status
Update workflow lifecycle status between `"active"` and `"resolved"`.

**Example Request:**
```bash
curl -X PATCH http://127.0.0.1:8000/hazards/1/status \
  -H "Content-Type: application/json" \
  -d '{"status": "resolved"}'
```

---

#### 6. `DELETE /hazards/{id}` — Delete Hazard
Explicitly removes a hazard record.

---

### D. Hazard-Aware Route Recommendation

#### `POST /route/recommend` — Recommend Safest Driving Route
Evaluates candidate driving routes from OSRM against active road hazards in PostGIS within a spatial buffer, balances travel distance with hazard risk, and recommends the safest route.

**Example Request:**
```bash
curl -X POST http://127.0.0.1:8000/route/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "origin": {"latitude": 18.5204, "longitude": 73.8567},
    "destination": {"latitude": 18.5310, "longitude": 73.8470},
    "hazard_radius_meters": 50.0,
    "safety_weight": 0.7
  }'
```

*(See Section 10 for full algorithmic details and response schema).*

---

## 9. Severity & Maintenance Priority Engines

> [!IMPORTANT]
> **Engineering Model Disclaimer:**
> Severity and maintenance priority are rule-based, explainable engineering estimates in the current prototype and are **not directly learned from ground-truth severity labels** (the underlying datasets annotate object presence, not municipal severity ratings).

### A. Severity Engine (`backend/services/severity.py`)
Calculates a continuous severity score `[0.0 - 1.0]` and categorical tier (`Low`, `Medium`, `High`):

```python
relative_area = (box_width * box_height) / (image_width * image_height)

# Normalized size component:
# < 0.02 (small) -> 0.33 | 0.02 to 0.10 (medium) -> 0.66 | > 0.10 (large) -> 1.00

severity_score = (
    0.50 * hazard_base_weight
    + 0.30 * confidence
    + 0.20 * size_component
) + hazard_adjustments  # e.g., +0.05 for large potholes or extensive waterlogging
```

- **Base Weights:** Pothole (`0.85`), Waterlogging (`0.90`), Road Crack (`0.50`), Construction Barrier (`0.50`).
- **Thresholds:**
  - `Low`: Score `< 0.40`
  - `Medium`: `0.40 <= Score < 0.70`
  - `High`: `Score >= 0.70`

### B. Maintenance Priority Scoring Engine (`backend/services/priority.py`)
Computes an actionable municipal index `[0.0 - 100.0]`, priority tier, and deterministic reasoning:

```python
priority_score = (
    0.50 * severity_multiplier
    + 0.30 * hazard_type_multiplier
    + 0.20 * confidence
) * 100.0
```

- **Severity Multipliers:** `Low: 0.33`, `Medium: 0.66`, `High: 1.00`
- **Hazard Type Multipliers:**
  - `waterlogging`: `1.00` (flooding / hydroplaning / impassable)
  - `pothole`: `0.80` (mechanical rim damage / blowout risk)
  - `construction_barrier`: `0.70` (lane constriction / active workzone)
  - `road_crack`: `0.60` (progressive degradation / monitoring)
- **Priority Tiers:**
  - `Low`: `0.0 - 24.9`
  - `Medium`: `25.0 - 49.9`
  - `High`: `50.0 - 74.9`
  - `Critical`: `75.0 - 100.0`
- **Deterministic Reason:** Generates an explainable description stating the severity, hazard type, and confidence certainty for municipal maintenance crews.

---

## 10. Hazard-Aware Route Recommendation Engine

> [!IMPORTANT]
> **Engineering Model Disclaimer:**
> The current routing prototype uses a rule-based hazard penalty model. It is not a learned routing model.

The routing engine bridges AI computer vision detections with real-time navigation. Instead of simply finding the shortest Euclidean or network distance, it balances **Route Distance** against **Route Safety** by penalizing candidate routes that pass near active, high-priority road hazards.

### A. Architectural Pipeline

```
User Origin & Destination Coordinates
                 ↓
      OSRM Driving Service
                 ↓
     Candidate Route Alternatives
                 ↓
  PostGIS Spatial Buffer Search
     (ST_DWithin on geography)
                 ↓
Calculate Proximity Decay Factors
  prox = max(0, 1 - dist / radius)
                 ↓
    Calculate Hazard Penalties
  penalty = (priority / 100) * prox
                 ↓
    Aggregate Route Risk Score
      risk = sum(hazard_penalties)
                 ↓
  Normalize Distance & Safety Cost
  cost = dist_norm + safety_weight * haz_norm
                 ↓
   Recommend Lowest Cost Route
   (Explainable Deterministic Reason)
```

1. **Candidate Routes from OSRM:** Queries the driving profile of Open Source Routing Machine (`/route/v1/driving/`) with `alternatives=true`, `overview=full`, and `geometries=geojson` to obtain driving geometry and metrics.
2. **PostGIS Spatial Search:** Converts route GeoJSON into SRID 4326 geometry and executes `ST_DWithin` using `geography` casting to accurately locate active hazards within the search radius in meters:
   ```sql
   ST_DWithin(h.location::geography, ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)::geography, :radius_meters)
   ```
3. **Priority Score Re-Use:** Directly consumes the existing municipal `priority_score` (0–100) from the Priority Engine, avoiding duplicate weighting logic.
4. **Proximity Influence:** Applies a linear decay function so hazards directly on the centerline carry full weight while hazards near the boundary approach zero:
   $$\text{proximity\_factor} = \max\left(0,\, 1 - \frac{\text{distance}}{\text{hazard\_radius\_meters}}\right)$$
5. **Individual Hazard Penalty:**
   $$\text{hazard\_penalty} = \left(\frac{\text{priority\_score}}{100}\right) \times \text{proximity\_factor}$$
6. **Route Risk Score:** Aggregates penalties across all detected hazards along candidate route $i$:
   $$\text{hazard\_risk\_score} = \sum \text{hazard\_penalty}$$
7. **Distance + Safety Cost Normalization:** Normalizes candidate alternatives against the maximum distance and maximum hazard risk among candidates:
   $$\text{distance\_component} = \frac{\text{distance}_i}{\max(\text{distance})}$$
   $$\text{hazard\_component} = \frac{\text{hazard\_risk}_i}{\max(\text{hazard\_risk})} \quad (\text{or } 0 \text{ if all risks are } 0)$$
   $$\text{route\_cost} = \text{distance\_component} + (\text{safety\_weight} \times \text{hazard\_component})$$
8. **Recommendation Decision:** The candidate with the lowest `route_cost` is chosen. If all routes have zero hazards, the shortest route naturally wins. If an alternative avoids critical hazards with a reasonable distance increase, the safer route is recommended with a clear explanation.

---

### B. Configuration Parameters

- **`hazard_radius_meters`** (float, default: `50.0`, range: `[10.0, 500.0]`): Search buffer perpendicular to the route path.
- **`safety_weight`** (float, default: `0.7`, range: `[0.0, 1.0]`): Tradeoff balance between travel distance and safety:
  - `0.0`: Prioritizes shortest route exclusively.
  - `1.0`: Strongly prioritizes hazard avoidance.
  - `0.7` (default): Favors safety while keeping distance reasonable.

---

### C. Frontend API Integration Contract (React / Leaflet)

#### Endpoint
`POST /route/recommend`

#### Request Payload
```json
{
  "origin": {
    "latitude": 18.5204,
    "longitude": 73.8567
  },
  "destination": {
    "latitude": 18.5310,
    "longitude": 73.8470
  },
  "hazard_radius_meters": 50.0,
  "safety_weight": 0.7
}
```

#### Response Payload
```json
{
  "success": true,
  "recommended_route": {
    "route_id": 1,
    "distance_km": 2.76,
    "duration_minutes": 2.9,
    "hazard_count": 5,
    "critical_hazard_count": 5,
    "high_priority_hazard_count": 0,
    "hazard_risk_score": 2.19,
    "route_cost": 1.7,
    "is_recommended": true,
    "geometry": {
      "type": "LineString",
      "coordinates": [
        [73.8567, 18.5204],
        [73.8562, 18.5215],
        [73.8470, 18.5310]
      ]
    },
    "hazards": [
      {
        "id": 1,
        "hazard_type": "pothole",
        "severity": "High",
        "priority_score": 90.4,
        "priority_level": "Critical",
        "confidence": 0.82,
        "latitude": 18.5204,
        "longitude": 73.8567,
        "distance_from_route": 0.0
      }
    ]
  },
  "alternatives": [],
  "recommendation_reason": "Recommended as the only available drivable route (5 hazards detected along the path).",
  "safety_weight_used": 0.7,
  "hazard_radius_meters_used": 50.0
}
```

> [!NOTE]
> **Coordinate Ordering for Leaflet:**
> The API returns GeoJSON standard `[longitude, latitude]` in `geometry.coordinates`. When rendering in Leaflet `L.polyline` or `Polyline` in React-Leaflet, swap to `[lat, lng]` (e.g., `coords.map(([lon, lat]) => [lat, lon])`) or use standard Leaflet GeoJSON layer `L.geoJSON()`.

