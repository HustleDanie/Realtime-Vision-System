# MLflow Quick Start Guide (Without Docker)

## Setup

### 1. Install MLflow and PyTorch

```bash
pip install mlflow torch torchvision
```

### 2. Start MLflow Tracking Server

Open a terminal and run:

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000
```

This starts the MLflow UI at **http://127.0.0.1:5000**

Keep this terminal running in the background.

## Run Training Script

In a new terminal:

```bash
python scripts/train_pytorch_mlflow.py --experiment-name my-experiment --epochs 10
```

### Command-Line Options

```bash
python scripts/train_pytorch_mlflow.py \
    --mlflow-tracking-uri http://127.0.0.1:5000 \
    --experiment-name "pytorch-demo" \
    --run-name "test-run-1" \
    --epochs 10 \
    --batch-size 32 \
    --lr 0.001 \
    --device cuda
```

**Parameters:**
- `--mlflow-tracking-uri`: MLflow server URL (default: http://127.0.0.1:5000)
- `--experiment-name`: Name for grouping related runs
- `--run-name`: Optional name for this specific run
- `--epochs`: Number of training epochs (default: 5)
- `--batch-size`: Batch size (default: 32)
- `--lr`: Learning rate (default: 0.001)
- `--device`: cuda or cpu (default: cuda)

## What Gets Tracked

MLflow automatically logs:

### 1. **Parameters**
- Model architecture
- Hyperparameters (epochs, batch_size, learning_rate)
- Optimizer type
- Device (CPU/GPU)

### 2. **Metrics** (per epoch)
- Training loss and accuracy
- Validation loss and accuracy
- Epoch training time

### 3. **Artifacts**
- Best model (PyTorch checkpoint)
- Final model (PyTorch checkpoint)
- Model summary (architecture details)

### 4. **System Tags**
- Platform (Windows/Linux/macOS)
- Python version
- PyTorch version
- CUDA availability and version
- GPU name and memory

## View Results

1. Open browser: **http://127.0.0.1:5000**
2. Navigate to your experiment
3. View metrics, compare runs, download models

## Compare Multiple Runs

```bash
# Run 1: baseline
python scripts/train_pytorch_mlflow.py --run-name "baseline" --lr 0.001 --epochs 10

# Run 2: higher learning rate
python scripts/train_pytorch_mlflow.py --run-name "high-lr" --lr 0.01 --epochs 10

# Run 3: larger batch size
python scripts/train_pytorch_mlflow.py --run-name "large-batch" --batch-size 64 --epochs 10
```

Then compare all runs in the MLflow UI.

## Load Saved Model

```python
import mlflow.pytorch

# Load model by run ID
run_id = "YOUR_RUN_ID_HERE"
model = mlflow.pytorch.load_model(f"runs:/{run_id}/best_model")

# Or load latest version
model = mlflow.pytorch.load_model("models:/pytorch-demo/latest")
```

## Using Local File Storage (No Server)

If you don't want to run a server, MLflow can log to local files:

```python
# In your script, set tracking URI to a local directory
mlflow.set_tracking_uri("file:///path/to/mlruns")
```

Or via command line:

```bash
python scripts/train_pytorch_mlflow.py --mlflow-tracking-uri file:///./mlruns
```

Then view results later:

```bash
mlflow ui --backend-store-uri file:///./mlruns
```

## Troubleshooting

### Server not starting

```bash
# Check if port 5000 is in use
netstat -an | findstr :5000

# Use a different port
mlflow ui --port 5001
python scripts/train_pytorch_mlflow.py --mlflow-tracking-uri http://127.0.0.1:5001
```

### Connection refused

Make sure the MLflow server is running before starting training.

### CUDA not available

The script automatically falls back to CPU if CUDA is not available. To force CPU:

```bash
python scripts/train_pytorch_mlflow.py --device cpu
```

## Next Steps

- Integrate with DVC for dataset versioning
- Add custom metrics and plots
- Set up remote tracking server for team collaboration
- Deploy models with MLflow Models
