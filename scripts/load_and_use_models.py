"""
Load and Use Models from MLflow Model Registry

Demonstrates:
1. Loading models from MLflow runs
2. Loading registered models by name and version
3. Making predictions with loaded models
4. Model versioning and stage transitions
"""

import argparse
import mlflow
import mlflow.pytorch
import torch
import torch.nn as nn
from pathlib import Path


def load_model_from_run(tracking_uri, run_id, model_path="pytorch_model"):
    """
    Load a model from a specific MLflow run
    
    Args:
        tracking_uri: MLflow tracking server URI
        run_id: Run ID where the model was logged
        model_path: Path within the run (default: "pytorch_model")
    
    Returns:
        Loaded PyTorch model
    """
    mlflow.set_tracking_uri(tracking_uri)
    
    # Build the model URI
    model_uri = f"runs:/{run_id}/{model_path}"
    
    print(f"Loading model from run: {model_uri}")
    model = mlflow.pytorch.load_model(model_uri)
    print(f"✓ Model loaded successfully")
    
    return model


def load_registered_model(tracking_uri, model_name, version=None, stage=None):
    """
    Load a registered model from MLflow Model Registry
    
    Args:
        tracking_uri: MLflow tracking server URI
        model_name: Name of the registered model
        version: Specific version number (e.g., 1, 2, 3)
        stage: Stage name (e.g., "Staging", "Production")
                Either version or stage should be specified
    
    Returns:
        Loaded PyTorch model
    """
    mlflow.set_tracking_uri(tracking_uri)
    
    # Build model URI
    if version:
        model_uri = f"models:/{model_name}/{version}"
        print(f"Loading model: {model_uri}")
    elif stage:
        model_uri = f"models:/{model_name}/{stage}"
        print(f"Loading model: {model_uri}")
    else:
        # Default to latest version
        model_uri = f"models:/{model_name}/latest"
        print(f"Loading model: {model_uri}")
    
    try:
        model = mlflow.pytorch.load_model(model_uri)
        print(f"✓ Model loaded successfully")
        return model
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        return None


def list_registered_models(tracking_uri):
    """List all registered models"""
    mlflow.set_tracking_uri(tracking_uri)
    client = mlflow.MlflowClient()
    
    print("\n" + "="*70)
    print("Registered Models in MLflow Model Registry")
    print("="*70 + "\n")
    
    try:
        models = client.search_registered_models()
        
        if not models:
            print("No registered models found.")
            return []
        
        for model in models:
            print(f"📦 Model: {model.name}")
            print(f"   Description: {model.description or 'N/A'}")
            print(f"   Latest Version: {model.latest_versions[0].version}")
            print(f"   Latest Stage: {model.latest_versions[0].current_stage}")
            print()
        
        return models
    except Exception as e:
        print(f"Error listing models: {e}")
        return []


def list_model_versions(tracking_uri, model_name):
    """List all versions of a registered model"""
    mlflow.set_tracking_uri(tracking_uri)
    client = mlflow.MlflowClient()
    
    print(f"\n{'='*70}")
    print(f"Versions of Model: {model_name}")
    print(f"{'='*70}\n")
    
    try:
        versions = client.search_model_versions(f"name = '{model_name}'")
        
        if not versions:
            print(f"No versions found for {model_name}")
            return []
        
        for version in versions:
            print(f"Version {version.version}:")
            print(f"  Stage: {version.current_stage}")
            print(f"  Status: {version.status}")
            print(f"  Description: {version.description or 'N/A'}")
            print(f"  Run ID: {version.run_id}")
            print()
        
        return versions
    except Exception as e:
        print(f"Error listing versions: {e}")
        return []


def transition_model_stage(tracking_uri, model_name, version, stage):
    """
    Transition a model version to a new stage
    
    Stages: "None", "Staging", "Production", "Archived"
    """
    mlflow.set_tracking_uri(tracking_uri)
    client = mlflow.MlflowClient()
    
    print(f"Transitioning {model_name} v{version} to stage '{stage}'...")
    
    try:
        client.transition_model_version_stage(
            name=model_name,
            version=version,
            stage=stage
        )
        print(f"✓ Successfully transitioned to {stage}")
    except Exception as e:
        print(f"❌ Failed to transition: {e}")


def make_predictions(model, num_samples=5):
    """Make predictions with the loaded model"""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    model.eval()
    
    print(f"\n{'='*70}")
    print("Making Predictions")
    print(f"{'='*70}\n")
    
    with torch.no_grad():
        # Generate random input
        x = torch.randn(num_samples, 3, 32, 32).to(device)
        
        # Get predictions
        outputs = model(x)
        probabilities = torch.softmax(outputs, dim=1)
        predictions = torch.argmax(probabilities, dim=1)
        
        # Display results
        for i in range(num_samples):
            pred_class = predictions[i].item()
            confidence = probabilities[i, pred_class].item() * 100
            print(f"Sample {i+1}: Class {pred_class} (confidence: {confidence:.2f}%)")


def main():
    parser = argparse.ArgumentParser(
        description="Load and use models from MLflow Model Registry"
    )
    
    parser.add_argument("--mlflow-tracking-uri", type=str,
                        default="http://127.0.0.1:5000",
                        help="MLflow tracking server URI")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List registered models
    list_parser = subparsers.add_parser("list", help="List registered models")
    
    # List versions of a model
    versions_parser = subparsers.add_parser("versions", help="List versions of a model")
    versions_parser.add_argument("model_name", help="Name of the registered model")
    
    # Load from run
    run_parser = subparsers.add_parser("from-run", help="Load model from a specific run")
    run_parser.add_argument("run_id", help="MLflow run ID")
    run_parser.add_argument("--model-path", default="pytorch_model",
                           help="Path within the run (default: pytorch_model)")
    run_parser.add_argument("--predict", action="store_true",
                           help="Make sample predictions after loading")
    
    # Load registered model
    registry_parser = subparsers.add_parser("from-registry", 
                                            help="Load registered model")
    registry_parser.add_argument("model_name", help="Name of the registered model")
    registry_parser.add_argument("--version", type=int,
                                help="Specific version number (e.g., 1, 2, 3)")
    registry_parser.add_argument("--stage", default="latest",
                                help="Stage: latest, Staging, Production, Archived")
    registry_parser.add_argument("--predict", action="store_true",
                                help="Make sample predictions after loading")
    
    # Transition stage
    transition_parser = subparsers.add_parser("transition",
                                             help="Transition model to a stage")
    transition_parser.add_argument("model_name", help="Name of the registered model")
    transition_parser.add_argument("version", type=int, help="Version number")
    transition_parser.add_argument("stage",
                                  choices=["None", "Staging", "Production", "Archived"],
                                  help="Target stage")
    
    args = parser.parse_args()
    
    try:
        if args.command == "list":
            list_registered_models(args.mlflow_tracking_uri)
        
        elif args.command == "versions":
            list_model_versions(args.mlflow_tracking_uri, args.model_name)
        
        elif args.command == "from-run":
            model = load_model_from_run(
                args.mlflow_tracking_uri,
                args.run_id,
                args.model_path
            )
            if model and args.predict:
                make_predictions(model)
        
        elif args.command == "from-registry":
            model = load_registered_model(
                args.mlflow_tracking_uri,
                args.model_name,
                version=args.version,
                stage=args.stage
            )
            if model and args.predict:
                make_predictions(model)
        
        elif args.command == "transition":
            transition_model_stage(
                args.mlflow_tracking_uri,
                args.model_name,
                args.version,
                args.stage
            )
        
        else:
            parser.print_help()
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
