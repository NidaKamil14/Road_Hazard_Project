import os
import time
import uuid
import cv2
import numpy as np
import torch
from ultralytics import YOLO

from backend.schemas.detection import (
    BoundingBox,
    DetectionItem,
    DetectionResponse,
    HealthResponse,
)


class RoadHazardDetector:
    """Road Hazard Detection Service wrapping YOLO11s trained model.
    Loads once on startup and handles batched/single image inference.
    """

    DEFAULT_MODEL_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "runs",
        "detect",
        "experiment2_yolo11s_800",
        "weights",
        "best.pt",
    )

    EXPECTED_CLASSES = {
        0: "pothole",
        1: "road_crack",
        2: "waterlogging",
        3: "construction_barrier",
    }

    def __init__(self, model_path: str = None):
        self.model_path = model_path or os.environ.get("MODEL_PATH", self.DEFAULT_MODEL_PATH)
        if not os.path.isabs(self.model_path):
            self.model_path = os.path.abspath(self.model_path)

        if not os.path.exists(self.model_path):
            # Fallback search in backend/models
            alt_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "models",
                "best.pt",
            )
            if os.path.exists(alt_path):
                self.model_path = alt_path
            else:
                raise FileNotFoundError(
                    f"Trained YOLO11s model checkpoint not found at: {self.model_path}"
                )

        # Detect compute device
        self.has_cuda = torch.cuda.is_available()
        self.device_str = "cuda:0" if self.has_cuda else "cpu"
        self.device_name = (
            torch.cuda.get_device_name(0) if self.has_cuda else "CPU"
        )

        print(f"[RoadHazardDetector] Loading model from: {self.model_path}")
        print(f"[RoadHazardDetector] Compute Device: {self.device_str} ({self.device_name})")

        # Load YOLO model
        self.model = YOLO(self.model_path)
        
        # Verify classes
        self.class_names = self.model.names if hasattr(self.model, "names") else self.EXPECTED_CLASSES
        print(f"[RoadHazardDetector] Model loaded successfully with classes: {self.class_names}")

    def get_health(self) -> HealthResponse:
        """Return loaded model health and compute device metadata."""
        classes_list = [
            self.class_names.get(i, f"class_{i}")
            for i in sorted(self.class_names.keys())
        ]
        return HealthResponse(
            status="ok",
            model="YOLO11s",
            model_path=self.model_path,
            device=f"{self.device_str} ({self.device_name})",
            classes=classes_list,
        )

    def predict_image(
        self,
        image_bytes: bytes,
        filename: str = "upload.jpg",
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        output_dir: str = None,
    ) -> DetectionResponse:
        """Run YOLO inference on uploaded image bytes and save annotated output."""
        # Decode raw bytes to OpenCV image (BGR)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img_bgr is None:
            raise ValueError("Failed to decode image bytes into valid image format.")

        height, width = img_bgr.shape[:2]

        # Run inference with resolution 800 (matching model training)
        t0 = time.perf_counter()
        results = self.model.predict(
            source=img_bgr,
            conf=conf_threshold,
            iou=iou_threshold,
            imgsz=800,
            device=self.device_str,
            verbose=False,
        )[0]
        inference_time_ms = round((time.perf_counter() - t0) * 1000, 2)

        # Extract detections
        detections = []
        for box in results.boxes:
            cls_id = int(box.cls[0].item())
            cls_name = self.class_names.get(cls_id, str(cls_id))
            conf_val = round(float(box.conf[0].item()), 4)
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            detections.append(
                DetectionItem(
                    class_id=cls_id,
                    class_name=cls_name,
                    confidence=conf_val,
                    bounding_box=BoundingBox(
                        x1=round(x1, 1),
                        y1=round(y1, 1),
                        x2=round(x2, 1),
                        y2=round(y2, 1),
                    ),
                )
            )

        # Generate annotated image
        annotated_url = None
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            annotated_img = results.plot()  # Standard high-visibility YOLO annotation
            clean_stem = os.path.splitext(os.path.basename(filename))[0]
            unique_id = uuid.uuid4().hex[:8]
            out_filename = f"annotated_{int(time.time())}_{unique_id}_{clean_stem}.jpg"
            out_filepath = os.path.join(output_dir, out_filename)
            cv2.imwrite(out_filepath, annotated_img)
            annotated_url = f"/outputs/{out_filename}"

        return DetectionResponse(
            success=True,
            total_detections=len(detections),
            inference_time_ms=inference_time_ms,
            image_width=width,
            image_height=height,
            annotated_image_url=annotated_url,
            detections=detections,
        )
