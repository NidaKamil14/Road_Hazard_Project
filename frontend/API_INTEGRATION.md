# Frontend API Integration Contract

This document details the expected API contract for the Road Hazard Detection System frontend. The frontend is currently running in mock mode, but is prepared to integrate with a backend implementing this specification.

## API Endpoint
**POST** `/api/detect`

## Request Format
The request must be sent as `multipart/form-data`.
- **Field name:** `image`
- **Value:** The image file uploaded by the user.

*Note: The frontend uses the browser's native `FormData` and `fetch` API. It does not manually set the `Content-Type` header so that the browser can correctly append the multipart boundary.*

## Responses

### 1. Successful Detection (Hazards Found)
When hazards are successfully detected in the uploaded image.

**Status:** 200 OK
**Content-Type:** `application/json`

```json
{
  "success": true,
  "filename": "road.jpg",
  "detections": [
    {
      "class_id": 0,
      "class_name": "Pothole",
      "confidence": 0.92,
      "bbox": {
        "x1": 120,
        "y1": 180,
        "x2": 310,
        "y2": 340
      }
    }
  ],
  "counts": {
    "Pothole": 1,
    "Road Crack": 0,
    "Waterlogging": 0,
    "Construction Barrier": 0
  },
  "annotated_image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ..."
}
```

#### Field Details:
- `confidence`: A decimal value between `0.0` and `1.0`. The frontend will convert this to a percentage if necessary.
- `bbox`: Absolute pixel coordinates relative to the original image dimensions.
  - `x1`, `y1`: Top-left corner.
  - `x2`, `y2`: Bottom-right corner.

### 2. Successful Detection (No Hazards Found)
When the image is successfully processed but no hazards are identified.

**Status:** 200 OK
**Content-Type:** `application/json`

```json
{
  "success": true,
  "filename": "road.jpg",
  "detections": [],
  "counts": {
    "Pothole": 0,
    "Road Crack": 0,
    "Waterlogging": 0,
    "Construction Barrier": 0
  },
  "annotated_image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ..." 
}
```
*Note: `annotated_image` in this case may just be the original image or omitted entirely, but the frontend will handle empty detections gracefully.*

### 3. Error Response
When the server fails to process the image (e.g., invalid format, model error, server error).

**Status:** 4xx or 500
**Content-Type:** `application/json`

```json
{
  "success": false,
  "error": "Unable to process the uploaded image."
}
```

## Frontend Configuration
The frontend exposes a simple configuration block at the top of `app.js` to toggle backend integration:

```javascript
const CONFIG = {
  USE_MOCK_API: true, // Set to false to enable actual backend requests
  API_BASE_URL: "http://localhost:5000",
  DETECT_ENDPOINT: "/api/detect",
  REQUEST_TIMEOUT_MS: 30000
};
```
