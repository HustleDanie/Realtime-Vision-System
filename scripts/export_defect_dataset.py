"""Export defect images and metadata into a dataset-friendly structure.

This script reads defect predictions from the database, copies the
corresponding images into a dataset folder, and writes a metadata CSV
for future model retraining.

Dataset layout (train/val split is optional; defaults to all in `train`):

output_dir/
  train/
    <defect_type>/image_123.jpg
  val/
    <defect_type>/image_456.jpg
  metadata.csv

Usage:
  python scripts/export_defect_dataset.py \
      --db-url sqlite:///./vision_logs.db \
      --storage-base prediction_images \
      --output-dir dataset/defects \
      --train-ratio 0.9 \
      --limit 2000
"""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path
from typing import List

from src.logging_service import DatabaseConnection, PredictionLog, SessionManager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export defect images and metadata to dataset structure",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--db-url", default="sqlite:///./vision_logs.db", help="Database URL")
    parser.add_argument("--storage-base", default="prediction_images", help="Base path where images are stored")
    parser.add_argument("--output-dir", default="dataset/defects", help="Output dataset directory")
    parser.add_argument("--train-ratio", type=float, default=1.0, help="Portion to put into train split (rest into val). Use 1.0 to skip val split.")
    parser.add_argument("--limit", type=int, default=None, help="Max number of defects to export")
    parser.add_argument("--shuffle", action="store_true", help="Shuffle records before splitting")
    return parser.parse_args()


def fetch_defect_logs(session, limit: int | None) -> List[PredictionLog]:
    query = session.query(PredictionLog).filter(PredictionLog.defect_detected == True)
    query = query.order_by(PredictionLog.timestamp.desc())
    if limit:
        query = query.limit(limit)
    return query.all()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def copy_records(args: argparse.Namespace, records: List[PredictionLog]) -> None:
    storage_base = Path(args.storage_base)
    output_root = Path(args.output_dir)
    ensure_dir(output_root)

    # Prepare splits
    splits = [("train", args.train_ratio)]
    if args.train_ratio < 1.0:
        splits.append(("val", 1.0 - args.train_ratio))

    if args.shuffle:
        random.shuffle(records)

    metadata_rows = []
    idx = 0
    for rec in records:
        # Determine split
        split = "train"
        if args.train_ratio < 1.0:
            split = "train" if (idx / len(records)) < args.train_ratio else "val"

        defect_type = rec.defect_type or "unknown"
        src_path = storage_base / rec.image_path
        if not src_path.exists():
            print(f"[WARN] Missing image file: {src_path}")
            idx += 1
            continue

        filename = f"{rec.image_id}.jpg"
        dest_path = output_root / split / defect_type / filename
        ensure_dir(dest_path.parent)

        # Copy file (use copy instead of symlink for portability)
        dest_path.write_bytes(src_path.read_bytes())

        metadata_rows.append(
            {
                "image_id": rec.image_id,
                "split": split,
                "defect_type": defect_type,
                "confidence": rec.confidence_score,
                "timestamp": rec.timestamp.isoformat() if rec.timestamp else "",
                "model_version": rec.model_version,
                "source_path": str(src_path),
                "dest_path": str(dest_path),
                "inference_time_ms": rec.inference_time_ms or "",
            }
        )
        idx += 1

    # Write metadata CSV
    csv_path = output_root / "metadata.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "image_id",
                "split",
                "defect_type",
                "confidence",
                "timestamp",
                "model_version",
                "source_path",
                "dest_path",
                "inference_time_ms",
            ],
        )
        writer.writeheader()
        writer.writerows(metadata_rows)

    print(f"Exported {len(metadata_rows)} records to {output_root}")
    print(f"Metadata written to {csv_path}")


def main() -> None:
    args = parse_args()

    db = DatabaseConnection(db_url=args.db_url)
    with SessionManager(db) as session:
        records = fetch_defect_logs(session, args.limit)
    print(f"Loaded {len(records)} defect records from DB")

    if not records:
        return

    copy_records(args, records)


if __name__ == "__main__":
    main()
