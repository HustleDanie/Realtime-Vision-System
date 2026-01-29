"""
Extract monitoring features from defect images.
Features per image:
- brightness (mean pixel value)
- edge_density (Canny edges pixel ratio)
- bbox_area_mean (YOLO-format labels: cx cy w h normalized)
- bbox_area_sum
- bbox_count
- confidence_mean (YOLO detections: class conf cx cy w h)
Outputs a CSV with one row per image.

Requirements: pillow, numpy, opencv-python, pandas
YOLO label files are optional; if absent, bbox/conf features are NaN.
"""

import argparse
import glob
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
import cv2


def compute_brightness(img: Image.Image) -> float:
    arr = np.asarray(img.convert("L"), dtype=np.float32)
    return float(arr.mean())


def compute_edge_density(img: Image.Image, low: int = 100, high: int = 200) -> float:
    gray = np.asarray(img.convert("L"), dtype=np.uint8)
    edges = cv2.Canny(gray, low, high)
    return float((edges > 0).sum() / edges.size)


def parse_yolo_labels(label_path: Path) -> tuple[float, float, int, float]:
    """Return (bbox_area_mean, bbox_area_sum, bbox_count, confidence_mean)."""
    if not label_path.exists():
        return np.nan, np.nan, 0, np.nan
    areas = []
    confs = []
    with label_path.open() as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 5:
                # class cx cy w h (no conf)
                _, _, _, w, h = parts
                conf = None
            elif len(parts) >= 6:
                # class conf cx cy w h
                _, conf, _, _, w, h = parts[:6]
                conf = float(conf)
            else:
                continue
            try:
                w = float(w)
                h = float(h)
            except ValueError:
                continue
            areas.append(w * h)
            if conf is not None:
                confs.append(conf)
    if not areas:
        return np.nan, np.nan, 0, np.nan
    area_mean = float(np.mean(areas))
    area_sum = float(np.sum(areas))
    conf_mean = float(np.mean(confs)) if confs else np.nan
    return area_mean, area_sum, len(areas), conf_mean


def process_images(img_dir: Path, labels_dir: Path | None) -> pd.DataFrame:
    rows = []
    img_paths = sorted(glob.glob(str(img_dir / "*.jpg")) + glob.glob(str(img_dir / "*.png")) + glob.glob(str(img_dir / "*.jpeg")))
    for img_path_str in img_paths:
        img_path = Path(img_path_str)
        with Image.open(img_path) as img:
            brightness = compute_brightness(img)
            edge_density = compute_edge_density(img)
        label_path = labels_dir / (img_path.stem + ".txt") if labels_dir else Path("/nonexistent")
        bbox_area_mean, bbox_area_sum, bbox_count, confidence_mean = parse_yolo_labels(label_path)
        rows.append({
            "filename": img_path.name,
            "brightness": brightness,
            "edge_density": edge_density,
            "bbox_area_mean": bbox_area_mean,
            "bbox_area_sum": bbox_area_sum,
            "bbox_count": bbox_count,
            "confidence_mean": confidence_mean,
        })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="Extract monitoring features from defect images")
    parser.add_argument("--images", required=True, help="Directory with images")
    parser.add_argument("--labels", help="Directory with YOLO label/detection txt files")
    parser.add_argument("--output-csv", default="defect_features.csv", help="Output CSV path")
    args = parser.parse_args()

    img_dir = Path(args.images)
    labels_dir = Path(args.labels) if args.labels else None

    df = process_images(img_dir, labels_dir)
    df.to_csv(args.output_csv, index=False)
    print(f"Saved features to {args.output_csv}")


if __name__ == "__main__":
    main()
