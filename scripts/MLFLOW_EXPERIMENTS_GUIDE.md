# MLflow Experiments and Artifacts Guide

## Overview

This guide shows how to list MLflow experiments, verify model artifacts, and monitor training runs for the real-time vision system.

## Quick Start

### List All Experiments

```bash
python scripts/mlflow_experiments_info.py --list-experiments
```

Output shows:
- Experiment ID and name
- Number of runs in each experiment
- Lifecycle stage (active/deleted)
- Artifact storage location

### Verify Model Artifacts

```bash
python scripts/mlflow_experiments_info.py --verify-artifacts
```

Output shows:
- Which experiment contains artifacts
- Run IDs with logged artifacts
- Artifact paths and types
- File sizes and timestamps

### Combined Query

```bash
python scripts/mlflow_experiments_info.py --list-experiments --show-artifacts
```

## Current Experiments

### 1. model-registry-demo (ID: 2)
- **Status**: Active
- **Runs**: 1 (demo-run-1)
- **Artifacts Location**: mlflow-artifacts:/2
- **Model**: SimpleCNN
- **Training Config**:
  - Epochs: 3
  - Batch Size: 32
  - Learning Rate: 0.001
  - Optimizer: Adam
  - Device: CPU
  - Total Parameters: 545,098

**Metrics**:
- Train Loss: 2.301
- Train Accuracy: 10.31%
- Val Loss: 2.325
- Val Accuracy: 8.13%
- Final Val Accuracy: 15.63%

### 2. my-exp (ID: 1)
- **Status**: Active
- **Runs**: 1 (test-run-new)
- **Artifacts Location**: mlflow-artifacts:/1
- **Model**: SimpleCNN
- **Training Config**:
  - Epochs: 5
  - Batch Size: 32
  - Learning Rate: 0.001
  - Optimizer: Adam
  - Device: CPU
  - Num Classes: 10
  - Total Parameters: 545,098

**Metrics**:
- Train Loss: 2.278
- Train Accuracy: 14.38%
- Val Loss: 2.303
- Val Accuracy: 11.25%
- Epoch Time: 0.466s

**Platform Info**:
- Python: 3.12.5
- PyTorch: 2.10.0+cpu
- CUDA Available: False

### 3. Default (ID: 0)
- **Status**: Active
- **Runs**: 0 (no runs)

## Command-Line Options

### Listing Experiments

```bash
python scripts/mlflow_experiments_info.py \
  --list-experiments \
  [--show-artifacts] \
  [--json] \
  [--uri <tracking_uri>]
```

Options:
- `--list-experiments`: List all experiments
- `--show-artifacts`: Include artifacts for each experiment
- `--json`: Output in JSON format instead of table
- `--uri <tracking_uri>`: Use custom tracking URI (default: local sqlite)

### Verifying Artifacts

```bash
python scripts/mlflow_experiments_info.py \
  --verify-artifacts \
  [--experiment <name>] \
  [--artifact-filter <pattern>] \
  [--json] \
  [--uri <tracking_uri>]
```

Options:
- `--verify-artifacts`: Verify model artifacts
- `--experiment <name>`: Filter by experiment name
- `--artifact-filter <pattern>`: Filter artifacts by name/path (e.g., "model")
- `--json`: Output in JSON format
- `--uri <tracking_uri>`: Use custom tracking URI

## Examples

### List experiments only (simple format)
```bash
python scripts/mlflow_experiments_info.py --list-experiments
```

### Find all model artifacts
```bash
python scripts/mlflow_experiments_info.py --verify-artifacts --artifact-filter "model"
```

### Get specific experiment info
```bash
python scripts/mlflow_experiments_info.py --verify-artifacts --experiment "model-registry-demo"
```

### JSON output for parsing
```bash
python scripts/mlflow_experiments_info.py --list-experiments --json
```

### Use remote MLflow server
```bash
python scripts/mlflow_experiments_info.py \
  --list-experiments \
  --uri http://localhost:5000
```

## MLflow Directory Structure

