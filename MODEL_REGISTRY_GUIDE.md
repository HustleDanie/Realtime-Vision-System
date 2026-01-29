# MLflow Model Saving, Logging, and Registration Guide

## Overview

This guide demonstrates how to:
1. **Save** PyTorch models locally
2. **Log** models as artifacts to MLflow
3. **Register** models in the MLflow Model Registry
4. **Load** and use registered models
5. **Manage** model versions and stages

## Key Concepts

### Artifacts vs Model Registry

**Artifacts:**
- Files logged during a run (models, checkpoints, visualizations)
- Tied to specific runs
- Stored in the artifact store (local directory or S3/Azure/etc)
- Useful for experiment tracking

**Model Registry:**
- Central model repository for managing models across experiments
- Version control and stage transitions (Staging, Production, Archived)
- Model lineage and run traceability
- Better for model deployment workflows

---

## 1. Training and Logging Models

### Script: `train_and_register_model.py`

This script trains a model and logs it to MLflow:

```bash
# Basic usage
python scripts/train_and_register_model.py

# With custom settings
python scripts/train_and_register_model.py \
    --experiment-name "production-models" \
    --run-name "cnn-v1" \
    --model-name "image-classifier-v1" \
    --epochs 10 \
    --batch-size 32 \
    --lr 0.001
```

### What Gets Logged

```python
# 1. Hyperparameters
mlflow.log_params({
    "model": "SimpleCNN",
    "epochs": 10,
    "batch_size": 32,
    "learning_rate": 0.001,
    "total_parameters": 95050,
})

# 2. Performance metrics (per epoch)
mlflow.log_metrics({
    "train_loss": 2.3,
    "train_accuracy": 8.12,
    "val_loss": 2.29,
    "val_accuracy": 13.75,
})

# 3. Models using MLflow's PyTorch integration
mlflow.pytorch.log_model(model, "pytorch_model")
# This saves:
# - model.pkl: serialized model
# - conda.yaml: environment dependencies
# - requirements.txt: Python packages
# - MLmodel: metadata file

# 4. Checkpoint artifact
mlflow.log_artifact("best_model.pt")

# 5. Model metadata
mlflow.log_artifact("model_metadata.json")
```

### Model Registration

After training, the script registers the model:

```python
# Create model URI from the run
model_uri = f"runs:/{run_id}/pytorch_model"

# Register in Model Registry
model_version = mlflow.register_model(model_uri, "simple-cnn-classifier")

# Update version description
client = mlflow.MlflowClient()
client.update_model_version(
    name="simple-cnn-classifier",
    version=model_version.version,
    description="SimpleCNN trained with lr=0.001"
)
```

---

## 2. Loading Models from Runs

Load a model from a specific MLflow run:

```bash
python scripts/load_and_use_models.py from-run <RUN_ID> --predict
```

**Example:**

```bash
python scripts/load_and_use_models.py from-run 0676488122104f66a433df1d95c2332e --predict
```

### In Code

```python
import mlflow.pytorch

# Load model
model_uri = f"runs:/{run_id}/pytorch_model"
model = mlflow.pytorch.load_model(model_uri)

# Or with tracking URI
mlflow.set_tracking_uri("http://127.0.0.1:5000")
model = mlflow.pytorch.load_model(model_uri)

# Use for predictions
predictions = model(input_tensor)
```

---

## 3. Loading Registered Models

### List All Registered Models

```bash
python scripts/load_and_use_models.py list
```

**Output:**
```
Registered Models in MLflow Model Registry
=============================================

📦 Model: simple-cnn-classifier
   Description: SimpleCNN trained with lr=0.001, batch_size=32
   Latest Version: 1
   Latest Stage: None
```

### Load Latest Version

```bash
python scripts/load_and_use_models.py from-registry simple-cnn-classifier --predict
```

### Load Specific Version

```bash
python scripts/load_and_use_models.py from-registry simple-cnn-classifier --version 1 --predict
```

### Load from Stage

```bash
# After transitioning to Production
python scripts/load_and_use_models.py from-registry simple-cnn-classifier --stage Production
```

### In Code

```python
# Load latest version
model = mlflow.pytorch.load_model("models:/simple-cnn-classifier/latest")

# Load specific version
model = mlflow.pytorch.load_model("models:/simple-cnn-classifier/1")

# Load from stage (Staging, Production, Archived)
model = mlflow.pytorch.load_model("models:/simple-cnn-classifier/Production")
```

---

## 4. Model Versioning and Stages

### List Model Versions

```bash
python scripts/load_and_use_models.py versions simple-cnn-classifier
```

**Output:**
```
Versions of Model: simple-cnn-classifier
========================================

Version 1:
  Stage: None
  Status: READY
  Description: SimpleCNN trained with lr=0.001
  Run ID: 0676488122104f66a433df1d95c2332e

Version 2:
  Stage: Staging
  Status: READY
  Description: SimpleCNN with improved architecture
  Run ID: a1b2c3d4e5f6g7h8i9j0
```

### Transition to Stage

Stages represent the maturity/deployment status:
- **None**: Default stage (no specific designation)
- **Staging**: Model under testing
- **Production**: Model in use
- **Archived**: Retired model

