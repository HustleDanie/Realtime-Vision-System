"""
Complete MLflow Workflow: Train, Save, Log, and Register PyTorch Model

Demonstrates:
1. Training a PyTorch model
2. Saving the model as an artifact
3. Logging the model to MLflow
4. Registering the model in MLflow Model Registry
5. Loading and using registered models
"""

import argparse
import time
import json
import mlflow
import mlflow.pytorch
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from pathlib import Path


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


def create_dummy_data(batch_size=32, num_batches=10):
    """Create dummy dataset for demonstration"""
    X = torch.randn(batch_size * num_batches, 3, 32, 32)
    y = torch.randint(0, 10, (batch_size * num_batches,))
    
    dataset = TensorDataset(X, y)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    return dataloader


def train_epoch(model, dataloader, criterion, optimizer, device):
    """Train for one epoch"""
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    
    for inputs, labels in dataloader:
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


def save_model_locally(model, save_dir, model_name="model.pt"):
    """Save model locally as checkpoint"""
    Path(save_dir).mkdir(parents=True, exist_ok=True)
    checkpoint_path = Path(save_dir) / model_name
    torch.save(model.state_dict(), checkpoint_path)
    return str(checkpoint_path)


def log_model_metrics_and_artifacts(model, val_acc, val_loss, checkpoint_path):
    """Log model info, metrics, and artifacts to MLflow"""
    
    # Log performance metrics
    mlflow.log_metrics({
        "final_val_accuracy": val_acc,
        "final_val_loss": val_loss,
    })
    
    # Save and log model using MLflow's PyTorch integration
    # This automatically handles the entire model saving/loading pipeline
    mlflow.pytorch.log_model(model, "pytorch_model")
    print("✓ Logged model using mlflow.pytorch.log_model()")
    
    # Also log the checkpoint file as a generic artifact
    mlflow.log_artifact(checkpoint_path)
    print(f"✓ Logged checkpoint artifact: {checkpoint_path}")
    
    # Create and log model metadata
    metadata = {
        "model_name": "SimpleCNN",
        "model_class": "SimpleCNN",
        "input_shape": [1, 3, 32, 32],
        "output_shape": [1, 10],
        "num_classes": 10,
    }
    with open("model_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    mlflow.log_artifact("model_metadata.json")
    print("✓ Logged model metadata")


def register_model(run_id, model_name, description=None):
    """
    Register model in MLflow Model Registry
    
    Args:
        run_id: MLflow run ID where the model was logged
        model_name: Name to register the model under
        description: Optional description of the model
    
    Returns:
        model_version: Registered model version
    """
    try:
        # Create model URI from the run
        model_uri = f"runs:/{run_id}/pytorch_model"
        
        # Register the model
        model_version = mlflow.register_model(model_uri, model_name)
        print(f"✓ Model registered: {model_name} (version {model_version.version})")
        
        # Set description and tags
        client = mlflow.MlflowClient()
        client.update_model_version(
            name=model_name,
            version=model_version.version,
            description=description or "SimpleCNN trained model"
        )
        
        # Optionally transition to production
        # client.transition_model_version_stage(
        #     name=model_name,
        #     version=model_version.version,
        #     stage="Production"
        # )
        
        return model_version
    
    except Exception as e:
        print(f"⚠ Model registration failed: {e}")
        print("  This may occur if the model is already registered.")
        return None


def train_and_register(args):
    """Train model and register it in MLflow"""
    
    setup_mlflow(args.mlflow_tracking_uri, args.experiment_name)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"✓ Using device: {device}")
    
    # Data
    print(f"✓ Creating dataset (batch_size={args.batch_size})...")
    train_loader = create_dummy_data(args.batch_size, num_batches=10)
    val_loader = create_dummy_data(args.batch_size, num_batches=5)
    
    # Model
    model = SimpleCNN(num_classes=10).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=args.lr)
    total_params = sum(p.numel() for p in model.parameters())
    
    print(f"\n{'='*70}")
    print(f"Starting Training Run: {args.run_name or 'Auto-generated'}")
    print(f"{'='*70}\n")
    
    with mlflow.start_run(run_name=args.run_name) as run:
        
        # Log parameters
        mlflow.log_params({
            "model": "SimpleCNN",
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.lr,
            "optimizer": "Adam",
            "device": str(device),
            "total_parameters": total_params,
        })
        print("✓ Logged hyperparameters")
        
        # Training loop
        best_val_acc = 0.0
        best_checkpoint = None
        
        for epoch in range(args.epochs):
            train_loss, train_acc = train_epoch(
                model, train_loader, criterion, optimizer, device
            )
            val_loss, val_acc = validate_epoch(model, val_loader, criterion, device)
            
            current_lr = optimizer.param_groups[0].get("lr", args.lr)
            
            mlflow.log_metrics({
                "train_loss": train_loss,
                "train_accuracy": train_acc,
                "val_loss": val_loss,
                "val_accuracy": val_acc,
                "learning_rate": current_lr,
            }, step=epoch)
            
            print(f"Epoch {epoch+1}/{args.epochs} | "
                  f"Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.2f}% | "
                  f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.2f}%")
            
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                # Save best checkpoint locally
                best_checkpoint = save_model_locally(model, "checkpoints", "best_model.pt")
                print(f"  → New best model saved (val_acc: {val_acc:.2f}%)")
        
        # Log models and artifacts to MLflow
        print(f"\n{'='*70}")
        print("Logging Models and Artifacts to MLflow")
        print(f"{'='*70}\n")
        
        log_model_metrics_and_artifacts(model, best_val_acc, val_loss, best_checkpoint)
        
        # Get run ID for model registration
        run_id = run.info.run_id
        
        # Register the model
        print(f"\n{'='*70}")
        print("Registering Model in MLflow Model Registry")
        print(f"{'='*70}\n")
        
        model_version = register_model(
            run_id,
            model_name=args.model_name,
            description=f"SimpleCNN trained with lr={args.lr}, batch_size={args.batch_size}"
        )
        
        # Summary
        print(f"\n{'='*70}")
        print("Training & Registration Complete!")
        print(f"{'='*70}")
        print(f"Run ID: {run_id}")
        print(f"Best Validation Accuracy: {best_val_acc:.2f}%")
        if model_version:
            print(f"Model Name: {args.model_name}")
            print(f"Model Version: {model_version.version}")
            print(f"Model URI: models:/{args.model_name}/{model_version.version}")
        print(f"\nView at: {args.mlflow_tracking_uri}")
        print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Train PyTorch model and register in MLflow"
    )
    
    # MLflow arguments
    parser.add_argument("--mlflow-tracking-uri", type=str, 
                        default="http://127.0.0.1:5000",
                        help="MLflow tracking server URI")
    parser.add_argument("--experiment-name", type=str, 
                        default="pytorch-model-registry",
                        help="MLflow experiment name")
    parser.add_argument("--run-name", type=str, default=None,
                        help="MLflow run name (optional)")
    parser.add_argument("--model-name", type=str, 
                        default="simple-cnn-classifier",
                        help="Name to register model under in MLflow Model Registry")
    
    # Training arguments
    parser.add_argument("--epochs", type=int, default=5,
                        help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=32,
                        help="Batch size for training")
    parser.add_argument("--lr", type=float, default=0.001,
                        help="Learning rate")
    
    args = parser.parse_args()
    
    try:
        train_and_register(args)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
