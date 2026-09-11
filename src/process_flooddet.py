import os
import shutil
import json
from PIL import Image

SRC_IMG_BASE = r"f:\Road_Hazards\Datasets\FloodDET\FloodDET"
SRC_ANNO_BASE = r"f:\Road_Hazards\Datasets\FloodDET\annotations_source"
OUT_BASE = r"f:\Road_Hazards\Datasets\processed\FloodDET"

DUPLICATES_TO_REMOVE = {
    "Flood_11966.jpg": ("val/Flood_8723.jpg", "37ad4acbaf44cb27e99779b1f42b6bd8"),
    "Flood_11885.jpg": ("val/Flood_8831.jpg", "3a3981899bc964c2b2dd9b81e9e5f5fb"),
    "Flood_11979.jpg": ("val/Flood_8845.jpg", "20cb89f506ed9e38e50d2b10fc010c62"),
    "Flood_11891.jpg": ("val/Flood_8857.jpg", "2c60d1f5dee608f62f5f50c28ea2cf0a"),
    "Flood_9167.jpg":  ("val/Flood_9190.jpg", "db59c9b52b06a63d92fb3365a52a89d0"),
    "Flood_12030.jpg": ("val/Flood_9214.jpg", "0e50eede351b272a7eb2265a4f17ca41"),
}

splits = ['train', 'val', 'test']

# 1. Create directory structure
for s in splits:
    os.makedirs(os.path.join(OUT_BASE, "images", s), exist_ok=True)
    os.makedirs(os.path.join(OUT_BASE, "labels", s), exist_ok=True)

stats = {
    "source_images": {},
    "copied_images": {},
    "processed_images": {},
    "annotations_flood": {},
    "annotations_excluded": {},
    "clamped_boxes": [],
    "negative_images": {},
    "duplicates_removed": []
}

for s in splits:
    json_path = os.path.join(SRC_ANNO_BASE, f"{s}.json")
    with open(json_path, 'r', encoding='utf-8') as f:
        coco = json.load(f)
        
    src_img_dir = os.path.join(SRC_IMG_BASE, s)
    dst_img_dir = os.path.join(OUT_BASE, "images", s)
    dst_lbl_dir = os.path.join(OUT_BASE, "labels", s)
    
    local_files = sorted(os.listdir(src_img_dir))
    stats["source_images"][s] = len(local_files)
    
    # Map filename -> coco image
    filename_to_img = {img['file_name']: img for img in coco['images']}
    
    # Map image_id -> list of annotations
    img_id_to_annos = {}
    for ann in coco['annotations']:
        img_id_to_annos.setdefault(ann['image_id'], []).append(ann)
        
    flood_count = 0
    excluded_count = 0
    neg_count = 0
    
    for fname in local_files:
        # Copy image to processed folder
        src_path = os.path.join(src_img_dir, fname)
        dst_path = os.path.join(dst_img_dir, fname)
        shutil.copy2(src_path, dst_path)
        
        coco_img = filename_to_img[fname]
        iid = coco_img['id']
        img_w = float(coco_img['width'])
        img_h = float(coco_img['height'])
        
        annos = img_id_to_annos.get(iid, [])
        yolo_lines = []
        
        for a in annos:
            cid = a['category_id']
            if cid == 45: # 'flood'
                x_min, y_min, w, h = a['bbox']
                orig_bbox = list(a['bbox'])
                x_max = x_min + w
                y_max = y_min + h
                
                # Boundary clamping
                clamped_x_min = max(0.0, min(x_min, img_w))
                clamped_y_min = max(0.0, min(y_min, img_h))
                clamped_x_max = max(0.0, min(x_max, img_w))
                clamped_y_max = max(0.0, min(y_max, img_h))
                
                new_w = clamped_x_max - clamped_x_min
                new_h = clamped_y_max - clamped_y_min
                
                is_clamped = (clamped_x_min != x_min or clamped_y_min != y_min or 
                              clamped_x_max != x_max or clamped_y_max != y_max)
                if is_clamped:
                    stats["clamped_boxes"].append({
                        "split": s,
                        "file": fname,
                        "anno_id": a['id'],
                        "orig_bbox": orig_bbox,
                        "clamped_bbox": [clamped_x_min, clamped_y_min, new_w, new_h],
                        "img_size": [img_w, img_h]
                    })
                    
                if new_w <= 0 or new_h <= 0:
                    print(f"Warning: zero box after clamp in {fname}: {a}")
                    continue
                    
                x_center = (clamped_x_min + new_w / 2.0) / img_w
                y_center = (clamped_y_min + new_h / 2.0) / img_h
                norm_w = new_w / img_w
                norm_h = new_h / img_h
                
                # YOLO class 2 = waterlogging
                yolo_lines.append(f"2 {x_center:.6f} {y_center:.6f} {norm_w:.6f} {norm_h:.6f}\n")
                flood_count += 1
            else:
                excluded_count += 1
                
        # Write YOLO label file
        txt_name = os.path.splitext(fname)[0] + ".txt"
        txt_path = os.path.join(dst_lbl_dir, txt_name)
        with open(txt_path, 'w', encoding='utf-8') as out_f:
            out_f.writelines(yolo_lines)
            
        if len(yolo_lines) == 0:
            neg_count += 1
            
    stats["copied_images"][s] = len(local_files)
    stats["annotations_flood"][s] = flood_count
    stats["annotations_excluded"][s] = excluded_count
    stats["negative_images"][s] = neg_count

# TASK 6: Remove the 6 duplicate test images and their labels
test_img_dir = os.path.join(OUT_BASE, "images", "test")
test_lbl_dir = os.path.join(OUT_BASE, "labels", "test")

for dup_name, (val_counterpart, md5_hash) in DUPLICATES_TO_REMOVE.items():
    dup_img_path = os.path.join(test_img_dir, dup_name)
    dup_lbl_path = os.path.join(test_lbl_dir, os.path.splitext(dup_name)[0] + ".txt")
    
    img_removed = False
    lbl_removed = False
    if os.path.exists(dup_img_path):
        os.remove(dup_img_path)
        img_removed = True
    if os.path.exists(dup_lbl_path):
        os.remove(dup_lbl_path)
        lbl_removed = True
        
    stats["duplicates_removed"].append({
        "test_image": dup_name,
        "val_counterpart": val_counterpart,
        "md5": md5_hash,
        "img_removed": img_removed,
        "lbl_removed": lbl_removed
    })

# Final counts in processed directory
for s in splits:
    img_count = len(os.listdir(os.path.join(OUT_BASE, "images", s)))
    lbl_count = len(os.listdir(os.path.join(OUT_BASE, "labels", s)))
    stats["processed_images"][s] = (img_count, lbl_count)

print("Processing complete!")
print("Initial copied images:", stats["copied_images"])
print("Duplicates removed:", len(stats["duplicates_removed"]))
print("Final processed images (images, labels):", stats["processed_images"])
print("Clamped boxes total:", len(stats["clamped_boxes"]))
print("Flood annotations by split:", stats["annotations_flood"])
print("Excluded non-flood annotations by split:", stats["annotations_excluded"])
print("Negative images by split:", stats["negative_images"])
