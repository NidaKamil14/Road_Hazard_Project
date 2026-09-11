#!/usr/bin/env python3
"""
Road Hazard Detection - Model Evaluation Script
Evaluates trained checkpoints on Validation and Test sets and prints per-class breakdown.
"""

import os
import argparse
import torch
from ultralytics import YOLO


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate YOLO11 Road Hazard Model")
    parser.add_argument(
        "--weights",
        type=str,
        default="runs/detect/runs/detect/baseline/weights/best.pt",
        help="Path to trained weights .pt",
    )
    parser.add_argument("--data", type=str, default="configs/data.yaml", help="Path to data.yaml")
    parser.add_argument("--split", type=str, default="test", choices=["val", "test", "both"], help="Split to evaluate")
    parser.add_argument("--imgsz", type=int, default=640, help="Image resolution")
    parser.add_argument("--batch", type=int, default=32, help="Batch size")
    parser.add_argument("--device", type=str, default=None, help="Device to evaluate on")
    return parser.parse_args()


def evaluate_split(model, split_name, data_path, imgsz, batch, device):
    print("\n" + "=" * 60)
    print(f"EVALUATION ON '{split_name.upper()}' SPLIT")
    print("=" * 60)

    results = model.val(
        data=data_path,
        split=split_name,
        imgsz=imgsz,
        batch=batch,
        device=device,
        plots=True,
    )

    class_names = {0: "pothole", 1: "road_crack", 2: "waterlogging", 3: "construction_barrier"}

    precision = float(results.box.mp)
    recall = float(results.box.mr)
    map50 = float(results.box.map50)
    map50_95 = float(results.box.map)

    print(f"\nOverall Metrics ({split_name}):")
    print(f"  mAP@50:     {map50 * 100:.2f}% ({map50:.4f})")
    print(f"  mAP@50-95:  {map50_95 * 100:.2f}% ({map50_95:.4f})")
    print(f"  Precision:  {precision * 100:.2f}% ({precision:.4f})")
    print(f"  Recall:     {recall * 100:.2f}% ({recall:.4f})")

    print("\nPer-Class Breakdown:")
    print(f"  {'Class ID':<10} {'Class Name':<24} {'Precision':<12} {'Recall':<12} {'mAP@50':<12} {'mAP@50-95':<12}")
    print("  " + "-" * 78)
    for i, cname in class_names.items():
        if i < len(results.box.p):
            p = float(results.box.p[i])
            r = float(results.box.r[i])
            ap50 = float(results.box.ap50[i])
            ap = float(results.box.ap[i])
            print(f"  {i:<10} {cname:<24} {p * 100:>8.2f}%   {r * 100:>8.2f}%   {ap50 * 100:>8.2f}%   {ap * 100:>8.2f}%")


def main():
    args = parse_args()
    if not os.path.exists(args.weights):
        # Check alternate standard location
        alt_weights = "runs/detect/baseline/weights/best.pt"
        if os.path.exists(alt_weights):
            args.weights = alt_weights
        else:
            raise FileNotFoundError(f"Model weights file not found at: {args.weights}")

    cuda_avail = torch.cuda.is_available()
    device = args.device if args.device is not None else (0 if cuda_avail else "cpu")

    print(f"Loading weights: {args.weights}")
    model = YOLO(args.weights)

    if args.split in ["val", "both"]:
        evaluate_split(model, "val", args.data, args.imgsz, args.batch, device)

    if args.split in ["test", "both"]:
        evaluate_split(model, "test", args.data, args.imgsz, args.batch, device)


if __name__ == "__main__":
    main()
