#!/usr/bin/env python3
"""
Road Hazard Detection - Experiment 3 Training Script
Model: YOLO11s
Dataset: 53,521 images (merged_dataset: RDD2022 + FloodDET Waterlogging + ROADWork)
Image Size: 800x800
Epochs: 100
Patience: 20
Output: runs/detect/experiment3_yolo11s_800/
"""

import os
import sys
import json
import time
from pathlib import Path
import torch
from ultralytics import YOLO

def main():
    print("=" * 80)
    print("STARTING EXPERIMENT 3 TRAINING: YOLO11s (800x800, 100 Epochs)")
    print("=" * 80)
    
    # 1. Hardware & Environment Check
    print(f"PyTorch Version: {torch.__version__}")
    cuda_avail = torch.cuda.is_available()
    print(f"CUDA Available:  {cuda_avail}")
    if not cuda_avail:
        print("ERROR: CUDA is not available. Training must run on NVIDIA GPU.")
        sys.exit(1)
        
    device_name = torch.cuda.get_device_name(0)
    total_vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    free_vram = torch.cuda.mem_get_info()[0] / (1024**3)
    print(f"GPU Device:      {device_name}")
    print(f"VRAM Total:      {total_vram:.2f} GB")
    print(f"VRAM Free:       {free_vram:.2f} GB")
    
    # Safe batch size selection for 16 GB VRAM at 800x800
    batch_size = 16 if free_vram >= 10.0 else 8
    print(f"Selected Batch:  {batch_size} (Safe allocation for {free_vram:.1f} GB free VRAM)")
    
    # 2. Paths
    workspace_root = Path(r"F:\Road_Hazards")
    data_yaml = workspace_root / "Datasets/experiment3_dataset/merged_dataset/data.yaml"
    project_dir = workspace_root / "runs/detect"
    run_name = "experiment3_yolo11s_800"
    exp_dir = project_dir / run_name
    
    print(f"Data YAML:       {data_yaml}")
    print(f"Output Run Dir:  {exp_dir}")
    assert data_yaml.exists(), f"data.yaml not found at {data_yaml}"
    
    # 3. Model Initialization
    print(f"\nInitializing base model: yolo11s.pt...")
    model = YOLO("yolo11s.pt")
    
    # 4. Training
    t_start = time.time()
    print("\nStarting model training...")
    train_results = model.train(
        data=str(data_yaml),
        epochs=100,
        imgsz=800,
        batch=batch_size,
        patience=20,
        device=0,
        pretrained=True,
        project=str(project_dir),
        name=run_name,
        exist_ok=True,
        save=True,
        save_period=-1,
        # Augmentations matching Experiment 2
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
        workers=4,
        cache=False
    )
    t_train = time.time() - t_start
    print(f"\nTraining completed in {t_train/3600:.2f} hours ({t_train:.1f} seconds).")
    
    best_weights = exp_dir / "weights" / "best.pt"
    assert best_weights.exists(), f"best.pt not found at {best_weights}"
    print(f"Best checkpoint saved at: {best_weights}")
    
    # 5. Validation Evaluation on Best Model
    print("\n" + "=" * 80)
    print("EVALUATING BEST MODEL ON EXPERIMENT 3 VALIDATION SET")
    print("=" * 80)
    best_model = YOLO(str(best_weights))
    val_results = best_model.val(
        data=str(data_yaml),
        split="val",
        imgsz=800,
        batch=batch_size,
        device=0,
        plots=True
    )
    
    # 6. Test Set Evaluation on Best Model (Untouched Test Set)
    print("\n" + "=" * 80)
    print("EVALUATING BEST MODEL ON UNTOUCHED EXPERIMENT 3 TEST SET")
    print("=" * 80)
    test_results = best_model.val(
        data=str(data_yaml),
        split="test",
        imgsz=800,
        batch=batch_size,
        device=0,
        plots=True
    )
    
    # 7. Collect and Save Metrics Summary
    class_map = {0: "pothole", 1: "road_crack", 2: "waterlogging", 3: "construction_barrier"}
    
    def extract_metrics(res):
        p = [float(x) for x in res.box.p]
        r = [float(x) for x in res.box.r]
        ap50 = [float(x) for x in res.box.ap50]
        ap = [float(x) for x in res.box.ap]
        
        per_class = {}
        for cid, cname in class_map.items():
            if cid < len(p):
                per_class[cname] = {
                    "precision": p[cid],
                    "recall": r[cid],
                    "map50": ap50[cid],
                    "map50_95": ap[cid]
                }
        return {
            "overall": {
                "precision": float(res.box.mp),
                "recall": float(res.box.mr),
                "map50": float(res.box.map50),
                "map50_95": float(res.box.map)
            },
            "per_class": per_class
        }
        
    val_metrics = extract_metrics(val_results)
    test_metrics = extract_metrics(test_results)
    
    summary = {
        "model": "YOLO11s",
        "imgsz": 800,
        "epochs_requested": 100,
        "batch_size": batch_size,
        "training_time_seconds": t_train,
        "gpu": device_name,
        "val": val_metrics,
        "test": test_metrics
    }
    
    metrics_path = exp_dir / "metrics_summary.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nMetrics summary saved to: {metrics_path}")
    
    # 8. Print Executive Summary
    print("\n" + "=" * 80)
    print("EXPERIMENT 3 FINAL EVALUATION RESULTS")
    print("=" * 80)
    print(f"Validation mAP@50:    {val_metrics['overall']['map50']*100:.2f}%")
    print(f"Validation mAP@50-95: {val_metrics['overall']['map50_95']*100:.2f}%")
    print(f"Test mAP@50:          {test_metrics['overall']['map50']*100:.2f}%")
    print(f"Test mAP@50-95:       {test_metrics['overall']['map50_95']*100:.2f}%")
    print("=" * 80)

if __name__ == "__main__":
    main()
