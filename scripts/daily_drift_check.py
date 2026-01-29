"""
Daily drift check script:
- Computes simple image features on reference (training) and new inspection data
- Runs statistical drift detection with Evidently
- Flags drift if p-values or drift shares exceed thresholds

Intended to be run daily via scheduler (Task Scheduler / cron).

Requirements:
    pip install evidently pillow numpy pandas opencv-python

Usage:
    C:/realtime-vision-system/.venv/Scripts/python.exe scripts/daily_drift_check.py \
        --reference-dir data/train_images \
        --production-dir data/new_images \
        --reference-labels data/train_labels \
        --production-labels data/new_labels \
        --pvalue-threshold 0.05 \
        --drift-share-threshold 0.3 \
        --out-html drift_daily.html \
        --out-json drift_daily.json
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


def compute_image_features(img_path: Path) -> dict:
    with Image.open(img_path) as img:
        img = img.convert("RGB")
        stat = ImageStat.Stat(img)
        brightness = float(np.mean(stat.mean))
        contrast = float(np.mean(stat.stddev))
        gray = img.convert("L")
        arr = np.asarray(gray, dtype=np.uint8)
        # Edge density via simple Sobel gradient magnitude proxy
        gx = np.abs(np.gradient(arr, axis=0))
        gy = np.abs(np.gradient(arr, axis=1))
        edge_mag = gx + gy
        edge_density = float((edge_mag > 32).sum() / edge_mag.size)
    return {"brightness": brightness, "contrast": contrast, "edge_density": edge_density}


def load_bbox_features(label_path: Path) -> dict:
    if not label_path.exists():
        return {"bbox_area_mean": np.nan, "bbox_area_sum": np.nan, "bbox_count": 0}
    areas = []
    with label_path.open() as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            try:
                w = float(parts[-2])
                h = float(parts[-1])
            except ValueError:
                continue
            areas.append(w * h)
    if not areas:
        return {"bbox_area_mean": np.nan, "bbox_area_sum": np.nan, "bbox_count": 0}
    return {
        "bbox_area_mean": float(np.mean(areas)),
        "bbox_area_sum": float(np.sum(areas)),
        "bbox_count": len(areas),
    }


def build_df(folder: Path, labels_dir: Path | None) -> pd.DataFrame:
    rows = []
    for img_path_str in glob.glob(str(folder / "*.jpg")) + glob.glob(str(folder / "*.png")) + glob.glob(str(folder / "*.jpeg")):
        img_path = Path(img_path_str)
        feats = compute_image_features(img_path)
        label_path = labels_dir / (img_path.stem + ".txt") if labels_dir else Path("/nonexistent")
        feats.update(load_bbox_features(label_path))
        feats["filename"] = img_path.name
        rows.append(feats)
    return pd.DataFrame(rows)


def run_drift(reference: pd.DataFrame, current: pd.DataFrame, pvalue_threshold: float, drift_share_threshold: float, out_html: str, out_json: str) -> bool:
    num_features = [c for c in ["brightness", "contrast", "edge_density", "bbox_area_mean", "bbox_area_sum", "bbox_count"] if c in reference.columns]
    mapping = ColumnMapping(numerical_features=num_features, target=None)

    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=reference, current_data=current, column_mapping=mapping)

    report.save_html(out_html)
    as_dict = report.as_dict()
    with open(out_json, "w") as f:
        json.dump(as_dict, f, indent=2)

    # Determine drift status from Evidently outputs
    overall = as_dict.get("metrics", [])[0].get("result", {}) if as_dict.get("metrics") else {}
    drift_share = overall.get("drift_share")
    p_values = [f.get("p_value") for f in overall.get("drift_by_columns", {}).values() if isinstance(f, dict)]
    min_p = min(p_values) if p_values else 1.0

    drift_flag = False
    reasons = []
    if drift_share is not None and drift_share > drift_share_threshold:
        drift_flag = True
        reasons.append(f"drift_share {drift_share:.3f} > {drift_share_threshold}")
    if min_p < pvalue_threshold:
        drift_flag = True
        reasons.append(f"min_p_value {min_p:.3f} < {pvalue_threshold}")

    print(f"Drift share: {drift_share}, min p-value: {min_p}")
    if drift_flag:
        print("⚠ Drift detected: " + "; ".join(reasons))
    else:
        print("No drift detected under thresholds.")

    return drift_flag


def main():
    parser = argparse.ArgumentParser(description="Daily drift check for inspection data")
    parser.add_argument("--reference-dir", required=True, help="Training/reference images directory")
    parser.add_argument("--production-dir", required=True, help="New inspection images directory")
    parser.add_argument("--reference-labels", help="Labels for reference images (YOLO txt)")
    parser.add_argument("--production-labels", help="Labels for production images (YOLO txt)")
    parser.add_argument("--pvalue-threshold", type=float, default=0.05)
    parser.add_argument("--drift-share-threshold", type=float, default=0.3)
    parser.add_argument("--out-html", default="drift_daily.html")
    parser.add_argument("--out-json", default="drift_daily.json")
    args = parser.parse_args()

    ref_labels = Path(args.reference_labels) if args.reference_labels else None
    prod_labels = Path(args.production_labels) if args.production_labels else None

    ref_df = build_df(Path(args.reference_dir), ref_labels)
    prod_df = build_df(Path(args.production_dir), prod_labels)

    drift = run_drift(
        ref_df,
        prod_df,
        pvalue_threshold=args.pvalue_threshold,
        drift_share_threshold=args.drift_share_threshold,
        out_html=args.out_html,
        out_json=args.out_json,
    )

    # Exit code for schedulers/alerts
    if drift:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