```bash
# Transition version 1 to Staging
python scripts/load_and_use_models.py transition simple-cnn-classifier 1 Staging

# Promote to Production
python scripts/load_and_use_models.py transition simple-cnn-classifier 1 Production

# Archive old version
python scripts/load_and_use_models.py transition simple-cnn-classifier 0 Archived
```

### In Code

```python
client = mlflow.MlflowClient()

# Transition to Production
client.transition_model_version_stage(
    name="simple-cnn-classifier",
    version=1,
    stage="Production"
)

# Archive a version
client.transition_model_version_stage(
    name="simple-cnn-classifier",
    version=0,
    stage="Archived"
)
```

---

## 5. Complete Workflow Example

### Step 1: Train and Register

```bash
# Terminal 1: Start MLflow server
python -m mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000

# Terminal 2: Train model and register
python scripts/train_and_register_model.py \
    --experiment-name "production" \
    --model-name "image-classifier"

# Output will show:
# Run ID: abc123def456
# Model Name: image-classifier
# Model Version: 1
```

### Step 2: List and Inspect

```bash
# List all registered models
python scripts/load_and_use_models.py list

# List versions of the model
python scripts/load_and_use_models.py versions image-classifier
```

### Step 3: Test Staging

```bash
# Load version 1 and make predictions
python scripts/load_and_use_models.py from-registry image-classifier --version 1 --predict

# Transition to Staging
python scripts/load_and_use_models.py transition image-classifier 1 Staging
```

### Step 4: Production Deployment

```bash
# After testing passes
python scripts/load_and_use_models.py transition image-classifier 1 Production

# Production code can now simply load from Production stage
# model = mlflow.pytorch.load_model("models:/image-classifier/Production")
```

---

## 6. Artifact Storage

### Default (Local File Storage)

```
./mlruns/
├── 0/
│   └── abc123def456/
│       ├── artifacts/
│       │   ├── pytorch_model/
│       │   │   ├── model.pkl
│       │   │   ├── conda.yaml
│       │   │   └── MLmodel
│       │   ├── best_model.pt
│       │   ├── model_metadata.json
│       │   └── model_summary.txt
│       ├── metrics/
│       └── params/
└── 1/  (model registry)
```

### Remote Storage (S3, Azure, GCS)

```python
# Set artifact location for experiment
mlflow.create_experiment(
    "prod-experiments",
    artifact_location="s3://my-bucket/mlflow-artifacts"
)

# Or set via environment variable
import os
os.environ["MLFLOW_S3_ENDPOINT_URL"] = "https://s3.amazonaws.com"
```

---

## 7. Advanced: Custom Model Saving

### Save with Custom Dependencies

```python
# Create conda environment file
conda_env = {
    "name": "mlflow-env",
    "channels": ["pytorch", "conda-forge"],
    "dependencies": [
        "python=3.10",
        "pytorch::pytorch",
        "pytorch::torchvision",
        "pip",
        {"pip": ["mlflow==2.10.2"]},
    ],
}

# Log model with custom environment
mlflow.pytorch.log_model(
    model=model,
    artifact_path="pytorch_model",
    conda_env=conda_env,
)
```

### Load Model Without MLflow

If you just want to load the checkpoint:

```python
import torch
from pathlib import Path

# Download from MLflow run
# Or load from saved artifact
checkpoint = torch.load("best_model.pt")
model = SimpleCNN()
model.load_state_dict(checkpoint)
```

---

## 8. Common Issues and Solutions

### Issue: "Model already exists"

When registering a model with a name that already exists:

```python
# Solution: Use different name or check if model exists
client = mlflow.MlflowClient()
try:
    model_version = mlflow.register_model(model_uri, model_name)
except Exception as e:
    if "already exists" in str(e):
        # Get the latest version and register as new version
        models = client.search_model_versions(f"name = '{model_name}'")
        print(f"Model {model_name} exists with {len(models)} versions")
```

### Issue: "Transition invalid"

Can't transition to a stage that's already active:

```python
# Solution: Check current stage first
versions = client.search_model_versions(f"name = '{model_name}'")
for v in versions:
    print(f"Version {v.version}: Stage = {v.current_stage}")
    if v.current_stage != "Production":
        client.transition_model_version_stage(
            name=model_name,
            version=v.version,
            stage="Production"
        )
```

### Issue: Model won't load

Check model directory structure:

```bash
# Inspect saved model
ls -la mlruns/0/<run_id>/artifacts/pytorch_model/

# Should contain:
# - model.pkl
# - conda.yaml
# - MLmodel
# - requirements.txt
```

---

## 9. Key takeaways

| Task | Command/Code |
|------|------|
| Log model | `mlflow.pytorch.log_model(model, "pytorch_model")` |
| Register | `mlflow.register_model(f"runs:/{run_id}/pytorch_model", name)` |
| Load from run | `mlflow.pytorch.load_model(f"runs:/{run_id}/pytorch_model")` |
| Load registered | `mlflow.pytorch.load_model(f"models:/{name}/latest")` |
| Load from stage | `mlflow.pytorch.load_model(f"models:/{name}/Production")` |
| List models | `client.search_registered_models()` |
| List versions | `client.search_model_versions(f"name = '{name}'")` |
| Transition stage | `client.transition_model_version_stage(name, version, stage)` |
