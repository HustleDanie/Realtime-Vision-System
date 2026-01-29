# MLflow Tracking Setup Guide

## Quick Start

### 1. Start MLflow Tracking Server

```bash
# Using Docker Compose (recommended)
docker-compose -f docker-compose.mlflow.yml up -d

# Check status
docker-compose -f docker-compose.mlflow.yml ps

# View logs
docker-compose -f docker-compose.mlflow.yml logs -f
```

The MLflow UI will be available at: **http://localhost:5000**

### 2. Install Python Dependencies

```bash
pip install mlflow torch torchvision
```

### 3. Run Training with MLflow Tracking

```bash
# Basic training
python scripts/train_with_mlflow.py

# With custom parameters
python scripts/train_with_mlflow.py \
    --experiment-name my-vision-model \
    --run-name experiment-001 \
    --epochs 20 \
    --batch-size 32 \
    --lr 0.001

# Connect to remote MLflow server
python scripts/train_with_mlflow.py \
    --mlflow-tracking-uri http://mlflow-server:5000 \
    --experiment-name production-training
```

### 4. View Results in MLflow UI

1. Open http://localhost:5000 in your browser
2. Navigate to your experiment
3. View metrics, parameters, and artifacts
4. Compare multiple runs
5. Download trained models

## What Gets Logged

### Parameters (Hyperparameters)
- Model architecture
- Epochs, batch size, learning rate
- Optimizer type
- Device (CPU/GPU)
- Number of classes

### Metrics (Time Series)
- Training loss
- Training accuracy
- Validation loss
- Validation accuracy
- Epoch time
- Best validation accuracy

### Artifacts (Files)
- Best model checkpoint (PyTorch format)
- Final model
- Model summary (architecture + parameter count)
- Training logs

### Tags (Metadata)
- CUDA availability
- GPU name and memory
- PyTorch version
- CUDA version

## MLflow Server Configuration

### Using SQLite (Default)
```yaml
# Suitable for local development
backend-store-uri: sqlite:///mlflow/mlflow.db
artifact-root: /mlruns
```

### Using PostgreSQL (Production)
```yaml
# Uncomment postgres service in docker-compose.mlflow.yml
backend-store-uri: postgresql://mlflow:mlflow@postgres:5432/mlflow
artifact-root: s3://my-bucket/mlruns  # or other cloud storage
```

## MLflow CLI Commands

```bash
# List experiments
mlflow experiments list --tracking-uri http://localhost:5000

# Search runs
mlflow runs list --experiment-id 0 --tracking-uri http://localhost:5000

# Delete experiment
mlflow experiments delete --experiment-id 1 --tracking-uri http://localhost:5000

# Download artifacts
mlflow artifacts download \
    --run-id <run-id> \
    --artifact-path best_model \
    --dst-path ./downloaded_models
```

## Integration with Training Pipeline

### Connect Existing Training Script

```python
import mlflow

# Set tracking server
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("my-experiment")

# Start run
with mlflow.start_run():
    # Log parameters
    mlflow.log_param("learning_rate", 0.001)
    mlflow.log_param("batch_size", 32)
    
    # Training loop
    for epoch in range(epochs):
        train_loss = train_one_epoch()
        val_loss = validate()
        
        # Log metrics
        mlflow.log_metric("train_loss", train_loss, step=epoch)
        mlflow.log_metric("val_loss", val_loss, step=epoch)
    
    # Log model
    mlflow.pytorch.log_model(model, "model")
    
    # Log artifacts
    mlflow.log_artifact("config.yaml")
```

## Compare Multiple Experiments

```python
import mlflow

# Get experiment
experiment = mlflow.get_experiment_by_name("vision-training")

# Search runs
runs = mlflow.search_runs(
    experiment_ids=[experiment.experiment_id],
    filter_string="metrics.val_accuracy > 0.8",
    order_by=["metrics.val_accuracy DESC"],
    max_results=10,
)

print(runs[["run_id", "params.learning_rate", "metrics.val_accuracy"]])
```

## Load Trained Model

```python
import mlflow.pytorch

# Load model from MLflow
model_uri = "runs:/<run-id>/best_model"
model = mlflow.pytorch.load_model(model_uri)

# Or download and load manually
mlflow.artifacts.download_artifacts(
    run_id="<run-id>",
    artifact_path="best_model.pth",
    dst_path="./models"
)
```

## Docker Compose Commands

```bash
# Start server
docker-compose -f docker-compose.mlflow.yml up -d

# Stop server
docker-compose -f docker-compose.mlflow.yml down

# Stop and remove volumes
docker-compose -f docker-compose.mlflow.yml down -v

# View logs
docker-compose -f docker-compose.mlflow.yml logs -f mlflow-server

# Restart server
docker-compose -f docker-compose.mlflow.yml restart
```

## Production Deployment

### Using PostgreSQL + S3

1. Update `docker-compose.mlflow.yml`:
```yaml
services:
  mlflow-server:
    environment:
      - MLFLOW_BACKEND_STORE_URI=postgresql://user:pass@postgres:5432/mlflow
      - MLFLOW_ARTIFACT_ROOT=s3://my-bucket/mlruns
      - AWS_ACCESS_KEY_ID=<key>
      - AWS_SECRET_ACCESS_KEY=<secret>
```

2. Enable PostgreSQL service:
```yaml
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: mlflow
      POSTGRES_PASSWORD: mlflow
      POSTGRES_DB: mlflow
```

### Authentication (Optional)

Add basic auth using nginx reverse proxy:
```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "5000:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./htpasswd:/etc/nginx/.htpasswd
```

## Troubleshooting

### Connection Refused
```bash
# Check if MLflow server is running
docker ps | grep mlflow

# Check logs
docker logs mlflow-tracking-server

# Test connection
curl http://localhost:5000/health
```

### Permissions Issues
```bash
# Fix volume permissions
sudo chown -R $(id -u):$(id -g) mlruns/
```

### Port Already in Use
```bash
# Change port in docker-compose.mlflow.yml
ports:
  - "5001:5000"  # Use 5001 instead

# Update tracking URI in training script
--mlflow-tracking-uri http://localhost:5001
```

## Best Practices

1. **Use Experiments** to group related runs
2. **Tag Runs** with metadata (git commit, dataset version, etc.)
3. **Log Parameters** before training starts
4. **Log Metrics** at each epoch/batch
5. **Save Best Model** based on validation metrics
6. **Use Run Names** for easy identification
7. **Add Notes** to runs for context
8. **Compare Runs** to identify best hyperparameters

## Resources

- MLflow Documentation: https://mlflow.org/docs/latest/index.html
- MLflow Tracking: https://mlflow.org/docs/latest/tracking.html
- MLflow Models: https://mlflow.org/docs/latest/models.html
- REST API: https://mlflow.org/docs/latest/rest-api.html
