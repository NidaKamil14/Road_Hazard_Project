#!/usr/bin/env python3
"""
Road Hazard Detection - Balanced Dataset Preparation
Selects, balances, and creates oversampled training manifest (train.txt)
Combines RDD2022, FloodDET, and RoadworkCones datasets.
"""

import os
import shutil
import random
import time
import argparse
from collections import defaultdict


def parse_args():
    parser = argparse.ArgumentParser(description="Assemble and balance Road Hazard dataset")
    parser.add_argument("--processed_base", type=str, default="Datasets/processed", help="Processed datasets base folder")
    parser.add_argument("--out_base", type=str, default="Datasets/balanced_dataset", help="Output balanced dataset folder")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    return parser.parse_args()


def get_src_paths(processed_base, dataset_name, split):
    d_dir = os.path.join(processed_base, dataset_name)
    img_a = os.path.join(d_dir, split, "images")
    lbl_a = os.path.join(d_dir, split, "labels")
    img_b = os.path.join(d_dir, "images", split)
    lbl_b = os.path.join(d_dir, "labels", split)
    if os.path.exists(img_a) and os.path.exists(lbl_a):
        return img_a, lbl_a
    elif os.path.exists(img_b) and os.path.exists(lbl_b):
        return img_b, lbl_b
    raise FileNotFoundError(f"Missing paths for {dataset_name} {split}")


