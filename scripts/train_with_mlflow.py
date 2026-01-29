"""
PyTorch training script with MLflow tracking integration.

Logs metrics, parameters, and artifacts to MLflow tracking server.

Usage:
    # Start MLflow server first:
    docker-compose -f docker-compose.mlflow.yml up -d
    
    # Then run training:
    python scripts/train_with_mlflow.py \
        --experiment-name vision-training \
        --epochs 10 \
        --batch-size 16 \
        --lr 0.001
"""

import argparse
import time
from pathlib import Path
from typing import Dict, Any

import torch
import torch.nn as nn
import torch.optim as optim
import mlflow
import mlflow.pytorch


class SimpleCNN(nn.Module):
    """Simple CNN for demonstration."""
    
    def __init__(self, num_classes: int = 10):
        super(SimpleCNN, self).__init__()
        self.conv1 = nn.Conv2d(3, 32, 3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, 3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.fc1 = nn.Linear(64 * 8 * 8, 128)
        self.fc2 = nn.Linear(128, num_classes)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.5)
    
    def forward(self, x):
        x = self.pool(self.relu(self.conv1(x)))
        x = self.pool(self.relu(self.conv2(x)))
        x = x.view(-1, 64 * 8 * 8)
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        return x


def setup_mlflow(args: argparse.Namespace) -> None:
    """
    Configure MLflow tracking server connection.
    
    Args:
        args: Command-line arguments with MLflow config
    """
    # Set tracking URI (MLflow server address)
    mlflow.set_tracking_uri(args.mlflow_tracking_uri)
    
    # Set or create experiment
    mlflow.set_experiment(args.experiment_name)
    
    print(f"✓ MLflow tracking URI: {args.mlflow_tracking_uri}")
    print(f"✓ Experiment: {args.experiment_name}")
    print(f"✓ MLflow UI: http://localhost:5000")


def log_system_info() -> Dict[str, Any]:
    """Log system and environment information."""
    info = {
        "cuda_available": torch.cuda.is_available(),
        "cuda_device_count": torch.cuda.device_count(),
        "pytorch_version": torch.__version__,
    }
    
    if torch.cuda.is_available():
        info["cuda_version"] = torch.version.cuda
        info["gpu_name"] = torch.cuda.get_device_name(0)
        info["gpu_memory_gb"] = torch.cuda.get_device_properties(0).total_memory / 1e9
    
    return info


def train_epoch(
    model: nn.Module,
    optimizer: optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
    epoch: int,
) -> Dict[str, float]:
    """
    Train for one epoch (simplified/mock training).
    
    Args:
        model: Neural network model
        optimizer: Optimizer
        criterion: Loss function
        device: Training device
        epoch: Current epoch number
        
    Returns:
        Dictionary with training metrics
    """
    model.train()
    
    # Simulate training batch
    # In real training, iterate over DataLoader
    dummy_input = torch.randn(16, 3, 32, 32).to(device)
    dummy_target = torch.randint(0, 10, (16,)).to(device)
    
    optimizer.zero_grad()
    output = model(dummy_input)
    loss = criterion(output, dummy_target)
    loss.backward()
    optimizer.step()
    
    # Calculate accuracy
    _, predicted = torch.max(output.data, 1)
    accuracy = (predicted == dummy_target).sum().item() / dummy_target.size(0)
    
    return {
        "train_loss": loss.item(),
        "train_accuracy": accuracy,
    }


def validate_epoch(
    model: nn.Module,
    criterion: nn.Module,
    device: torch.device,
    epoch: int,
) -> Dict[str, float]:
    """
    Validate for one epoch (simplified/mock validation).
    
    Args:
        model: Neural network model
        criterion: Loss function
        device: Device
        epoch: Current epoch number
        
    Returns:
        Dictionary with validation metrics
    """
    model.eval()
    
    with torch.no_grad():
        # Simulate validation batch
        dummy_input = torch.randn(16, 3, 32, 32).to(device)
        dummy_target = torch.randint(0, 10, (16,)).to(device)
        
        output = model(dummy_input)
        loss = criterion(output, dummy_target)
        
        _, predicted = torch.max(output.data, 1)
        accuracy = (predicted == dummy_target).sum().item() / dummy_target.size(0)
    
    return {
        "val_loss": loss.item(),
        "val_accuracy": accuracy,
    }


