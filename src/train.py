#!/usr/bin/env python3
"""
Road Hazard Detection - YOLO11 Baseline Training Script
Detects: Potholes, Road Cracks, Waterlogging, and Construction Barriers.
"""

import os
import sys
import argparse
import time
import torch
from ultralytics import YOLO
import ultralytics


def parse_args():
    parser = argparse.ArgumentParser(description="Train YOLO11 on Road Hazard Dataset")
    parser.add_argument("--data", type=str, default="configs/data.yaml", help="Path to data.yaml")
    parser.add_argument("--model", type=str, default="yolo11n.pt", help="Base model weights or architecture")
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=32, help="Batch size")
    parser.add_argument("--imgsz", type=int, default=640, help="Input image resolution")
    parser.add_argument("--patience", type=int, default=15, help="Early stopping patience")
    parser.add_argument("--device", type=str, default=None, help="Device to run on (e.g. '0', 'cpu')")
    parser.add_argument("--project", type=str, default="runs/detect", help="Output project directory")
    parser.add_argument("--name", type=str, default="baseline", help="Run name")
    parser.add_argument("--workers", type=int, default=4, help="DataLoader worker processes")
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 80)
    print("ROAD HAZARD DETECTION - MODEL TRAINING")
    print("=" * 80)
    print(f"PyTorch Version:     {torch.__version__}")
    print(f"Ultralytics Version: {ultralytics.__version__}")

    cuda_avail = torch.cuda.is_available()
    print(f"CUDA Available:      {cuda_avail}")

    if args.device is not None:
        device = args.device
    else:
        device = 0 if cuda_avail else "cpu"

    if cuda_avail and device != "cpu":
        print(f"Device Name:         {torch.cuda.get_device_name(0)}")
        vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
        print(f"Total VRAM:          {vram_gb} GB")
    else:
        print("Note: Running on CPU.")

    print(f"\nConfiguration:")
    print(f"  Dataset Config:    {args.data}")
    print(f"  Base Model:        {args.model}")
    print(f"  Epochs:            {args.epochs}")
    print(f"  Batch Size:        {args.batch}")
    print(f"  Image Size:        {args.imgsz}")
    print(f"  Patience:          {args.patience}")
    print(f"  Output:            {args.project}/{args.name}")

    # Load model
    print(f"\nInitializing model: {args.model}...")
    model = YOLO(args.model)

    start_time = time.time()

    # Train model with domain-specific augmentations
    # Vertical flips, extreme shears, and perspectives are disabled to preserve road geometry
    results = model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        patience=args.patience,
        device=device,
        pretrained=True,
        project=args.project,
        name=args.name,
        exist_ok=True,
        save=True,
        save_period=-1,
        # Augmentations
        mosaic=1.0,
        mixup=0.15,
        fliplr=0.5,
        scale=0.5,
        flipud=0.0,
        perspective=0.0,
        shear=0.0,
        copy_paste=0.0,
        degrees=0.0,
        plots=True,
        verbose=True,
        workers=args.workers if cuda_avail else 2,
    )

    elapsed = time.time() - start_time
    print(f"\nTraining completed in {elapsed / 60:.2f} minutes ({elapsed:.1f} seconds).")

    best_pt = os.path.join(args.project, args.name, "weights", "best.pt")
    last_pt = os.path.join(args.project, args.name, "weights", "last.pt")
    print(f"Best checkpoint: {best_pt} (Exists: {os.path.exists(best_pt)})")
    print(f"Last checkpoint: {last_pt} (Exists: {os.path.exists(last_pt)})")


if __name__ == "__main__":
    main()
