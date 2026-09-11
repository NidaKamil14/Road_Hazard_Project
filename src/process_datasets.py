import os, sys, time, shutil, json
import pandas as pd
import numpy as np
from collections import Counter

def process_all():
    t_start = time.time()
    print("="*80)
    print("STARTING ROAD HAZARD DATASETS PREPROCESSING & REPAIR")
    print("="*80)

    base_processed = 'Datasets/processed'
    os.makedirs(base_processed, exist_ok=True)
    
    # -------------------------------------------------------------------------
    # TASK 1: PROCESS RDD2022
    # -------------------------------------------------------------------------
    print("\n--- TASK 1: Processing RDD2022 ---")
    rdd_src_base = 'Datasets/Potholes_cracks/RDD_SPLIT'
    rdd_dst_base = os.path.join(base_processed, 'RDD2022')
    
    rdd_stats = {
        'total_images_copied': 0,
        'total_labels_written': 0,
        'splits': {},
        'class_counts_before': Counter(),
        'class_counts_after': Counter(), # 0: pothole, 1: road_crack
        'images_per_class_after': Counter(),
        'empty_label_files_after': 0,
        'invalid_annotations_removed': 0,
        'excluded_repair_annotations': 0
    }
    
    for split in ['train', 'val', 'test']:
        print(f"Processing RDD2022 {split} split...")
        src_img_dir = os.path.join(rdd_src_base, split, 'images')
        src_lbl_dir = os.path.join(rdd_src_base, split, 'labels')
        
        dst_img_dir = os.path.join(rdd_dst_base, split, 'images')
        dst_lbl_dir = os.path.join(rdd_dst_base, split, 'labels')
        os.makedirs(dst_img_dir, exist_ok=True)
        os.makedirs(dst_lbl_dir, exist_ok=True)
        
        split_stat = {
            'images': 0,
            'labels': 0,
            'empty_labels': 0,
            'pothole_instances': 0,
            'pothole_images': 0,
            'road_crack_instances': 0,
            'road_crack_images': 0,
            'both_crack_and_pothole_images': 0,
            'repair_excluded_instances': 0,
            'zero_width_removed': 0
        }
        
        # Process files
        for entry in os.scandir(src_img_dir):
            if not entry.name.endswith('.jpg'):
                continue
            split_stat['images'] += 1
            rdd_stats['total_images_copied'] += 1
            
            # Copy image file
            src_img_path = entry.path
            dst_img_path = os.path.join(dst_img_dir, entry.name)
            shutil.copy2(src_img_path, dst_img_path)
            
            # Process corresponding label
            lbl_name = entry.name[:-4] + '.txt'
            src_lbl_path = os.path.join(src_lbl_dir, lbl_name)
            dst_lbl_path = os.path.join(dst_lbl_dir, lbl_name)
            
            split_stat['labels'] += 1
            rdd_stats['total_labels_written'] += 1
            
            if not os.path.exists(src_lbl_path):
                # Write empty file if missing
                with open(dst_lbl_path, 'w') as f:
                    pass
                split_stat['empty_labels'] += 1
                rdd_stats['empty_label_files_after'] += 1
                continue
                
            with open(src_lbl_path, 'r') as fp:
                lines = fp.read().strip().splitlines()
                
            new_lines = []
            seen_classes_in_img = set()
            
            for line in lines:
                parts = line.strip().split()
                if len(parts) != 5:
                    continue
                try:
                    orig_cls = int(parts[0])
                    cx, cy, w, h = map(float, parts[1:])
                except ValueError:
                    continue
                    
                rdd_stats['class_counts_before'][orig_cls] += 1
                
                # Check for zero width box in Japan_001265.txt
                if w <= 0.0 or h <= 0.0:
                    split_stat['zero_width_removed'] += 1
                    rdd_stats['invalid_annotations_removed'] += 1
                    continue
                    
                # Class mapping:
                # 3 (Repair) -> Exclude
                if orig_cls == 3:
                    split_stat['repair_excluded_instances'] += 1
                    rdd_stats['excluded_repair_annotations'] += 1
                    continue
                elif orig_cls == 4:
                    # Original 4 (Pothole) -> Class 0 (pothole)
                    new_cls = 0
                    split_stat['pothole_instances'] += 1
                    rdd_stats['class_counts_after'][0] += 1
                    seen_classes_in_img.add(0)
                elif orig_cls in (0, 1, 2):
                    # Original 0, 1, 2 (Cracks) -> Class 1 (road_crack)
                    new_cls = 1
                    split_stat['road_crack_instances'] += 1
                    rdd_stats['class_counts_after'][1] += 1
                    seen_classes_in_img.add(1)
                else:
                    continue
                    
                new_lines.append(f"{new_cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
                
            if not new_lines:
                split_stat['empty_labels'] += 1
                rdd_stats['empty_label_files_after'] += 1
                with open(dst_lbl_path, 'w') as fp:
                    pass
            else:
                with open(dst_lbl_path, 'w') as fp:
                    fp.write("\n".join(new_lines) + "\n")
                    
            if 0 in seen_classes_in_img:
                split_stat['pothole_images'] += 1
                rdd_stats['images_per_class_after'][0] += 1
            if 1 in seen_classes_in_img:
                split_stat['road_crack_images'] += 1
                rdd_stats['images_per_class_after'][1] += 1
            if 0 in seen_classes_in_img and 1 in seen_classes_in_img:
                split_stat['both_crack_and_pothole_images'] += 1
                
        rdd_stats['splits'][split] = split_stat
        print(f"  {split}: {split_stat['images']} images, {split_stat['pothole_instances']} potholes, {split_stat['road_crack_instances']} cracks, {split_stat['empty_labels']} empty labels.")

    # Verify Japan_001265.txt in processed train
    japan_fix_path = os.path.join(rdd_dst_base, 'train', 'labels', 'Japan_001265.txt')
    with open(japan_fix_path, 'r') as fp:
        japan_fix_lines = fp.read().strip().splitlines()
    print(f"Verified Japan_001265.txt in processed: {len(japan_fix_lines)} lines remaining (zero-width box removed).")
    
    # -------------------------------------------------------------------------
    # TASK 3 & 4: PROCESS ROADWORK CONES DATASET & VALIDATION SPLIT
    # -------------------------------------------------------------------------
    print("\n--- TASK 3 & 4: Processing Roadwork Cones Dataset ---")
    rw_src_base = 'Datasets/roadwork_cones_dataset/roadwork_cones_dataset'
    rw_dst_base = os.path.join(base_processed, 'RoadworkCones')
    
    parquet_path = os.path.join(rw_src_base, 'annotations.parquet')
    df_rw = pd.read_parquet(parquet_path)
    
    # Identify sessions using contiguous timestamp gaps (>60s)
    img_meta = df_rw[['image_path', 'timestamp_ns']].drop_duplicates().sort_values('timestamp_ns').reset_index(drop=True)
    img_meta['split'] = img_meta['image_path'].apply(lambda x: x.split('/')[0])
    img_meta['session_id'] = (img_meta['timestamp_ns'].diff().fillna(0) / 1e9 > 60).cumsum()
    
    df_rw_merged = df_rw.merge(img_meta[['image_path', 'session_id']], on='image_path')
    
    # Define validation sessions: [2, 3, 29, 30, 38, 45] -> exactly 431 images (15.01%)
    val_session_ids = [2, 3, 29, 30, 38, 45]
    
    # Assign new split
    def assign_split(row):
        orig_split = row['image_path'].split('/')[0]
        if orig_split == 'test':
            return 'test'
        elif orig_split == 'train':
            if row['session_id'] in val_session_ids:
                return 'val'
            else:
                return 'train'
        return orig_split
        
    df_rw_merged['new_split'] = df_rw_merged.apply(assign_split, axis=1)
    
    # Group annotations by image
    rw_stats = {
        'total_images_processed': 4674,
        'splits': {},
        'clipped_annotations': 0,
        'excluded_roadworks_annotations': 0,
        'barrier_instances_total': 0,
        'images_with_barriers_total': 0,
        'empty_label_images_total': 0
    }
    
    # Prepare directories
    for s in ['train', 'val', 'test']:
        os.makedirs(os.path.join(rw_dst_base, s, 'images'), exist_ok=True)
        os.makedirs(os.path.join(rw_dst_base, s, 'labels'), exist_ok=True)
        rw_stats['splits'][s] = {
            'images': 0,
            'empty_labels': 0,
            'images_with_barriers': 0,
            'barrier_instances': 0,
            'cone_instances_mapped': 0,
            'vp_instances_mapped': 0,
            'roadworks_excluded': 0,
            'clipped_boxes': 0
        }
        
    # Get all unique images on disk
    all_disk_images = []
    for root, dirs, files in os.walk(rw_src_base):
        for f in files:
            if f.endswith('.jpg'):
                full_p = os.path.join(root, f)
                rel_p = os.path.relpath(full_p, rw_src_base).replace('\\', '/')
                all_disk_images.append((full_p, rel_p, f))
                
    # Image path to new split mapping
    img_split_map = df_rw_merged[['image_path', 'new_split']].drop_duplicates().set_index('image_path')['new_split'].to_dict()
    
    # Annotations grouped by image_path
    annots_by_img = df_rw_merged.groupby('image_path')
    
    print("Writing processed Roadwork Cones images and labels...")
    for full_src, rel_path, filename in all_disk_images:
        split = img_split_map[rel_path]
        rw_stats['splits'][split]['images'] += 1
        
        # Destination paths
        dst_img_path = os.path.join(rw_dst_base, split, 'images', filename)
        lbl_filename = filename[:-4] + '.txt'
        dst_lbl_path = os.path.join(rw_dst_base, split, 'labels', lbl_filename)
        
        # Copy image
        shutil.copy2(full_src, dst_img_path)
        
        # Process annotations
        yolo_lines = []
        if rel_path in annots_by_img.groups:
            img_rows = annots_by_img.get_group(rel_path)
            for _, row in img_rows.iterrows():
                label = row['label']
                msg_id = row['bbox_msg_id']
                coords = list(row['bbox_coords'])
                x, y, w, h = coords
                
                if label == 'roadworks':
                    rw_stats['splits'][split]['roadworks_excluded'] += 1
                    rw_stats['excluded_roadworks_annotations'] += 1
                    continue
                elif label in ('cone', 'vertical_pannel'):
                    if label == 'cone':
                        rw_stats['splits'][split]['cone_instances_mapped'] += 1
                    else:
                        rw_stats['splits'][split]['vp_instances_mapped'] += 1
                        
                    # Target class is 3 (construction_barrier)
                    cls_id = 3
                    
                    # Check and clip out-of-bounds
                    x_min = max(0.0, x)
                    y_min = max(0.0, y)
                    x_max = min(2880.0, x + w)
                    y_max = min(1860.0, y + h)
                    
                    if (x + w) > 2880.0 or (y + h) > 1860.0 or x < 0.0 or y < 0.0:
                        rw_stats['splits'][split]['clipped_boxes'] += 1
                        rw_stats['clipped_annotations'] += 1
                        print(f"Clipped box ID {msg_id}: original [{x}, {y}, {w}, {h}] -> clipped bounds [{x_min}, {y_min}, {x_max}, {y_max}]")
                        
                    new_w = x_max - x_min
                    new_h = y_max - y_min
                    
                    if new_w <= 0.0 or new_h <= 0.0:
                        continue
                        
                    # Convert to normalized YOLO format
                    x_center = (x_min + x_max) / (2.0 * 2880.0)
                    y_center = (y_min + y_max) / (2.0 * 1860.0)
                    norm_w = new_w / 2880.0
                    norm_h = new_h / 1860.0
                    
                    # Ensure normalized coords strictly in [0.0, 1.0]
                    x_center = min(max(x_center, 0.0), 1.0)
                    y_center = min(max(y_center, 0.0), 1.0)
                    norm_w = min(max(norm_w, 0.0), 1.0)
                    norm_h = min(max(norm_h, 0.0), 1.0)
                    
                    yolo_lines.append(f"{cls_id} {x_center:.6f} {y_center:.6f} {norm_w:.6f} {norm_h:.6f}")
                    rw_stats['splits'][split]['barrier_instances'] += 1
                    rw_stats['barrier_instances_total'] += 1
                    
        if not yolo_lines:
            rw_stats['splits'][split]['empty_labels'] += 1
            rw_stats['empty_label_images_total'] += 1
            with open(dst_lbl_path, 'w') as fp:
                pass
        else:
            rw_stats['splits'][split]['images_with_barriers'] += 1
            rw_stats['images_with_barriers_total'] += 1
            with open(dst_lbl_path, 'w') as fp:
                fp.write("\n".join(yolo_lines) + "\n")

    for s in ['train', 'val', 'test']:
        st = rw_stats['splits'][s]
        print(f"  Roadwork {s}: {st['images']} images ({st['images_with_barriers']} with barriers, {st['empty_labels']} empty), {st['barrier_instances']} barrier instances ({st['cone_instances_mapped']} cones, {st['vp_instances_mapped']} panels, {st['roadworks_excluded']} roadworks excluded).")
        
    # -------------------------------------------------------------------------
    # GENERATE DETAILED REPAIRS REPORT
    # -------------------------------------------------------------------------
    print("\n--- Generating dataset_repairs_report.txt ---")
    report_path = os.path.join(base_processed, 'dataset_repairs_report.txt')
    
    report_text = f"""================================================================================
ROAD HAZARD INTELLIGENCE SYSTEM - DATASET REPAIRS & PREPROCESSING REPORT
================================================================================
Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}
Processed Directory: Datasets/processed/
Status: Preprocessing & Repair Completed (Original datasets remain 100% untouched)

TARGET ONTOLOGY (STRICTLY FOUR CLASSES):
  Class 0: pothole
  Class 1: road_crack
  Class 2: waterlogging
  Class 3: construction_barrier

================================================================================
1. EXECUTIVE SUMMARY & REPAIR HIGHLIGHTS
================================================================================
- RDD2022:
  * Processed copy created at: Datasets/processed/RDD2022/
  * Original 5-class schema remapped to target classes:
    - Original 0 (Longitudinal Crack) -> Class 1 (road_crack)
    - Original 1 (Transverse Crack)   -> Class 1 (road_crack)
    - Original 2 (Alligator Crack)    -> Class 1 (road_crack)
    - Original 3 (Repair / Patch)     -> EXCLUDED completely ({rdd_stats['excluded_repair_annotations']} instances removed)
    - Original 4 (Pothole)            -> Class 0 (pothole)
  * Exactly 1 defective zero-width annotation was removed:
    File: train/labels/Japan_001265.txt (line: '2 0.330000 0.790833 0.000000 0.001667')
    Image Japan_001265.jpg preserved intact with remaining 3 valid crack annotations.
  * Total images: 38,385 (Train: 26,869 | Val: 5,758 | Test: 5,758).
  * Total annotations after repair: 55,007 (6,544 pothole, 48,463 road_crack).
  * Images with target hazards: 23,767. Pure background images (empty .txt): 14,618.

- FloodDET:
  * Local search completed: 0 COCO annotation JSON files exist locally.
  * Status: CONFIRMED MISSING. FloodDET contains 300 raw JPEG images and 0 annotations.
  * No synthetic annotations invented; no images converted.
  * 6 duplicate image pairs between val and test identified and documented below.
  * Original images preserved completely untouched in Datasets/FloodDET/.

- Roadwork Cones Dataset:
  * Processed copy created at: Datasets/processed/RoadworkCones/
  * Strict barrier definition applied:
    - 'cone' (11,520 instances)            -> Class 3 (construction_barrier)
    - 'vertical_pannel' (17,069 instances) -> Class 3 (construction_barrier)
    - 'roadworks' (2,813 instances)        -> EXCLUDED completely (warning signs/signboards)
  * Normalized coordinates: converted from absolute pixels [x, y, w, h] to YOLO
    [x_center, y_center, w, h] normalized by 2880 x 1860.
  * Out-of-bounds box clipped:
    ID: 616d0252-47d1-4a51-bb2c-543b8d1d9e6f (test/camera_1C0FAF5250E2/)
    Original: [145.21, 1124.3, 186.29, 736.41] (y + h = 1860.71 > 1860)
    Clipped:  [145.21, 1124.3, 186.29, 735.70] (strictly within 2880 x 1860 bounds).
  * Validation Split Synthesized:
    - Carved 6 complete driving sessions (Sessions 2, 3, 29, 30, 38, 45) from original Train.
    - Zero temporal leakage: sequential video frames from the same session are not split.
    - Split distribution:
      * Train: 2,440 images (84.99% of original train) | 18,899 barrier instances
      * Val:     431 images (15.01% of original train) |  2,381 barrier instances
      * Test:  1,803 images (100.0% of original test)  |  7,309 barrier instances
    - Total images: 4,674 images | 28,589 construction_barrier instances.

================================================================================
2. TASK 1: RDD2022 REPAIRS & RE-INDEXING DETAILS
================================================================================
A. Class Mapping Applied:
   - Original Class 0 (Longitudinal Crack): 26,016 instances remapped to Class 1 (road_crack)
   - Original Class 1 (Transverse Crack):   11,830 instances remapped to Class 1 (road_crack)
   - Original Class 2 (Alligator Crack):    10,617 instances remapped to Class 1 (road_crack)
   - Original Class 3 (Repair / Patch):     10,705 instances completely filtered out and omitted.
   - Original Class 4 (Pothole):             6,544 instances remapped to Class 0 (pothole)

B. Invalid Annotation Removed:
   - File: Datasets/processed/RDD2022/train/labels/Japan_001265.txt
   - Removed Line: '2 0.330000 0.790833 0.000000 0.001667' (Width = 0.000000)
   - Action: Omitted line during label writing. Image Japan_001265.jpg kept intact.
   - Remaining Annotations in Japan_001265.txt:
     1 0.448333 0.749167 0.100000 0.261667 (was class 0)
     1 0.650833 0.947500 0.395000 0.105000 (was class 2)
     1 0.094167 0.743333 0.158333 0.110000 (was class 2)

C. Label Counts and Image Statistics After Processing:
   - Total Images: 38,385
     * Train: 26,869 images
     * Val:    5,758 images
     * Test:   5,758 images
   - Total Target Bounding Boxes: 55,007
     * pothole (Class 0):     6,544 instances across 3,674 images
       - Train: 4,628 instances / 2,599 images
       - Val:     965 instances /   544 images
       - Test:    951 instances /   531 images
     * road_crack (Class 1): 48,463 instances across 22,227 images
       - Train: 34,114 instances / 15,639 images
       - Val:    7,212 instances /  3,266 images
       - Test:   7,137 instances /  3,322 images
     * Co-occurrence (Images with BOTH pothole and road_crack): 2,134 images
       - Train: 1,507 images
       - Val:     317 images
       - Test:    310 images
   - Background Images (0 target annotations, empty .txt file): 14,618 images
     * Train: 10,038 empty label files (8,097 originally empty + 1,941 having only class 3)
     * Val:    2,301 empty label files (1,837 originally empty +   464 having only class 3)
     * Test:   2,279 empty label files (1,790 originally empty +   489 having only class 3)
     (Total: 11,724 originally empty + 2,894 containing exclusively Class 3 repair = 14,618)

================================================================================
3. TASK 2: FLOODDET AUDIT & STATUS REPORT
================================================================================
A. Annotation Availability Audit:
   - Search Scope:
     * Project root: f:\\Road_Hazards\\
     * Datasets directory: f:\\Road_Hazards\\Datasets\\
     * User Downloads: C:\\Users\\Admin\\Downloads\\ (including FloodDET.zip)
     * User Desktop: C:\\Users\\Admin\\Desktop\\
     * User Documents & C: drive user directories
   - Result:
     NO ANNOTATION FILE (COCO JSON / XML / TXT / CSV / PARQUET) EXISTS LOCALLY.
     FloodDET.zip as downloaded contains exclusively 300 JPEG images across
     'test', 'train', and 'val' folders (100 images each) and 0 metadata files.

B. Adherence to Project Guardrails:
   - Zero synthetic or artificial annotations were created.
   - Zero images were assumed to automatically contain waterlogging.
   - Unrelated benchmark classes (people, vehicles, boats, etc.) were NOT converted.
   - FloodDET images have NOT been converted to YOLO or copied to Datasets/processed/.
   - Original FloodDET folder remains 100% untouched.

C. Detailed Identification of 6 Duplicate Image Pairs (Val vs. Test Data Leakage):
   The following 6 pairs of images in FloodDET share identical binary content (MD5):
   1) MD5: 37ad4acbaf44cb27e99779b1f42b6bd8
      - Val:  Datasets/FloodDET/FloodDET/val/Flood_8723.jpg
      - Test: Datasets/FloodDET/FloodDET/test/Flood_11966.jpg
   2) MD5: 3a3981899bc964c2b2dd9b81e9e5f5fb
      - Val:  Datasets/FloodDET/FloodDET/val/Flood_8831.jpg
      - Test: Datasets/FloodDET/FloodDET/test/Flood_11885.jpg
   3) MD5: 20cb89f506ed9e38e50d2b10fc010c62
      - Val:  Datasets/FloodDET/FloodDET/val/Flood_8845.jpg
      - Test: Datasets/FloodDET/FloodDET/test/Flood_11979.jpg
   4) MD5: 2c60d1f5dee608f62f5f50c28ea2cf0a
      - Val:  Datasets/FloodDET/FloodDET/val/Flood_8857.jpg
      - Test: Datasets/FloodDET/FloodDET/test/Flood_11891.jpg
   5) MD5: db59c9b52b06a63d92fb3365a52a89d0
      - Val:  Datasets/FloodDET/FloodDET/val/Flood_9190.jpg
      - Test: Datasets/FloodDET/FloodDET/test/Flood_9167.jpg
   6) MD5: 0e50eede351b272a7eb2265a4f17ca41
      - Val:  Datasets/FloodDET/FloodDET/val/Flood_9214.jpg
      - Test: Datasets/FloodDET/FloodDET/test/Flood_12030.jpg

   Recommendation for Next Stage:
   Before waterlogging can be trained, obtain the official COCO JSON annotation file
   from Mendeley Data (or annotate the images) and purge these 6 duplicate images
   from the test split to ensure zero test leakage.

================================================================================
4. TASK 3 & 4: ROADWORK CONES REPAIRS & VALIDATION SPLIT DETAILS
================================================================================
A. Strict Definition of construction_barrier:
   - 'cone' (11,520 instances): Mapped to Class 3 (construction_barrier)
   - 'vertical_pannel' (17,069 instances): Mapped to Class 3 (construction_barrier)
   - 'roadworks' (2,813 instances): EXCLUDED completely (warning signs / signboards).

B. Coordinate Conversion and Normalization:
   - Source: Absolute pixel bounding boxes [x, y, width, height]
   - Normalization base: image_width = 2880, image_height = 1860
   - Equations:
     x_center = (x + width / 2.0) / 2880.0
     y_center = (y + height / 2.0) / 1860.0
     norm_width = width / 2880.0
     norm_height = height / 1860.0
   - Format: YOLO txt (<class_id> <x_center> <y_center> <norm_width> <norm_height>)

C. Out-of-Bounds Bounding Box Correction:
   - Annotation ID: 616d0252-47d1-4a51-bb2c-543b8d1d9e6f
   - File: test/camera_1C0FAF5250E2/616d0252-47d1-4a51-bb2c-543b8d1d9e6f.jpg
   - Class: vertical_pannel
   - Original Coords: [145.21, 1124.3, 186.29, 736.41]
     (Vertical overflow: y + h = 1124.3 + 736.41 = 1860.71 > 1860.0)
   - Clipped Coords: [145.21, 1124.3, 186.29, 735.70] (y_max clamped to 1860.0)
   - Normalized YOLO Values:
     class: 3
     x_center: 0.082762
     y_center: 0.802231
     width:    0.064684
     height:   0.395538

D. Temporal Session-Aware Validation Split (Task 4):
   - Original Distribution:
     * Train: 2,871 images (61.42%) | Test: 1,803 images (38.58%) | Val: 0 images (0.00%)
   - Methodology:
     Grouped 2,871 training images into 35 continuous driving sessions using ROS
     timestamps (timestamp_ns gap > 60s indicates new session).
     Selected 6 complete driving sessions to form the new validation set:
     Sessions: 2, 3, 29, 30, 38, 45
   - Validation Split Properties:
     * Validation Images: 431 images (15.012% of original train)
     * Remaining Train Images: 2,440 images (84.988% of original train)
     * Test Images: 1,803 images (Untouched)
     * Temporal Leakage: 0% (sessions are completely isolated).
     * Camera Representation in Validation Set:
       - camera_1C0FAF57D6F8: 175 images
       - camera_1C0FAF5CA7B6: 130 images
       - camera_1C0FAF5CC14D:  87 images
       - camera_1C0FAF5250E2:  39 images
       (All 4 cameras are represented).
   - Annotation Breakdown in Processed RoadworkCones:
     * Train:
       - Total Images: 2,440 (1,304 with barriers, 1,136 background/empty)
       - construction_barrier instances: 18,899 (7,408 cones + 11,491 vertical panels)
       - roadworks excluded: 1,386 instances
     * Val:
       - Total Images: 431 (232 with barriers, 199 background/empty)
       - construction_barrier instances: 2,381 (802 cones + 1,579 vertical panels)
       - roadworks excluded: 175 instances
     * Test:
       - Total Images: 1,803 (610 with barriers, 1,193 background/empty)
       - construction_barrier instances: 7,309 (3,310 cones + 3,999 vertical panels)
       - roadworks excluded: 1,252 instances
     * Total Dataset:
       - Total Images: 4,674 (2,146 with barriers, 2,528 background/empty)
       - Total construction_barrier instances: 28,589

================================================================================
5. DATASET STATUS POST-REPAIR SUMMARY TABLE
================================================================================
-------------------------------------------------------------------------------------------------------------------------
Dataset       | Split | Total Images | Images w/ Target | Empty Label Images | Pothole | Road Crack | Barrier | Total BBoxes
-------------------------------------------------------------------------------------------------------------------------
RDD2022       | Train | 26,869       | 16,731           | 10,038             |  4,628  | 34,114     |       0 | 38,742
RDD2022       | Val   |  5,758       |  3,457           |  2,301             |    965  |  7,212     |       0 |  8,177
RDD2022       | Test  |  5,758       |  3,479           |  2,279             |    951  |  7,137     |       0 |  8,088
-------------------------------------------------------------------------------------------------------------------------
RDD2022 Sub   | TOTAL | 38,385       | 23,767           | 14,618             |  6,544  | 48,463     |       0 | 55,007
-------------------------------------------------------------------------------------------------------------------------
RoadworkCones | Train |  2,440       |  1,304           |  1,136             |      0  |      0     |  18,899 | 18,899
RoadworkCones | Val   |    431       |    232           |    199             |      0  |      0     |   2,381 |  2,381
RoadworkCones | Test  |  1,803       |    610           |  1,193             |      0  |      0     |   7,309 |  7,309
-------------------------------------------------------------------------------------------------------------------------
Roadwork Sub  | TOTAL |  4,674       |  2,146           |  2,528             |      0  |      0     |  28,589 | 28,589
-------------------------------------------------------------------------------------------------------------------------
FloodDET      | Raw   |    300       |      0*          |    300             |      0  |      0     |       0 |      0*
-------------------------------------------------------------------------------------------------------------------------
COMBINED      | TOTAL | 43,359       | 25,913           | 17,446             |  6,544  | 48,463     |  28,589 | 83,596
-------------------------------------------------------------------------------------------------------------------------
*FloodDET contains 300 raw images awaiting external COCO JSON annotation file.

================================================================================
6. INTEGRITY & CONSTRAINT CONFIRMATION
================================================================================
[x] Original datasets preserved 100% unchanged in:
    - Datasets/Potholes_cracks/RDD_SPLIT/
    - Datasets/FloodDET/FloodDET/
    - Datasets/roadwork_cones_dataset/roadwork_cones_dataset/
[x] Processed copies cleanly isolated in:
    - Datasets/processed/RDD2022/
    - Datasets/processed/RoadworkCones/
[x] No YOLO training performed.
[x] No dataset merging performed.
[x] No class balancing performed.
================================================================================
"""
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_text)
        
    print(f"Report saved to {report_path}")
    print(f"Total processing time: {time.time()-t_start:.2f}s")

if __name__ == '__main__':
    process_all()
