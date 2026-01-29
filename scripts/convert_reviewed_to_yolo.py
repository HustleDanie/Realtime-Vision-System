"""
Convert human-labeled review data into YOLO training format.

Assumptions:
- Reviewed folder contains images (*.jpg|*.png|*.jpeg) and a matching JSON file per image.
- Annotation JSON schema (per image):
    {
      "annotations": [
        {"class": "defect", "bbox": [x_min, y_min, x_max, y_max]},
        ...
      ],
      "image_width": 1280,   # optional (will be read from image if missing)
      "image_height": 720    # optional
    }
- Bounding boxes are in absolute pixel coords (x_min,y_min,x_max,y_max).

Outputs (YOLO format):
- Copies images to --out-images
- Writes YOLO txt labels to --out-labels with lines: class_id cx cy w h (normalized)
- Generates a mapping file classes.txt in the label folder

Usage:
    python scripts/convert_reviewed_to_yolo.py \
        --reviewed-dir reviewed/ \
        --out-images dataset/images \
        --out-labels dataset/labels \
        --class-map class_map.json

class_map.json example:
    {"defect": 0, "background": 1}
If no class_map provided, classes are discovered from the annotations in sorted order.
"""

import argparse
import json
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
from PIL import Image

IMG_EXTS = {".jpg", ".jpeg", ".png"}


def load_class_map(class_map_path: Path | None, discovered: List[str]) -> Dict[str, int]:
    if class_map_path and class_map_path.exists():
        with open(class_map_path, "r") as f:
            data = json.load(f)
        return {str(k): int(v) for k, v in data.items()}
    # infer from discovered classes
    classes_sorted = sorted(set(discovered))
    return {name: idx for idx, name in enumerate(classes_sorted)}


def to_yolo_bbox(bbox: List[float], img_w: int, img_h: int) -> Tuple[float, float, float, float]:
    x_min, y_min, x_max, y_max = bbox
    w = x_max - x_min
    h = y_max - y_min
    cx = x_min + w / 2.0
    cy = y_min + h / 2.0
    return cx / img_w, cy / img_h, w / img_w, h / img_h


def process_image(img_path: Path, reviewed_dir: Path) -> Tuple[List[dict], int, int]:
    json_path = img_path.with_suffix(".json")
    if not json_path.exists():
        raise FileNotFoundError(f"Missing annotation JSON for {img_path.name}")

    with open(json_path, "r") as f:
        data = json.load(f)

    annos = data.get("annotations", [])
    img_w = data.get("image_width")
    img_h = data.get("image_height")

    if img_w is None or img_h is None:
        with Image.open(img_path) as im:
            img_w, img_h = im.size

    return annos, img_w, img_h


def write_yolo_label(out_label_path: Path, annos: List[dict], class_map: Dict[str, int], img_w: int, img_h: int):
    lines = []
    for anno in annos:
        cls_name = anno.get("class", "defect")
        bbox = anno.get("bbox")
        if bbox is None or len(bbox) != 4:
            continue
        if cls_name not in class_map:
            continue
        cx, cy, w, h = to_yolo_bbox(bbox, img_w, img_h)
        lines.append(f"{class_map[cls_name]} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
    out_label_path.parent.mkdir(parents=True, exist_ok=True)
    out_label_path.write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Convert reviewed labels to YOLO format")
    parser.add_argument("--reviewed-dir", required=True, help="Folder with reviewed images and JSON labels")
    parser.add_argument("--out-images", required=True, help="Output images directory")
    parser.add_argument("--out-labels", required=True, help="Output labels directory")
    parser.add_argument("--class-map", help="Optional JSON mapping class_name->id")
    args = parser.parse_args()

    reviewed_dir = Path(args.reviewed_dir)
    out_images = Path(args.out_images)
    out_labels = Path(args.out_labels)
    class_map_path = Path(args.class_map) if args.class_map else None

    image_paths = [p for p in reviewed_dir.iterdir() if p.suffix.lower() in IMG_EXTS]
    if not image_paths:
        raise SystemExit("No images found in reviewed directory")

    # First pass: discover classes
    discovered_classes: List[str] = []
    for img_path in image_paths:
        json_path = img_path.with_suffix(".json")
        if not json_path.exists():
            continue
        with open(json_path, "r") as f:
            data = json.load(f)
        for anno in data.get("annotations", []):
            cls_name = anno.get("class", "defect")
            discovered_classes.append(cls_name)

    class_map = load_class_map(class_map_path, discovered_classes)

    # Write classes.txt for reference
    classes_txt = out_labels / "classes.txt"
    classes_txt.parent.mkdir(parents=True, exist_ok=True)
    classes_txt.write_text("\n".join(sorted(class_map, key=lambda k: class_map[k])))

    converted = 0
    for img_path in image_paths:
        annos, img_w, img_h = process_image(img_path, reviewed_dir)
        label_path = out_labels / f"{img_path.stem}.txt"
        write_yolo_label(label_path, annos, class_map, img_w, img_h)
        out_images.mkdir(parents=True, exist_ok=True)
        shutil.copy2(img_path, out_images / img_path.name)
        converted += 1

    print(f"Converted {converted} images to YOLO format")
    print(f"Classes: {class_map}")
    print(f"Images -> {out_images}")
    print(f"Labels -> {out_labels}")


if __name__ == "__main__":
    main()