```
c:\realtime-vision-system\
├── mlruns/                      # Artifacts storage
│   ├── 0/                      # Default experiment
│   ├── 1/                      # my-exp experiment
│   │   └── <run_id>/
│   │       ├── artifacts/      # Model files, configs, etc.
│   │       └── metrics/        # Logged metrics
│   └── 2/                      # model-registry-demo experiment
│       └── <run_id>/
│           ├── artifacts/
│           └── metrics/
└── mlflow.db                   # SQLite database with experiments metadata
```

## Accessing Run Data Programmatically

### Get experiment details
```python
import mlflow
from mlflow.tracking import MlflowClient

client = MlflowClient()
experiments = client.search_experiments()

for exp in experiments:
    print(f"Experiment: {exp.name} (ID: {exp.experiment_id})")
    runs = client.search_runs(experiment_ids=[exp.experiment_id])
    print(f"  Runs: {len(runs)}")
```

### Get run metrics and parameters
```python
from mlflow.tracking import MlflowClient

client = MlflowClient()
run = client.get_run(run_id="<run_id>")

print(f"Metrics: {run.data.metrics}")
print(f"Params: {run.data.params}")
print(f"Tags: {run.data.tags}")
```

### List artifacts in a run
```python
from mlflow.tracking import MlflowClient

client = MlflowClient()
artifacts = client.list_artifacts(run_id="<run_id>")

for artifact in artifacts:
    print(f"  {artifact.path} (is_dir={artifact.is_dir})")
```

### Download artifact
```python
from mlflow.tracking import MlflowClient

client = MlflowClient()
client.download_artifacts(
    run_id="<run_id>",
    path="<artifact_path>",
    dst_path="./downloaded"
)
```

## MLflow Server (Optional)

To launch the MLflow UI and access experiments via web interface:

```bash
# Start MLflow server (default: http://localhost:5000)
mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns

# Or with specific port
mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns -p 8000
```

Then open: http://localhost:5000 (or http://localhost:8000)

## Troubleshooting

### MLflow not installed
```bash
pip install mlflow
```

### Experiments not appearing
1. Check MLflow database exists: `mlflow.db`
2. Check tracking URI is correct: `mlflow.get_tracking_uri()`
3. Verify experiments were logged with: `mlflow.set_experiment("name")`

### Cannot access artifacts
- Artifacts require HTTP/HTTPS tracking URI or local file system access
- Check artifact storage path is accessible
- For remote artifacts, ensure MLflow server is running

### Slow queries on large datasets
Use `--artifact-filter` or `--experiment` to narrow search scope

## Integration with Training Scripts

### Log experiment in training
```python
import mlflow

# Set experiment
mlflow.set_experiment("my-exp")

# Log parameters
mlflow.log_params({
    "model": "SimpleCNN",
    "epochs": 5,
    "learning_rate": 0.001
})

# Log metrics
mlflow.log_metric("train_loss", loss_value)
mlflow.log_metric("val_accuracy", accuracy)

# Log artifacts
mlflow.log_artifact("model.pt")
mlflow.log_artifact("config.json")

# End run
mlflow.end_run()
```

### Query experiments programmatically
```python
from mlflow.tracking import MlflowClient

client = MlflowClient()

# Get best run by metric
runs = client.search_runs(
    experiment_ids=[1],
    order_by=["metrics.val_accuracy DESC"],
    max_results=1
)

best_run = runs[0]
print(f"Best run: {best_run.info.run_id}")
print(f"Metrics: {best_run.data.metrics}")
```

## Related Files

- [scripts/mlflow_experiments_info.py](mlflow_experiments_info.py) - Main query tool
- [scripts/train_and_register_model.py](train_and_register_model.py) - Example training script with MLflow logging
- [scripts/train_pytorch_mlflow.py](train_pytorch_mlflow.py) - PyTorch training with MLflow

## Additional Resources

- MLflow Documentation: https://mlflow.org/docs/latest/index.html
- MLflow Python API: https://mlflow.org/docs/latest/python_api/index.html
- Model Registry: https://mlflow.org/docs/latest/model-registry.html