def train_with_mlflow(args: argparse.Namespace) -> None:
    """
    Main training loop with MLflow tracking.
    
    Args:
        args: Training arguments
    """
    # Setup device
    device = torch.device("cuda" if torch.cuda.is_available() and args.device != "cpu" else "cpu")
    print(f"\n✓ Using device: {device}")
    
    # Start MLflow run
    with mlflow.start_run(run_name=args.run_name):
        
        # Log parameters
        params = {
            "model": "SimpleCNN",
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.lr,
            "optimizer": "Adam",
            "device": str(device),
            "num_classes": 10,
        }
        mlflow.log_params(params)
        print("\n✓ Logged parameters to MLflow")
        
        # Log system info as tags
        system_info = log_system_info()
        mlflow.set_tags(system_info)
        print("✓ Logged system info as tags")
        
        # Initialize model
        model = SimpleCNN(num_classes=10).to(device)
        optimizer = optim.Adam(model.parameters(), lr=args.lr)
        criterion = nn.CrossEntropyLoss()
        
        print(f"\n{'='*70}")
        print("TRAINING")
        print(f"{'='*70}\n")
        
        best_val_acc = 0.0
        
        # Training loop
        for epoch in range(args.epochs):
            start_time = time.time()
            
            # Train
            train_metrics = train_epoch(model, optimizer, criterion, device, epoch)
            
            # Validate
            val_metrics = validate_epoch(model, criterion, device, epoch)
            
            epoch_time = time.time() - start_time
            
            # Log metrics to MLflow
            mlflow.log_metrics({
                **train_metrics,
                **val_metrics,
                "epoch_time_sec": epoch_time,
            }, step=epoch)
            
            # Print progress
            print(f"Epoch {epoch+1}/{args.epochs} | "
                  f"Train Loss: {train_metrics['train_loss']:.4f} | "
                  f"Train Acc: {train_metrics['train_accuracy']:.3f} | "
                  f"Val Loss: {val_metrics['val_loss']:.4f} | "
                  f"Val Acc: {val_metrics['val_accuracy']:.3f} | "
                  f"Time: {epoch_time:.2f}s")
            
            # Save best model
            if val_metrics['val_accuracy'] > best_val_acc:
                best_val_acc = val_metrics['val_accuracy']
                
                # Save checkpoint locally
                checkpoint_path = Path("checkpoints")
                checkpoint_path.mkdir(exist_ok=True)
                torch.save(model.state_dict(), checkpoint_path / "best_model.pth")
                
                # Log model to MLflow
                mlflow.pytorch.log_model(model, "best_model")
                mlflow.log_metric("best_val_accuracy", best_val_acc)
                
                print(f"  → Saved best model (acc: {best_val_acc:.3f})")
        
        # Log final model
        mlflow.pytorch.log_model(model, "final_model")
        
        # Log training artifacts
        if (checkpoint_path / "best_model.pth").exists():
            mlflow.log_artifact(str(checkpoint_path / "best_model.pth"))
        
        # Log model summary as text artifact
        model_summary = f"""Model Architecture:
{model}

Total Parameters: {sum(p.numel() for p in model.parameters())}
Trainable Parameters: {sum(p.numel() for p in model.parameters() if p.requires_grad)}
"""
        with open("model_summary.txt", "w") as f:
            f.write(model_summary)
        mlflow.log_artifact("model_summary.txt")
        
        print(f"\n{'='*70}")
        print("TRAINING COMPLETE")
        print(f"{'='*70}")
        print(f"✓ Best validation accuracy: {best_val_acc:.3f}")
        print(f"✓ Run ID: {mlflow.active_run().info.run_id}")
        print(f"✓ View results: http://localhost:5000")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="PyTorch training with MLflow tracking",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    
    # MLflow config
    parser.add_argument(
        "--mlflow-tracking-uri",
        type=str,
        default="http://localhost:5000",
        help="MLflow tracking server URI",
    )
    parser.add_argument(
        "--experiment-name",
        type=str,
        default="vision-training",
        help="MLflow experiment name",
    )
    parser.add_argument(
        "--run-name",
        type=str,
        default=None,
        help="MLflow run name (optional)",
    )
    
    # Training config
    parser.add_argument(
        "--epochs",
        type=int,
        default=10,
        help="Number of training epochs",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Batch size",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=0.001,
        help="Learning rate",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Training device",
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Setup MLflow connection
    setup_mlflow(args)
    
    try:
        # Run training with MLflow tracking
        train_with_mlflow(args)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Log error to MLflow if run is active
        if mlflow.active_run():
            mlflow.set_tag("error", str(e))
            mlflow.end_run(status="FAILED")


if __name__ == "__main__":
    main()
