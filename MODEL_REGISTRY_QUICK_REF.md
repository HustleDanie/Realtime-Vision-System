# MLflow Model Registry - Quick Reference

## Quick Start Commands

### 1. Train and Register a Model

```bash
python scripts/train_and_register_model.py \
    --experiment-name "my-experiments" \
    --model-name "my-classifier" \
    --epochs 10
```

**Output:** `Model registered as "my-classifier" (version 1)`

---

### 2. List Registered Models

```bash
python scripts/load_and_use_models.py list
```

**Output:**
```
📦 Model: my-classifier
   Latest Version: 1
   Latest Stage: None
```

---

### 3. Load and Use Model

```bash
# Load from MLflow run
python scripts/load_and_use_models.py from-run <RUN_ID> --predict

# Load latest registered model
python scripts/load_and_use_models.py from-registry my-classifier --predict

# Load specific version
python scripts/load_and_use_models.py from-registry my-classifier --version 1 --predict

# Load from Production stage
python scripts/load_and_use_models.py from-registry my-classifier --stage Production
```

---

### 4. Manage Versions

```bash
# List all versions
python scripts/load_and_use_models.py versions my-classifier

# Promote to Production
python scripts/load_and_use_models.py transition my-classifier 1 Production

# Move to Staging
python scripts/load_and_use_models.py transition my-classifier 1 Staging

# Archive old version
python scripts/load_and_use_models.py transition my-classifier 0 Archived
```

---

## Model URIs

```
runs:/{run_id}/pytorch_model
├─ Used to load a model from a specific experiment run
└─ Example: runs:/abc123/pytorch_model

models:/{model_name}/latest
├─ Load the latest version of a registered model
└─ Example: models:/my-classifier/latest

models:/{model_name}/{version}
├─ Load a specific version by number
└─ Example: models:/my-classifier/2

models:/{model_name}/{stage}
├─ Load from a stage (Staging, Production, Archived)
└─ Example: models:/my-classifier/Production
```

---

## What Gets Saved

### Artifacts (per run)
- `pytorch_model/` - Full model (pkl, conda.yaml, requirements.txt, MLmodel)
- `best_model.pt` - Model checkpoint
- `model_metadata.json` - Model info
- `model_summary.txt` - Architecture

### Model Registry
- Version history
- Stage transitions
- Run lineage
- Descriptions and tags

---

## Python Code Examples

### Save and Log

```python
import mlflow
import mlflow.pytorch

# Train model...
model = train_model()

# Log to MLflow
mlflow.pytorch.log_model(model, "pytorch_model")

# Register in registry
model_version = mlflow.register_model(
    "runs:/{run_id}/pytorch_model", 
    "my-model"
)
```

### Load and Predict

```python
import mlflow.pytorch

# From registry
model = mlflow.pytorch.load_model("models:/my-model/Production")

# Make predictions
predictions = model(input_data)
```

### Manage Versions

```python
client = mlflow.MlflowClient()

# Transition to Production
client.transition_model_version_stage(
    name="my-model",
    version=1,
    stage="Production"
)

# List versions
versions = client.search_model_versions("name = 'my-model'")
for v in versions:
    print(f"Version {v.version}: {v.current_stage}")
```

---

## Stage Workflow

```
None (Initial)
  ↓
Staging (Testing)
  ↓
Production (Active)
  ↓
Archived (Retired)
```

---

## Where Files Are Stored

```
./mlruns/
├── 0/                           # Experiment 0
│   ├── abc123/                  # Run abc123
│   │   ├── artifacts/
│   │   │   ├── pytorch_model/   # Model with env info
│   │   │   ├── best_model.pt    # Checkpoint
│   │   │   └── model_metadata.json
│   │   ├── metrics/             # Performance metrics
│   │   └── params/              # Hyperparameters
│   └── def456/
└── 1/                           # Experiment 1 (Model Registry metadata)
    └── ...
```

---

## Common Scenarios

### Scenario 1: Deploy Model to Production

```bash
# 1. Train and register
python scripts/train_and_register_model.py --model-name "production-model"

# 2. Test in staging
python scripts/load_and_use_models.py transition production-model 1 Staging

# 3. After testing, promote
python scripts/load_and_use_models.py transition production-model 1 Production

# 4. Production app loads via:
# model = mlflow.pytorch.load_model("models:/production-model/Production")
```

### Scenario 2: A/B Testing Models

```bash
# Train model A
python scripts/train_and_register_model.py --model-name "classifier-v1" --run-name "exp-a"

# Train model B
python scripts/train_and_register_model.py --model-name "classifier-v1" --run-name "exp-b"

# Compare versions
python scripts/load_and_use_models.py versions classifier-v1

# Load and test each
python scripts/load_and_use_models.py from-registry classifier-v1 --version 1 --predict
python scripts/load_and_use_models.py from-registry classifier-v1 --version 2 --predict

# Promote winner
python scripts/load_and_use_models.py transition classifier-v1 2 Production
```

### Scenario 3: Rollback to Previous Version

```bash
# Current production has issues
# View all versions
python scripts/load_and_use_models.py versions my-model

# Rollback to previous version
python scripts/load_and_use_models.py transition my-model 2 Archived
python scripts/load_and_use_models.py transition my-model 1 Production
```

---

## Troubleshooting

### Model won't register

```bash
# Check if model exists
python scripts/load_and_use_models.py list

# Use different model name if needed
python scripts/train_and_register_model.py --model-name "my-model-v2"
```

### Port 5000 already in use

```bash
# Start MLflow on different port
python -m mlflow ui --port 5001

# Run script pointing to new port
python scripts/train_and_register_model.py --mlflow-tracking-uri http://127.0.0.1:5001
```

### Missing dependencies when loading model

The model includes conda.yaml and requirements.txt. Install them:

```bash
pip install -r requirements.txt
# or
conda env create -f conda.yaml
```

---

## Next Steps

- Integrate with deployment platforms (Docker, Kubernetes)
- Set up automated testing in Staging
- Use model registry with team collaboration
- Monitor model performance in production
- Implement model retraining pipelines
