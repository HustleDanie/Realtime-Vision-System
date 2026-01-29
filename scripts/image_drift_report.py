"""
Generate an Evidently data drift report comparing reference vs production image batches.
Computes simple image-level features (brightness, contrast, average bbox area) then uses
Evidently to detect drift. Output: HTML report and JSON metrics.

Inputs:
- Reference folder: reference_dir (e.g., historical training images)
- Production folder: production_dir (e.g., recent prod images)
- Optional YOLO-format bbox labels to compute bbox sizes (txt files with cx cy w h)

Requirements:
- pip install evidently pillow numpy pandas
- For bbox metrics: have matching *.txt files with YOLO labels alongside images.
"""

import argparse
import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageStat
from evidently import ColumnMapping
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset


def load_image_features(img_path: Path) -> dict:
    """Extract brightness and contrast features from an image."""
    with Image.open(img_path) as img:
        img = img.convert("RGB")
        stat = ImageStat.Stat(img)
        # Brightness: mean over channels
        brightness = float(np.mean(stat.mean))
        # Contrast proxy: mean standard deviation across channels
        contrast = float(np.mean(stat.stddev))
    return {"brightness": brightness, "contrast": contrast}


def load_bbox_features(label_path: Path) -> dict:
    """Compute average bbox area (normalized) from YOLO txt labels if present."""
    if not label_path.exists():
        return {"bbox_area_mean": np.nan}
    areas = []
    with label_path.open() as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            _, _, w, h = parts[0], parts[1], float(parts[3]), float(parts[4])
            areas.append(w * h)
    if not areas:
        return {"bbox_area_mean": np.nan}
    return {"bbox_area_mean": float(np.mean(areas))}


def build_dataframe(folder: Path, labels_dir: Path | None = None) -> pd.DataFrame:
    rows = []
    for img_path_str in glob.glob(str(folder / "*.jpg")) + glob.glob(str(folder / "*.png")):
        img_path = Path(img_path_str)
        feats = load_image_features(img_path)
        label_path = labels_dir / (img_path.stem + ".txt") if labels_dir else Path("/nonexistent")
        feats.update(load_bbox_features(label_path))
        feats["filename"] = img_path.name
        rows.append(feats)
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="Image data drift report with Evidently")
    parser.add_argument("--reference-dir", required=True, help="Path to reference images")
    parser.add_argument("--production-dir", required=True, help="Path to production images")
    parser.add_argument("--reference-labels", help="Path to YOLO txt labels for reference images")
    parser.add_argument("--production-labels", help="Path to YOLO txt labels for production images")
    parser.add_argument("--out-html", default="drift_report.html", help="Output HTML report path")
    parser.add_argument("--out-json", default="drift_report.json", help="Output JSON metrics path")
    args = parser.parse_args()

    ref_labels = Path(args.reference_labels) if args.reference_labels else None
    prod_labels = Path(args.production_labels) if args.production_labels else None

    ref_df = build_dataframe(Path(args.reference_dir), ref_labels)
    prod_df = build_dataframe(Path(args.production_dir), prod_labels)

    # Define column mapping (numerical features for drift)
    num_features = [c for c in ["brightness", "contrast", "bbox_area_mean"] if c in ref_df.columns]
    mapping = ColumnMapping(numerical_features=num_features, target=None)

    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=ref_df, current_data=prod_df, column_mapping=mapping)

    report.save_html(args.out_html)
    with open(args.out_json, "w") as f:
        json.dump(report.as_dict(), f, indent=2)

    print("Report saved:", args.out_html)
    print("Metrics saved:", args.out_json)


if __name__ == "__main__":
    main()
