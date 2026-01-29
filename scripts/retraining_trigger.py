"""
Retraining trigger module.
Fires when either:
  - Data drift is detected (via a drift JSON report), OR
  - At least N newly labeled samples are present in a folder.

This is a lightweight policy module; integrate with your scheduler/CI to kick off
train pipelines when `should_retrain()` returns True.

Usage examples:
    python scripts/retraining_trigger.py \
        --drift-json drift_daily.json \
        --new-labels-dir dataset/new_labels \
        --min-new-samples 50

Exit codes:
    0 -> no retrain needed
    1 -> retrain should be triggered
"""

import argparse
import json
from pathlib import Path


def drift_flagged(drift_json: Path, pvalue_threshold: float, drift_share_threshold: float) -> bool:
    if not drift_json.exists():
        return False
    try:
        data = json.loads(drift_json.read_text())
        metrics = data.get("metrics", [])
        if not metrics:
            return False
        overall = metrics[0].get("result", {})
        drift_share = overall.get("drift_share")
        p_values = [f.get("p_value") for f in overall.get("drift_by_columns", {}).values() if isinstance(f, dict)]
        min_p = min(p_values) if p_values else 1.0
        if drift_share is not None and drift_share > drift_share_threshold:
            return True
        if min_p < pvalue_threshold:
            return True
        return False
    except Exception:
        return False


def count_new_labels(labels_dir: Path) -> int:
    if not labels_dir.exists():
        return 0
    return len(list(labels_dir.glob("*.txt")))


def should_retrain(drift_json: Path, labels_dir: Path, min_new_samples: int, pvalue_threshold: float, drift_share_threshold: float) -> bool:
    drift = drift_flagged(drift_json, pvalue_threshold, drift_share_threshold)
    new_samples = count_new_labels(labels_dir)
    return drift or new_samples >= min_new_samples


def main():
    parser = argparse.ArgumentParser(description="Retraining trigger policy")
    parser.add_argument("--drift-json", required=True, help="Path to drift JSON report")
    parser.add_argument("--new-labels-dir", required=True, help="Directory containing new YOLO label txt files")
    parser.add_argument("--min-new-samples", type=int, default=50, help="Minimum new samples to trigger retrain")
    parser.add_argument("--pvalue-threshold", type=float, default=0.05, help="P-value threshold for drift")
    parser.add_argument("--drift-share-threshold", type=float, default=0.3, help="Drift share threshold")
    args = parser.parse_args()

    drift_json = Path(args.drift_json)
    labels_dir = Path(args.new_labels_dir)

    trigger = should_retrain(
        drift_json=drift_json,
        labels_dir=labels_dir,
        min_new_samples=args.min_new_samples,
        pvalue_threshold=args.pvalue_threshold,
        drift_share_threshold=args.drift_share_threshold,
    )

    if trigger:
        print("RETRAIN_TRIGGER=1")
        raise SystemExit(1)
    else:
        print("RETRAIN_TRIGGER=0")
        raise SystemExit(0)


if __name__ == "__main__":
    main()
