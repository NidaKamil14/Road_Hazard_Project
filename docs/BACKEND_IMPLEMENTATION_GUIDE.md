# Backend Implementation Guide

This guide explains how to build the Flask backend API for the Road Hazard Detection System and connect it safely with the existing YOLO11 model.

It is written for the teammate responsible for the backend. Follow the steps in order. Do not modify the frontend while implementing the backend.

## 1. Goal

Build a local Flask API that:

1. Loads the trained YOLO11 model once when the server starts.
2. Accepts one JPG, JPEG, or PNG image.
3. Runs road-hazard detection.
4. Returns every detection, class IDs and names, confidence scores, bounding boxes, per-class counts, and an annotated result image.
5. Handles invalid requests without crashing.

The frontend contract is also documented in `frontend/API_INTEGRATION.md`.

## 2. Existing project facts

The trained model should be located at:

```text
runs/detect/baseline/weights/best.pt
```

The four model classes are:

| Class ID | Internal name | API display name |
|---:|---|---|
| 0 | pothole | Pothole |
| 1 | road_crack | Road Crack |
| 2 | waterlogging | Waterlogging |
| 3 | construction_barrier | Construction Barrier |

The frontend currently runs at `http://localhost:8000`.

The backend will run at `http://localhost:5000`.

The detection endpoint must be:

```text
POST http://localhost:5000/api/detect
```

The multipart upload field must be named `image`.

## 3. Create a backend branch

Open PowerShell inside the cloned repository.

First check for uncommitted work:

```powershell
git status
```

If there are changes that belong to somebody else, stop and coordinate before continuing.

Update `main` and create the backend branch:

```powershell
git switch main
git pull origin main
git switch -c feature/backend-api
git push -u origin feature/backend-api
```

Confirm the branch:

```powershell
git branch --show-current
```

Expected result:

```text
feature/backend-api
```

Do not work directly on `main` or `feature/frontend-ui`.

## 4. Check Python and the model

From the repository root:

```powershell
python --version
Test-Path "runs\detect\baseline\weights\best.pt"
```

If `python` is not recognized, try:

```powershell
py --version
```

`Test-Path` must return `True`. If it returns `False`, do not change the model path randomly. Confirm that `best.pt` was downloaded or ask the project owner for the checkpoint.

## 5. Create and activate a virtual environment

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, do not change the computer-wide execution policy. Run the virtual-environment Python directly instead:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

Install the existing requirements:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If the environment was not activated, use:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 6. Add backend dependencies

Add these two lines to `requirements.txt`:

```text
Flask>=3.0.0
flask-cors>=4.0.0
```

Then install them:

```powershell
pip install Flask flask-cors
```

## 7. Create the backend files

Create this structure:

```text
backend/
├── __init__.py
└── app.py
```

The `__init__.py` file may be empty.

Put the following implementation in `backend/app.py`:

```python
from pathlib import Path
import base64

import cv2
import numpy as np
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge
from ultralytics import YOLO


ROOT_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT_DIR / "runs" / "detect" / "baseline" / "weights" / "best.pt"

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

DISPLAY_NAMES = {
    0: "Pothole",
    1: "Road Crack",
    2: "Waterlogging",
    3: "Construction Barrier",
}

COUNT_KEYS = [
    "Pothole",
    "Road Crack",
    "Waterlogging",
    "Construction Barrier",
]


if not MODEL_PATH.exists():
    raise FileNotFoundError(f"Model weights not found: {MODEL_PATH}")

print(f"Loading model from: {MODEL_PATH}")
model = YOLO(str(MODEL_PATH))
print("Model loaded successfully.")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

CORS(
    app,
    resources={r"/api/*": {"origins": ["http://localhost:8000"]}},
)


@app.get("/api/health")
def health():
    return jsonify(
        {
            "success": True,
            "status": "ready",
            "model": MODEL_PATH.name,
        }
    )


@app.post("/api/detect")
def detect():
    if "image" not in request.files:
        return jsonify(
            {
                "success": False,
                "error": 'Missing multipart field "image".',
            }
        ), 400

    uploaded_file = request.files["image"]

    if not uploaded_file or uploaded_file.filename == "":
        return jsonify(
            {
                "success": False,
                "error": "No image was selected.",
            }
        ), 400

    mime_type = (uploaded_file.mimetype or "").lower()
    if mime_type not in ALLOWED_MIME_TYPES:
        return jsonify(
            {
                "success": False,
                "error": "Invalid file type. Upload a JPG, JPEG, or PNG image.",
            }
        ), 400

    image_bytes = uploaded_file.read()
    if not image_bytes:
        return jsonify(
            {
                "success": False,
                "error": "The uploaded image is empty.",
            }
        ), 400

    encoded_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(encoded_array, cv2.IMREAD_COLOR)

    if image is None:
        return jsonify(
            {
                "success": False,
                "error": "The uploaded file could not be decoded as an image.",
            }
        ), 400

    try:
        result = model.predict(
            source=image,
            conf=0.25,
            iou=0.45,
            imgsz=640,
            verbose=False,
        )[0]

        detections = []
        counts = {name: 0 for name in COUNT_KEYS}

        if result.boxes is not None:
            for box in result.boxes:
                class_id = int(box.cls[0].item())
                confidence = float(box.conf[0].item())
                x1, y1, x2, y2 = [
                    round(float(value), 2)
                    for value in box.xyxy[0].tolist()
                ]

                class_name = DISPLAY_NAMES.get(
                    class_id,
                    str(result.names.get(class_id, f"Class {class_id}")),
                )

                detections.append(
                    {
                        "class_id": class_id,
                        "class_name": class_name,
                        "confidence": round(confidence, 4),
                        "bbox": {
                            "x1": x1,
                            "y1": y1,
                            "x2": x2,
                            "y2": y2,
                        },
                    }
                )

                if class_name in counts:
                    counts[class_name] += 1

        annotated_image = result.plot()
        encode_success, encoded_image = cv2.imencode(".jpg", annotated_image)

        if not encode_success:
            raise RuntimeError("Could not encode the annotated result image.")

        annotated_base64 = base64.b64encode(encoded_image.tobytes()).decode("utf-8")

        return jsonify(
            {
                "success": True,
                "filename": uploaded_file.filename,
                "detections": detections,
                "counts": counts,
                "annotated_image": "data:image/jpeg;base64," + annotated_base64,
            }
        )

    except Exception:
        app.logger.exception("Detection failed")
        return jsonify(
            {
                "success": False,
                "error": "Unable to process the uploaded image.",
            }
        ), 500


@app.errorhandler(RequestEntityTooLarge)
def handle_large_upload(_error):
    return jsonify(
        {
            "success": False,
            "error": "The uploaded image is too large. Maximum size is 10 MB.",
        }
    ), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
```

Important points:

- The model is loaded once at startup, not once per request.
- Images are processed in memory.
- Do not save user uploads into the repository.
- Do not return Python exception details to the browser.
- `debug=True` is acceptable only during local development.

## 8. Start the backend

From the repository root with the virtual environment active:

```powershell
python backend/app.py
```

Or, without activating the environment:

```powershell
.\.venv\Scripts\python.exe backend\app.py
```

Expected output includes:

```text
Model loaded successfully.
Running on http://127.0.0.1:5000
```

The first model load can take longer than later requests. Keep this terminal open.

## 9. Test the health endpoint

Open a second PowerShell terminal and run:

```powershell
Invoke-RestMethod http://localhost:5000/api/health
```

Expected fields:

```text
success : True
status  : ready
model   : best.pt
```

If this fails, do not continue to frontend testing until the backend starts successfully.

## 10. Test detection from PowerShell

Use a real road image and replace the example path:

```powershell
curl.exe -X POST -F "image=@C:\full\path\to\road-image.jpg" http://localhost:5000/api/detect -o detection-response.json
```

Inspect the response:

```powershell
Get-Content detection-response.json
```

Confirm that it contains:

- `success` set to `true`;
- the original filename;
- a `detections` array;
- confidence values between 0 and 1;
- bounding boxes with `x1`, `y1`, `x2`, and `y2`;
- all four count keys; and
- `annotated_image` beginning with `data:image/jpeg;base64,`.

An empty `detections` array is a valid successful response when no hazard is found.

## 11. Test invalid requests

### Missing image

```powershell
curl.exe -X POST http://localhost:5000/api/detect
```

Expected: HTTP 400 with `success: false`.

### Invalid file type

```powershell
curl.exe -X POST -F "image=@C:\full\path\to\document.pdf" http://localhost:5000/api/detect
```

Expected: HTTP 400 with a clear invalid-file message.

### Oversized image

Test with a file larger than 10 MB.

Expected: HTTP 413 with a clear size-limit message.

## 12. Validate the API response carefully

Before handing the backend over, verify:

- Class 0 becomes Pothole.
- Class 1 becomes Road Crack.
- Class 2 becomes Waterlogging.
- Class 3 becomes Construction Barrier.
- `confidence` stays numeric and ranges from 0.0 to 1.0.
- Bounding-box coordinates refer to the original uploaded image.
- `counts` agrees with the `detections` array.
- `annotated_image` can be opened by a browser.
- The server remains running after an invalid request.
- The model is not reloaded on every detection.

## 13. Do not modify the frontend yet

The frontend currently uses mock mode in `frontend/app.js`:

```javascript
USE_MOCK_API: true
```

Rehaan will change it to `false` during final integration.

There is one additional frontend change required during integration: after receiving a successful API response, `frontend/app.js` must set the result image source from `responseData.annotated_image`. At present, the frontend displays the locally uploaded image in the results view.

The frontend integrator should update the successful detection flow conceptually as follows:

```javascript
const responseData = await detectHazards(currentFile);

if (responseData.annotated_image) {
  imageResult.src = responseData.annotated_image;
}

showResults(responseData.detections);
```

The backend teammate should not edit `frontend/app.js` unless both teammates explicitly agree.

## 14. Commit and push backend work

Check the changes:

```powershell
git status
git diff --stat
```

Stage only backend-related files:

```powershell
git add backend requirements.txt
git status
```

Do not use `git add .` if unrelated files are present.

Commit:

```powershell
git commit -m "feat: add road hazard detection API"
```

Push:

```powershell
git push origin feature/backend-api
```

Share the following with the frontend teammate:

- Backend branch name: `feature/backend-api`
- Backend commit ID
- Screenshot of the health endpoint
- A sample successful `detection-response.json`
- Confirmation that invalid-file handling works

Do not merge into `main` until both teammates have reviewed and tested the API.

## 15. Final integration sequence

After the backend branch is pushed:

1. Review the backend changes.
2. Test the backend independently on port 5000.
3. Run the frontend independently on port 8000.
4. Set `USE_MOCK_API` to `false`.
5. Display `responseData.annotated_image` in the results view.
6. Upload a real road image.
7. Confirm that demo mode is hidden.
8. Confirm that real counts and confidence scores appear.
9. Test a no-hazard road image.
10. Test backend-unavailable and timeout states.
11. Commit the frontend integration separately.
12. Only then prepare pull requests and merge.

## 16. Common problems

### Python is not recognized

Use `py` instead of `python`, or call:

```powershell
.\.venv\Scripts\python.exe
```

### ModuleNotFoundError

Install dependencies using the same Python that starts the server:

```powershell
python -m pip install -r requirements.txt
```

### Model weights not found

Verify:

```powershell
Test-Path "runs\detect\baseline\weights\best.pt"
```

Run `backend/app.py` from the repository root. Do not copy the model into an arbitrary location.

### Port 5000 is already in use

Stop the process already using port 5000. Do not casually change the port because the frontend is configured for port 5000.

### Browser reports a CORS error

Confirm that `flask-cors` is installed, the frontend runs at `http://localhost:8000`, and the allowed origin matches it exactly.

### Every request is slow

Confirm the YOLO model is created once at module level. It must not be created inside `detect()`. CPU inference may still take several seconds.

### API returns detections but the frontend shows the uploaded image

This is a known integration step. Update `frontend/app.js` to assign `responseData.annotated_image` to `imageResult.src` before showing results.

### Counts do not match

Build counts from the same detections produced by the model. Do not hard-code counts separately.

### Large response

Base64 increases image-response size. Keep the returned annotated image in JPEG format. Do not return both raw image bytes and Base64.

## 17. Completion checklist

- [ ] Work is on `feature/backend-api`.
- [ ] `best.pt` is found.
- [ ] Flask and flask-cors are recorded in `requirements.txt`.
- [ ] Model loads once when the server starts.
- [ ] `GET /api/health` works.
- [ ] `POST /api/detect` accepts multipart field `image`.
- [ ] JPG, JPEG, and PNG work.
- [ ] PDF is rejected.
- [ ] Missing and empty uploads are rejected.
- [ ] Files larger than 10 MB are rejected.
- [ ] Detection objects match `frontend/API_INTEGRATION.md`.
- [ ] All four count keys are returned.
- [ ] `annotated_image` is a JPEG data URL.
- [ ] No-detection responses succeed with an empty array.
- [ ] CORS allows `http://localhost:8000`.
- [ ] Backend changes are committed and pushed.
- [ ] Branch name and sample response are shared with the frontend teammate.
