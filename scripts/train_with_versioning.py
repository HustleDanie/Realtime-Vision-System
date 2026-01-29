"""
Training script with DVC dataset version tracking.

This script logs the exact dataset version (Git commit + DVC hash) used during
training, enabling full experiment reproducibility.

Usage:
    python scripts/train_with_versioning.py \
        --model yolov8m \
        --epochs 50 \
        --batch-size 16 \
        --output-dir training_runs/exp001
"""

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


def get_git_commit_hash() -> str:
    """Get current Git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"


def get_git_commit_message() -> str:
    """Get current Git commit message."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"


def get_dvc_dataset_hash(dvc_file: str = "dataset.dvc") -> Optional[str]:
    """
    Extract DVC dataset hash from .dvc file.
    
    Args:
        dvc_file: Path to the .dvc file
        
    Returns:
        MD5 hash of the dataset or None if not found
    """
    try:
        import yaml
        with open(dvc_file, "r") as f:
            dvc_data = yaml.safe_load(f)
        
        # DVC stores hash in 'outs' section
        if dvc_data and "outs" in dvc_data:
            for out in dvc_data["outs"]:
                if "md5" in out:
                    return out["md5"]
        return None
    except Exception as e:
        print(f"Warning: Could not read DVC hash: {e}")
        return None


def check_git_uncommitted_changes() -> bool:
    """Check if there are uncommitted changes in Git."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        return len(result.stdout.strip()) > 0
    except subprocess.CalledProcessError:
        return False


def check_dvc_dataset_synced() -> bool:
    """Check if DVC dataset is synced with remote."""
    try:
        result = subprocess.run(
            ["python", "-m", "dvc", "status"],
            capture_output=True,
            text=True,
            check=True,
        )
        # If output is empty, everything is synced
        return len(result.stdout.strip()) == 0
    except subprocess.CalledProcessError:
        return False


def create_experiment_metadata(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Create comprehensive experiment metadata including dataset version.
    
    Args:
        args: Training arguments
        
    Returns:
        Dictionary with all experiment metadata
    """
    git_commit = get_git_commit_hash()
    git_message = get_git_commit_message()
    dvc_hash = get_dvc_dataset_hash("dataset.dvc")
    has_uncommitted = check_git_uncommitted_changes()
    dvc_synced = check_dvc_dataset_synced()
    
    metadata = {
        # Experiment info
        "experiment_name": args.experiment_name,
        "timestamp": datetime.utcnow().isoformat(),
        
        # Dataset versioning
        "dataset": {
            "git_commit": git_commit,
            "git_commit_message": git_message,
            "dvc_hash": dvc_hash,
            "git_has_uncommitted_changes": has_uncommitted,
            "dvc_synced": dvc_synced,
            "dataset_path": "dataset/",
        },
        
        # Training config
        "training": {
            "model": args.model,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.lr,
            "image_size": args.img_size,
        },
        
        # Environment
        "environment": {
            "device": args.device,
        },
        
        # Reproducibility instructions
        "reproduction_commands": [
            f"git checkout {git_commit}",
            "python -m dvc checkout",
            f"python scripts/train_with_versioning.py --model {args.model} --epochs {args.epochs} --batch-size {args.batch_size}",
        ],
    }
    
    return metadata


def save_experiment_metadata(metadata: Dict[str, Any], output_dir: Path) -> None:
    """
    Save experiment metadata to JSON file.
    
    Args:
        metadata: Experiment metadata dictionary
        output_dir: Output directory for training run
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_file = output_dir / "experiment_metadata.json"
    
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✓ Experiment metadata saved to: {metadata_file}")


def print_experiment_info(metadata: Dict[str, Any]) -> None:
    """Print experiment information to console."""
    print("\n" + "="*70)
    print("EXPERIMENT TRACKING")
    print("="*70)
    print(f"\nExperiment: {metadata['experiment_name']}")
    print(f"Timestamp: {metadata['timestamp']}")
    
    print("\n📦 Dataset Version:")
    dataset = metadata["dataset"]
    print(f"  Git commit: {dataset['git_commit'][:8]}")
    print(f"  Git message: {dataset['git_commit_message']}")
    print(f"  DVC hash: {dataset['dvc_hash'][:16]}..." if dataset['dvc_hash'] else "  DVC hash: unknown")
    
    if dataset['git_has_uncommitted_changes']:
        print("  ⚠️  WARNING: Uncommitted changes detected!")
    if not dataset['dvc_synced']:
        print("  ⚠️  WARNING: DVC dataset not synced with remote!")
    
    print("\n🔧 Training Config:")
    training = metadata["training"]
    print(f"  Model: {training['model']}")
    print(f"  Epochs: {training['epochs']}")
    print(f"  Batch size: {training['batch_size']}")
    print(f"  Learning rate: {training['learning_rate']}")
    
    print("\n📋 To reproduce this experiment:")
    for cmd in metadata["reproduction_commands"]:
        print(f"  {cmd}")
    
    print("\n" + "="*70 + "\n")


def run_training(args: argparse.Namespace, metadata: Dict[str, Any]) -> None:
    """
    Run actual training (placeholder - implement your training logic).
    
    Args:
        args: Training arguments
        metadata: Experiment metadata
    """
    print("Starting training...")
    print(f"Model: {args.model}")
    print(f"Dataset: {metadata['dataset']['dataset_path']}")
    print(f"Epochs: {args.epochs}")
    print(f"Batch size: {args.batch_size}")
    
    # TODO: Implement actual training logic here
    # Example:
    # model = load_model(args.model)
    # dataset = load_dataset(metadata['dataset']['dataset_path'])
    # trainer = Trainer(model, dataset, epochs=args.epochs, batch_size=args.batch_size)
    # trainer.train()
    # model.save(output_dir / "best_model.pt")
    
    print("\n✓ Training completed (placeholder)")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Training script with DVC dataset version tracking",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    
    # Experiment info
    parser.add_argument(
        "--experiment-name",
        type=str,
        default=f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        help="Experiment name",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="training_runs/latest",
        help="Output directory for training artifacts",
    )
    
    # Model config
    parser.add_argument(
        "--model",
        type=str,
        default="yolov8m",
        help="Model architecture",
    )
    
    # Training config
    parser.add_argument(
        "--epochs",
        type=int,
        default=50,
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
        "--img-size",
        type=int,
        default=640,
        help="Input image size",
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
    """Main training entry point."""
    args = parse_args()
    output_dir = Path(args.output_dir)
    
    # Create experiment metadata with dataset versioning
    print("Collecting experiment metadata...")
    metadata = create_experiment_metadata(args)
    
    # Save metadata to disk
    save_experiment_metadata(metadata, output_dir)
    
    # Print experiment information
    print_experiment_info(metadata)
    
    # Warn if environment is not clean
    if metadata["dataset"]["git_has_uncommitted_changes"]:
        response = input("⚠️  Uncommitted changes detected. Continue? (y/N): ")
        if response.lower() != "y":
            print("Training aborted.")
            return
    
    # Run training
    run_training(args, metadata)
    
    print(f"\n✓ Training artifacts saved to: {output_dir}")
    print(f"✓ Experiment metadata: {output_dir / 'experiment_metadata.json'}")


if __name__ == "__main__":
    main()
