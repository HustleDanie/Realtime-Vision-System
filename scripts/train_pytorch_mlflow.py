"""
PyTorch Training Script with MLflow Integration
Demonstrates experiment tracking, parameter logging, metrics logging, and model saving
"""

import argparse
import time
import mlflow
import mlflow.pytorch
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset


class SimpleCNN(nn.Module):
    """Simple CNN for demonstration purposes"""
    
    def __init__(self, num_classes=10):
        super(SimpleCNN, self).__init__()
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.fc1 = nn.Linear(64 * 8 * 8, 128)
        self.fc2 = nn.Linear(128, num_classes)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.5)
    
    def forward(self, x):
        x = self.pool(self.relu(self.conv1(x)))
        x = self.pool(self.relu(self.conv2(x)))
        x = x.view(-1, 64 * 8 * 8)
        x = self.dropout(self.relu(self.fc1(x)))
        x = self.fc2(x)
        return x


def setup_mlflow(tracking_uri, experiment_name):
    """Configure MLflow tracking"""
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)
    print(f"✓ MLflow tracking URI: {tracking_uri}")
    print(f"✓ MLflow experiment: {experiment_name}")


def log_system_info():
    """Log system information as tags"""
    import platform
    
    tags = {
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "pytorch_version": torch.__version__,
    }
    
    if torch.cuda.is_available():
        tags["cuda_available"] = "true"
        tags["cuda_version"] = torch.version.cuda
        tags["gpu_name"] = torch.cuda.get_device_name(0)
        tags["gpu_memory_gb"] = f"{torch.cuda.get_device_properties(0).total_memory / 1e9:.2f}"
    else:
        tags["cuda_available"] = "false"
    
    for key, value in tags.items():
        mlflow.set_tag(key, value)
    
    return tags


def create_dummy_data(batch_size=32, num_batches=10):
    """Create dummy dataset for demonstration"""
    # Create random data: batch_size * num_batches samples
    X = torch.randn(batch_size * num_batches, 3, 32, 32)
    y = torch.randint(0, 10, (batch_size * num_batches,))
    
    dataset = TensorDataset(X, y)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    return dataloader


def train_epoch(model, dataloader, criterion, optimizer, device, epoch):
    """Train for one epoch"""
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    
    for batch_idx, (inputs, labels) in enumerate(dataloader):
        inputs, labels = inputs.to(device), labels.to(device)
        
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        
        running_loss += loss.item()
        _, predicted = outputs.max(1)
        total += labels.size(0)
        correct += predicted.eq(labels).sum().item()
    
    epoch_loss = running_loss / len(dataloader)
    epoch_acc = 100. * correct / total
    
    return epoch_loss, epoch_acc


def validate_epoch(model, dataloader, criterion, device):
    """Validate the model"""
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0
    
    with torch.no_grad():
        for inputs, labels in dataloader:
            inputs, labels = inputs.to(device), labels.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            
            running_loss += loss.item()
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()
    
    val_loss = running_loss / len(dataloader)
    val_acc = 100. * correct / total
    
    return val_loss, val_acc


def train_with_mlflow(args):
    """Main training function with MLflow tracking"""
    
    # Setup MLflow
    setup_mlflow(args.mlflow_tracking_uri, args.experiment_name)
    
    # Set device
    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    print(f"✓ Using device: {device}")
    
    # Create dummy data
    print(f"✓ Creating dummy dataset (batch_size={args.batch_size})...")
    train_loader = create_dummy_data(args.batch_size, num_batches=10)
    val_loader = create_dummy_data(args.batch_size, num_batches=5)
    
    # Initialize model
    model = SimpleCNN(num_classes=10).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=args.lr)
    total_params = sum(p.numel() for p in model.parameters())
    
    print(f"\n{'='*60}")
    print(f"Starting MLflow Run: {args.run_name or 'Auto-generated'}")
    print(f"{'='*60}\n")
    
    # Start MLflow run
    with mlflow.start_run(run_name=args.run_name):
        
        # Log system information
        system_info = log_system_info()
        print("✓ Logged system information")
        
        # Log hyperparameters
        params = {
            "model": "SimpleCNN",
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.lr,
            "optimizer": "Adam",
            "device": str(device),
            "num_classes": 10,
            "total_parameters": total_params,
        }
        mlflow.log_params(params)
        print("✓ Logged hyperparameters")
        
        # Training loop
        best_val_acc = 0.0
        
        for epoch in range(args.epochs):
            epoch_start_time = time.time()
            
            # Train
            train_loss, train_acc = train_epoch(
                model, train_loader, criterion, optimizer, device, epoch
            )
            
            # Validate
            val_loss, val_acc = validate_epoch(model, val_loader, criterion, device)
            
            epoch_time = time.time() - epoch_start_time
            current_lr = optimizer.param_groups[0].get("lr", args.lr)
            
            # Log metrics to MLflow
            mlflow.log_metrics({
                "train_loss": train_loss,
                "train_accuracy": train_acc,
                "val_loss": val_loss,
                "val_accuracy": val_acc,
                "epoch_time_sec": epoch_time,
                "learning_rate": current_lr,
            }, step=epoch)
            
            # Print progress
            print(f"Epoch {epoch+1}/{args.epochs} | "
                  f"Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.2f}% | "
                  f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.2f}% | "
                  f"Time: {epoch_time:.2f}s")
            
            # Save best model
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                # Log model as MLflow artifact
                mlflow.pytorch.log_model(model, "best_model")
                print(f"  → Saved best model (val_acc: {val_acc:.2f}%)")
        
        # Log final model
        mlflow.pytorch.log_model(model, "final_model")
        
        # Log model summary as artifact
        with open("model_summary.txt", "w") as f:
            f.write(str(model))
            f.write(f"\n\nTotal parameters: {sum(p.numel() for p in model.parameters())}")
        mlflow.log_artifact("model_summary.txt")
        
        # Get run ID
        run_id = mlflow.active_run().info.run_id
        
        print(f"\n{'='*60}")
        print(f"Training Complete!")
        print(f"{'='*60}")
        print(f"Run ID: {run_id}")
        print(f"Best Validation Accuracy: {best_val_acc:.2f}%")
        print(f"\nView results at: {args.mlflow_tracking_uri}")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="PyTorch Training with MLflow")
    
    # MLflow arguments
    parser.add_argument("--mlflow-tracking-uri", type=str, 
                        default="http://127.0.0.1:5000",
                        help="MLflow tracking server URI")
    parser.add_argument("--experiment-name", type=str, 
                        default="pytorch-demo",
                        help="MLflow experiment name")
    parser.add_argument("--run-name", type=str, default=None,
                        help="MLflow run name (optional)")
    
    # Training arguments
    parser.add_argument("--epochs", type=int, default=5,
                        help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=32,
                        help="Batch size for training")
    parser.add_argument("--lr", type=float, default=0.001,
                        help="Learning rate")
    parser.add_argument("--device", type=str, default="cuda",
                        help="Device to use (cuda or cpu)")
    
    args = parser.parse_args()
    
    try:
        train_with_mlflow(args)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure MLflow server is running:")
        print("  python -m mlflow ui --port 5000")
        raise


if __name__ == "__main__":
    main()
