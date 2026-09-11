#!/usr/bin/env python3
"""
Road Hazard Detection - Inference & Prediction Script
Run inference on images, video files, directories, or webcam streams.
"""

import os
import argparse
import cv2
from ultralytics import YOLO


def parse_args():
    parser = argparse.ArgumentParser(description="Run Inference on Road Hazard Imagery")
    parser.add_argument(
        "--weights",
        type=str,
        default="runs/detect/runs/detect/baseline/weights/best.pt",
        help="Path to trained model weights",
    )
    parser.add_argument("--source", type=str, required=True, help="Input source: image path, video path, folder, or 0 (webcam)")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence detection threshold")
    parser.add_argument("--iou", type=float, default=0.45, help="NMS IoU threshold")
    parser.add_argument("--imgsz", type=int, default=640, help="Input image size")
    parser.add_argument("--save", action="store_true", default=True, help="Save annotated detection results")
    parser.add_argument("--project", type=str, default="runs/predict", help="Directory to save predictions")
    parser.add_argument("--name", type=str, default="exp", help="Prediction run name")
    return parser.parse_args()


def main():
    args = parse_args()
    if not os.path.exists(args.weights):
        alt_weights = "runs/detect/baseline/weights/best.pt"
        if os.path.exists(alt_weights):
            args.weights = alt_weights
        else:
            raise FileNotFoundError(f"Model weights not found at: {args.weights}")

    print(f"Loading model: {args.weights}")
    model = YOLO(args.weights)

    print(f"Running inference on source: {args.source}")
    print(f"Confidence threshold: {args.conf}, IoU threshold: {args.iou}")

    results = model.predict(
        source=args.source,
        conf=args.conf,
        iou=args.iou,
        imgsz=args.imgsz,
        save=args.save,
        project=args.project,
        name=args.name,
        exist_ok=True,
    )

    print(f"\nInference completed successfully!")
    if args.save:
        print(f"Results saved in: {os.path.join(args.project, args.name)}")


if __name__ == "__main__":
    main()
