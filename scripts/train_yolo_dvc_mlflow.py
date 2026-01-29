"""
Training pipeline that:
1) Pulls the latest dataset via DVC
2) Trains a YOLO model (Ultralytics)
3) Logs metrics/params/artifacts to MLflow
4) Registers the model in MLflow Model Registry if it improves over Production

Requirements:
- dvc
- mlflow
- ultralytics
- torch
"""

import argparse
import csv
import json
import os
import subprocess
from pathlib import Path

import mlflow
import mlflow.pytorch
from mlflow import MlflowClient
from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]


def run_cmd(cmd, cwd=None):
    result = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\nStdout: {result.stdout}\nStderr: {result.stderr}")
    return result.stdout.strip()


def pull_dvc_target(target: str):
    run_cmd(["dvc", "pull", target])


def read_dvc_hash(dvc_file: Path) -> str | None:
    if not dvc_file.exists():
        return None
    for line in dvc_file.read_text().splitlines():
        if line.strip().startswith("md5:"):
            return line.split(":", 1)[1].strip()
    return None


def parse_results_csv(results_csv: Path) -> dict:
    if not results_csv.exists():
        return {}
    with results_csv.open() as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if not rows:
            return {}
        row = rows[-1]
        metrics = {}
        for k, v in row.items():
            if v is None or v == "":
                continue
            try:
                metrics[k] = float(v)
            except ValueError:
                pass
        return metrics


def extract_best_metric(metrics: dict, preferred_keys: list[str]) -> tuple[str | None, float | None]:
    for key in preferred_keys:
        if key in metrics:
            return key, metrics[key]
    return None, None


def get_production_metric(model_name: str, metric_key: str, client: MlflowClient) -> float | None:
    versions = client.search_model_versions(f"name = '{model_name}'")
    prod_versions = [v for v in versions if v.current_stage == "Production"]
    if not prod_versions:
        return None
    prod = sorted(prod_versions, key=lambda v: int(v.version))[-1]
    run = client.get_run(prod.run_id)
    return run.data.metrics.get(metric_key)


def should_promote(metric_key: str | None, metric_value: float | None, model_name: str, client: MlflowClient) -> tuple[bool, float | None]:
    """Return (promote?, current_prod_metric) given new metric vs latest Production.

    Promote when:
    - No Production model exists, or
    - Production metric is missing, or
    - New metric strictly improves over Production.
    """
    if metric_key is None or metric_value is None:
        return False, None
    current_prod = get_production_metric(model_name, metric_key, client)
    if current_prod is None:
        return True, None
    return metric_value > current_prod, current_prod


def train_yolo(args):
    model = YOLO(args.model)
    results = model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=args.project,
        name=args.run_name or "yolo-dvc-mlflow",
        exist_ok=True,
        save=True,
        verbose=True,
    )
    save_dir = Path(results.save_dir) if hasattr(results, "save_dir") else Path(args.project) / (args.run_name or "yolo-dvc-mlflow")
    results_csv = save_dir / "results.csv"
    metrics = parse_results_csv(results_csv)
    best_weights = save_dir / "weights" / "best.pt"
    return metrics, best_weights, save_dir


def log_and_maybe_register(args, metrics, best_weights, save_dir, dataset_hash):
    mlflow.set_tracking_uri(args.mlflow_tracking_uri)
    mlflow.set_experiment(args.experiment_name)
    client = MlflowClient()

    preferred_keys = [args.metric_key, "metrics/mAP50(B)", "metrics/mAP50-95(B)", "map50" ]
    metric_key, metric_value = extract_best_metric(metrics, preferred_keys)

    with mlflow.start_run(run_name=args.run_name) as run:
        mlflow.log_params({
            "model": args.model,
            "data": args.data,
            "epochs": args.epochs,
            "batch": args.batch,
            "imgsz": args.imgsz,
            "device": args.device,
            "dataset_hash": dataset_hash,
        })

        if metric_key and metric_value is not None:
            mlflow.log_metric(metric_key, metric_value)
        for k, v in metrics.items():
            mlflow.log_metric(k, v)

        if save_dir.exists():
            mlflow.log_artifacts(str(save_dir))
        if best_weights.exists():
            mlflow.log_artifact(str(best_weights))

        yolo_loaded = YOLO(best_weights)
        mlflow.pytorch.log_model(yolo_loaded.model, artifact_path="model")

        run_id = run.info.run_id
        promote, current_prod = should_promote(metric_key, metric_value, args.model_name, client)

        if promote:
            model_uri = f"runs:/{run_id}/model"
            mv = mlflow.register_model(model_uri, args.model_name)
            # Promote straight to Production since metric improved
            try:
                client.transition_model_version_stage(args.model_name, mv.version, "Production")
            except Exception:
                pass
            print(
                "Registered and promoted new model version: "
                f"{args.model_name} v{mv.version} | {metric_key}: {metric_value}"
            )
            if current_prod is not None:
                print(f"Previous Production {metric_key}: {current_prod}")
        else:
            print(
                "Model not registered: "
                f"metric_key={metric_key}, metric_value={metric_value}, current_prod={current_prod}"
            )


def main():
    parser = argparse.ArgumentParser(description="Train YOLO with DVC + MLflow")
    parser.add_argument("--data", required=True, help="Path to YOLO data YAML")
    parser.add_argument("--model", default="yolov8n.pt", help="Base model to fine-tune")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--project", default="runs/train")
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--mlflow-tracking-uri", default="http://127.0.0.1:5000")
    parser.add_argument("--experiment-name", default="yolo-dvc-mlflow")
    parser.add_argument("--model-name", default="yolo-prod")
    parser.add_argument("--metric-key", default="metrics/mAP50(B)", help="Metric key to compare for improvement")
    parser.add_argument("--dvc-target", default="dataset.dvc", help="DVC target to pull")
    args = parser.parse_args()

    pull_dvc_target(args.dvc_target)
    dataset_hash = read_dvc_hash(ROOT / args.dvc_target) or "unknown"

    metrics, best_weights, save_dir = train_yolo(args)
    log_and_maybe_register(args, metrics, best_weights, save_dir, dataset_hash)


if __name__ == "__main__":
    main()