def main():
    args = parse_args()
    random.seed(args.seed)

    print("=" * 80)
    print("ASSEMBLING BALANCED ROAD HAZARD DATASET")
    print("=" * 80)

    for s in ["train", "val", "test"]:
        os.makedirs(os.path.join(args.out_base, "images", s), exist_ok=True)
        os.makedirs(os.path.join(args.out_base, "labels", s), exist_ok=True)

    # 1. Copy validation and test sets (clean & unskewed evaluation splits)
    print("Copying validation and test sets...")
    for split in ["val", "test"]:
        out_img_dir = os.path.join(args.out_base, "images", split)
        out_lbl_dir = os.path.join(args.out_base, "labels", split)

        for dname, prefix in [("RDD2022", "RDD_"), ("FloodDET", ""), ("RoadworkCones", "Roadwork_")]:
            src_img_dir, src_lbl_dir = get_src_paths(args.processed_base, dname, split)
            files = sorted(os.listdir(src_img_dir))
            print(f"  Copying {dname} {split} ({len(files)} files)...")
            for f in files:
                stem, ext = os.path.splitext(f)
                target_img_name = f"{prefix}{f}" if not f.startswith("Flood_") else f
                target_lbl_name = f"{prefix}{stem}.txt" if not f.startswith("Flood_") else f"{stem}.txt"

                src_img = os.path.join(src_img_dir, f)
                src_lbl = os.path.join(src_lbl_dir, f"{stem}.txt")
                dst_img = os.path.join(out_img_dir, target_img_name)
                dst_lbl = os.path.join(out_lbl_dir, target_lbl_name)

                shutil.copy2(src_img, dst_img)
                if os.path.exists(src_lbl):
                    shutil.copy2(src_lbl, dst_lbl)
                else:
                    open(dst_lbl, "w").close()

    # 2. Select balanced training files
    print("\nBalancing training distribution...")
    rdd_train_img, rdd_train_lbl = get_src_paths(args.processed_base, "RDD2022", "train")
    rdd_files_by_country = defaultdict(lambda: {"crack_only": [], "both": [], "pothole_only": [], "empty": []})

    for f in os.listdir(rdd_train_lbl):
        p = os.path.join(rdd_train_lbl, f)
        with open(p, "r") as fp:
            lines = [l.strip() for l in fp if l.strip()]
        cids = set(int(l.split()[0]) for l in lines)

        country = f.split("_")[0]
        if "China" in f:
            country = "_".join(f.split("_")[:2])
        elif "United" in f:
            country = "United_States"

        stem = os.path.splitext(f)[0]
        if cids == {1}:
            rdd_files_by_country[country]["crack_only"].append(stem)
        elif cids == {0, 1}:
            rdd_files_by_country[country]["both"].append(stem)
        elif cids == {0}:
            rdd_files_by_country[country]["pothole_only"].append(stem)
        elif len(cids) == 0:
            rdd_files_by_country[country]["empty"].append(stem)

    # Subsample crack-only to 2,250 preserving country distribution
    target_crack_only = 2250
    total_crack_only = sum(len(d["crack_only"]) for d in rdd_files_by_country.values())
    selected_crack_only = []
    for country, d in sorted(rdd_files_by_country.items()):
        c_list = d["crack_only"]
        num_to_pick = round(len(c_list) / total_crack_only * target_crack_only)
        picked = random.sample(c_list, min(num_to_pick, len(c_list)))
        selected_crack_only.extend(picked)

    if len(selected_crack_only) > target_crack_only:
        selected_crack_only = selected_crack_only[:target_crack_only]
    elif len(selected_crack_only) < target_crack_only:
        rem = target_crack_only - len(selected_crack_only)
        rem_pool = [x for d in rdd_files_by_country.values() for x in d["crack_only"] if x not in selected_crack_only]
        selected_crack_only.extend(random.sample(rem_pool, rem))

    # Keep all 'both' (1,507) and 'pothole_only' (1,092)
    selected_both = [x for d in rdd_files_by_country.values() for x in d["both"]]
    selected_pothole_only = [x for d in rdd_files_by_country.values() for x in d["pothole_only"]]

    # Sample 799 RDD empty background images
    target_rdd_empty = 799
    total_rdd_empty = sum(len(d["empty"]) for d in rdd_files_by_country.values())
    selected_rdd_empty = []
    for country, d in sorted(rdd_files_by_country.items()):
        e_list = d["empty"]
        if not e_list:
            continue
        num_to_pick = round(len(e_list) / total_rdd_empty * target_rdd_empty)
        picked = random.sample(e_list, min(num_to_pick, len(e_list)))
        selected_rdd_empty.extend(picked)

    if len(selected_rdd_empty) > target_rdd_empty:
        selected_rdd_empty = selected_rdd_empty[:target_rdd_empty]

    # Roadwork Cones
    cones_train_img, cones_train_lbl = get_src_paths(args.processed_base, "RoadworkCones", "train")
    cones_positive, cones_empty = [], []
    for f in os.listdir(cones_train_lbl):
        stem = os.path.splitext(f)[0]
        p = os.path.join(cones_train_lbl, f)
        with open(p, "r") as fp:
            lines = [l.strip() for l in fp if l.strip()]
        if lines:
            cones_positive.append(stem)
        else:
            cones_empty.append(stem)

    selected_cones_positive = list(cones_positive)
    selected_cones_empty = random.sample(cones_empty, min(200, len(cones_empty)))

    # FloodDET
    flood_train_img, flood_train_lbl = get_src_paths(args.processed_base, "FloodDET", "train")
    flood_positive, flood_empty = [], []
    for f in os.listdir(flood_train_lbl):
        stem = os.path.splitext(f)[0]
        p = os.path.join(flood_train_lbl, f)
        with open(p, "r") as fp:
            lines = [l.strip() for l in fp if l.strip()]
        if lines:
            flood_positive.append(stem)
        else:
            flood_empty.append(stem)

    selected_flood_positive = list(flood_positive)
    selected_flood_empty = list(flood_empty)

    train_copy_list = []
    for stem in selected_crack_only:
        train_copy_list.append((stem, rdd_train_img, rdd_train_lbl, "RDD_", "crack_only"))
    for stem in selected_both:
        train_copy_list.append((stem, rdd_train_img, rdd_train_lbl, "RDD_", "both"))
    for stem in selected_pothole_only:
        train_copy_list.append((stem, rdd_train_img, rdd_train_lbl, "RDD_", "pothole_only"))
    for stem in selected_rdd_empty:
        train_copy_list.append((stem, rdd_train_img, rdd_train_lbl, "RDD_", "background_rdd"))
    for stem in selected_cones_positive:
        train_copy_list.append((stem, cones_train_img, cones_train_lbl, "Roadwork_", "barrier_positive"))
    for stem in selected_cones_empty:
        train_copy_list.append((stem, cones_train_img, cones_train_lbl, "Roadwork_", "background_cones"))
    for stem in selected_flood_positive:
        train_copy_list.append((stem, flood_train_img, flood_train_lbl, "", "waterlogging_positive"))
    for stem in selected_flood_empty:
        train_copy_list.append((stem, flood_train_img, flood_train_lbl, "", "background_flood"))

    out_train_img = os.path.join(args.out_base, "images", "train")
    out_train_lbl = os.path.join(args.out_base, "labels", "train")

    print(f"\nCopying {len(train_copy_list)} balanced training files...")
    for stem, s_img_dir, s_lbl_dir, prefix, _ in train_copy_list:
        shutil.copy2(os.path.join(s_img_dir, f"{stem}.jpg"), os.path.join(out_train_img, f"{prefix}{stem}.jpg"))
        lbl_file = os.path.join(s_lbl_dir, f"{stem}.txt")
        dst_lbl = os.path.join(out_train_lbl, f"{prefix}{stem}.txt")
        if os.path.exists(lbl_file):
            shutil.copy2(lbl_file, dst_lbl)
        else:
            open(dst_lbl, "w").close()

    # Generate train.txt with dynamic oversampling
    train_lines = []
    for stem, _, _, prefix, tag in train_copy_list:
        target_img = f"images/train/{prefix}{stem}.jpg"
        if tag == "waterlogging_positive":
            for _ in range(7):  # 7x oversampling for minority waterlogging
                train_lines.append(target_img)
        elif tag == "pothole_only":
            weight = 2 if hash(stem) % 2 == 0 else 1  # 1.5x effective weight
            for _ in range(weight):
                train_lines.append(target_img)
        else:
            train_lines.append(target_img)

    with open(os.path.join(args.out_base, "train.txt"), "w", encoding="utf-8") as f:
        for line in train_lines:
            f.write(line + "\n")

    print(f"Generated train.txt manifest with {len(train_lines)} exposure entries.")
    print("Dataset assembly completed successfully!")


if __name__ == "__main__":
    main()
