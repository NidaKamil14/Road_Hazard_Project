# Model Weights Directory

To avoid duplicating large binary weight files across repository directories, the backend by default loads the current final model checkpoint directly from:

`runs/detect/experiment2_yolo11s_800/weights/best.pt`

- Architecture: YOLO11s (9.46M parameters)
- Input Resolution: 800 x 800
- Classes:
  - 0: pothole
  - 1: road_crack
  - 2: waterlogging
  - 3: construction_barrier

If a standalone deployment container or portable bundle is built in the future, `best.pt` can optionally be copied into this directory.
