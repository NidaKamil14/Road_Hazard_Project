# Admin API Integration Guide

This document specifies the API endpoints expected by the admin frontend. **No backend currently implements these endpoints.** The frontend degrades gracefully — all admin pages show "Service Unavailable" states until a backend is built.

## Configuration

All endpoints are configured in two files:

- **`auth.js`** → `AUTH_CONFIG` (authentication endpoints)
- **`admin.js`** → `ADMIN_CONFIG` (admin data endpoints)

Default base URL: `http://localhost:5000`

To change the base URL, edit the `API_BASE_URL` property in both files.

---

## Authentication Endpoints

All auth requests use `credentials: "include"` for cookie-based sessions.

### POST `/api/auth/login`

Authenticate a municipal user.

**Request:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response (200):**
```json
{
  "user": {
    "username": "admin_user"
  }
}
```

**Response (401):**
```json
{
  "error": "invalid_credentials"
}
```

The backend must set an HTTP-only session cookie on successful login.

---

### GET `/api/auth/session`

Check whether the current user has an active session.

**Response (200, authenticated):**
```json
{
  "authenticated": true,
  "user": {
    "username": "admin_user"
  }
}
```

**Response (200, not authenticated):**
```json
{
  "authenticated": false
}
```

**Response (401):** Treated as not authenticated.

---

### POST `/api/auth/logout`

End the current session.

**Response (200):**
```json
{
  "success": true
}
```

The backend must clear the session cookie.

---

## Admin Data Endpoints

All admin requests use `credentials: "include"`. If any request returns 401, the frontend redirects to the login gateway.

### GET `/api/admin/dashboard`

Fetch dashboard summary and recent reports.

**Response (200):**
```json
{
  "summary": {
    "total_reports": 148,
    "pending_review": 23,
    "high_priority": 19,
    "resolved": 87
  },
  "recent_reports": [
    {
      "id": "RH-0104",
      "hazard_type": "Pothole",
      "confidence": 0.96,
      "priority": "Critical",
      "status": "Pending Review",
      "submitted_at": "2024-10-26T09:14:00Z",
      "thumbnail": "https://example.com/thumb.jpg"
    }
  ]
}
```

---

### GET `/api/admin/reports`

Fetch all reports. Filtering is done client-side.

**Response (200):**
```json
{
  "reports": [
    {
      "id": "RH-0104",
      "hazard_type": "Pothole",
      "confidence": 0.96,
      "priority": "Critical",
      "status": "Pending Review",
      "submitted_at": "2024-10-26T09:14:00Z",
      "thumbnail": "https://example.com/thumb.jpg",
      "image_url": "https://example.com/full.jpg"
    }
  ]
}
```

---

### GET `/api/admin/reports/:id`

Fetch a single report by ID.

**Response (200):**
```json
{
  "report": {
    "id": "RH-0104",
    "hazard_type": "Pothole",
    "confidence": 0.96,
    "priority": "Critical",
    "status": "Pending Review",
    "submitted_at": "2024-10-26T09:14:00Z",
    "image_url": "https://example.com/full.jpg",
    "filename": "road_hazard_0104.jpg",
    "location": null,
    "admin_notes": "",
    "detections": [
      {
        "class_name": "Pothole",
        "confidence": 0.96,
        "bbox": {
          "x1": 120,
          "y1": 80,
          "x2": 340,
          "y2": 200
        }
      }
    ],
    "activity": [
      {
        "title": "Report submitted",
        "description": "Initial image uploaded and queued for processing.",
        "timestamp": "2024-10-26T09:14:00Z"
      },
      {
        "title": "Detection completed",
        "description": "Model completed detection inference (pothole detected · 96%).",
        "timestamp": "2024-10-26T09:14:02Z"
      }
    ]
  }
}
```

---

### PATCH `/api/admin/reports/:id`

Update a report's priority, status, and/or notes.

**Request:**
```json
{
  "priority": "High",
  "status": "Verified",
  "notes": "Confirmed pothole on main road."
}
```

**Response (200):**
```json
{
  "success": true
}
```

---

### POST `/api/admin/reports/:id/verify`

Quick action to verify a detection (sets status to "Verified").

**Response (200):**
```json
{
  "success": true
}
```

---

### POST `/api/admin/reports/:id/reject`

Quick action to mark as false detection (sets status to "Rejected").

**Response (200):**
```json
{
  "success": true
}
```

---

## CORS Requirements

If the frontend and backend run on different origins (e.g., `http://localhost:8000` for frontend, `http://localhost:5000` for backend), the backend must:

1. Set `Access-Control-Allow-Origin: http://localhost:8000`
2. Set `Access-Control-Allow-Credentials: true`
3. Set `Access-Control-Allow-Headers: Content-Type`
4. Set `Access-Control-Allow-Methods: GET, POST, PATCH, OPTIONS`
5. Handle `OPTIONS` preflight requests

---

## Frontend File Map

| File | Purpose |
|---|---|
| `auth.js` | Authentication API calls, session check, page protection |
| `admin.js` | Dashboard, reports, report details logic |
| `index.html` | Access Gateway with login form |
| `detect.html` | Public hazard detector (no auth required) |
| `admin-dashboard.html` | Dashboard (protected) |
| `admin-reports.html` | Reports listing (protected) |
| `admin-report-details.html` | Report detail view (protected) |
