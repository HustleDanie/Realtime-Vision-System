#!/usr/bin/env python3
"""
MLflow Experiments and Artifacts Management Script

Lists all MLflow experiments, shows run details, and verifies model artifacts.
Requires MLflow to be installed: pip install mlflow
"""

import os
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Try to import MLflow
try:
    import mlflow
    from mlflow.tracking import MlflowClient
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    print("⚠️ Warning: MLflow not available. Install with: pip install mlflow")


def run_command(cmd: str) -> tuple[str, int]:
    """Run shell command and return output and exit code."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout + result.stderr, result.returncode
    except Exception as e:
        return f"Error running command: {e}", 1


def list_mlflow_experiments(tracking_uri: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all MLflow experiments with their details."""
    if not MLFLOW_AVAILABLE:
        print("❌ Error: MLflow is not installed")
        return []

    try:
        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)
        
        client = MlflowClient()
        experiments = client.search_experiments()
        
        experiment_list = []
        for exp in experiments:
            exp_dict = {
                "id": exp.experiment_id,
                "name": exp.name,
                "artifact_location": exp.artifact_location,
                "lifecycle_stage": exp.lifecycle_stage,
                # Handle different MLflow versions for creation_timestamp
                "creation_timestamp": getattr(exp, 'creation_timestamp', getattr(exp, 'created_time', 'N/A')),
                "tags": getattr(exp, 'tags', {}),
            }
            
            # Count runs in experiment
            runs = client.search_runs(
                experiment_ids=[exp.experiment_id],
                max_results=1000
            )
            exp_dict["run_count"] = len(runs)
            
            experiment_list.append(exp_dict)
        
        return experiment_list
    except Exception as e:
        print(f"❌ Error listing experiments: {e}")
        return []


def verify_model_artifacts(
    experiment_name: Optional[str] = None,
    artifact_filter: Optional[str] = None,
    tracking_uri: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Verify model artifacts were logged in experiments."""
    if not MLFLOW_AVAILABLE:
        print("❌ Error: MLflow is not installed")
        return []

    try:
        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)
        
        client = MlflowClient()
        experiments = client.search_experiments()
        
        artifacts_found = []
        
        for exp in experiments:
            # Filter by experiment name if specified
            if experiment_name and exp.name != experiment_name:
                continue
            
            runs = client.search_runs(
                experiment_ids=[exp.experiment_id],
                max_results=1000
            )
            
            for run in runs:
                try:
                    # Try to list artifacts - catch exceptions if artifact storage is misconfigured
                    artifacts = client.list_artifacts(run.info.run_id)
                    
                    if artifacts:
                        for artifact in artifacts:
                            artifact_path = artifact.path
                            
                            # Filter by artifact name if specified
                            if artifact_filter and artifact_filter.lower() not in artifact_path.lower():
                                continue
                            
                            artifact_dict = {
                                "experiment_id": exp.experiment_id,
                                "experiment_name": exp.name,
                                "run_id": run.info.run_id,
                                "run_name": getattr(run.info, 'run_name', None) or getattr(run.data, 'tags', {}).get('mlflow.runName', 'N/A'),
                                "artifact_path": artifact_path,
                                "is_dir": artifact.is_dir,
                                "file_size": getattr(artifact, 'file_size', None) or 0,
                                "timestamp": datetime.fromtimestamp(run.info.start_time / 1000).isoformat() if run.info.start_time else "N/A",
                            }
                            
                            artifacts_found.append(artifact_dict)
                except Exception as e:
                    # Silently skip runs with artifact issues (artifact storage misconfiguration)
                    pass
        
        return artifacts_found
    except Exception as e:
        print(f"❌ Error verifying artifacts: {e}")
        return []


def show_experiments_table(experiments: List[Dict[str, Any]]) -> None:
    """Display experiments in formatted table."""
    if not experiments:
        print("No experiments found.")
        return
    
    print("\n" + "=" * 120)
    print(f"{'ID':<8} {'Name':<30} {'Runs':<8} {'Stage':<12} {'Artifact Location':<50}")
    print("=" * 120)
    
    for exp in experiments:
        artifact_loc = exp.get("artifact_location", "")
        if len(artifact_loc) > 47:
            artifact_loc = artifact_loc[:44] + "..."
        
        print(
            f"{exp['id']:<8} "
            f"{exp['name']:<30} "
            f"{exp['run_count']:<8} "
            f"{exp['lifecycle_stage']:<12} "
            f"{artifact_loc:<50}"
        )
    
    print("=" * 120)


def show_artifacts_table(artifacts: List[Dict[str, Any]]) -> None:
    """Display artifacts in formatted table."""
    if not artifacts:
        print("No artifacts found.")
        return
    
    print("\n" + "=" * 140)
    print(
        f"{'Experiment':<25} {'Run':<12} {'Artifact Path':<50} "
        f"{'Type':<8} {'Size':<12} {'Timestamp':<20}"
    )
    print("=" * 140)
    
    for artifact in artifacts:
        artifact_type = "DIR" if artifact.get("is_dir") else "FILE"
        file_size = artifact.get("file_size", "N/A")
        if isinstance(file_size, int):
            if file_size > 1024 * 1024:
                file_size = f"{file_size / (1024 * 1024):.2f} MB"
            elif file_size > 1024:
                file_size = f"{file_size / 1024:.2f} KB"
            else:
                file_size = f"{file_size} B"
        
        artifact_path = artifact.get("artifact_path", "")
        if len(artifact_path) > 47:
            artifact_path = artifact_path[:44] + "..."
        
        exp_name = artifact.get("experiment_name", "")
        if len(exp_name) > 23:
            exp_name = exp_name[:20] + "..."
        
        print(
            f"{exp_name:<25} "
            f"{artifact['run_id'][:12]:<12} "
            f"{artifact_path:<50} "
            f"{artifact_type:<8} "
            f"{file_size:<12} "
            f"{artifact['timestamp']:<20}"
        )
    
    print("=" * 140)


def show_experiments_json(experiments: List[Dict[str, Any]]) -> None:
    """Display experiments as JSON."""
    print(json.dumps(experiments, indent=2, default=str))


def show_artifacts_json(artifacts: List[Dict[str, Any]]) -> None:
    """Display artifacts as JSON."""
    print(json.dumps(artifacts, indent=2, default=str))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="List MLflow experiments and verify model artifacts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all experiments
  python mlflow_experiments_info.py --list-experiments
  
  # List all experiments with artifact details
  python mlflow_experiments_info.py --list-experiments --show-artifacts
  
  # Verify model artifacts
  python mlflow_experiments_info.py --verify-artifacts
  
  # Search for specific artifacts
  python mlflow_experiments_info.py --verify-artifacts --artifact-filter "model"
  
  # Use custom MLflow tracking URI
  python mlflow_experiments_info.py --list-experiments --uri file:///path/to/mlruns
  
  # JSON output
  python mlflow_experiments_info.py --list-experiments --json
        """
    )
    
    parser.add_argument(
        "--list-experiments",
        action="store_true",
        help="List all MLflow experiments"
    )
    
    parser.add_argument(
        "--verify-artifacts",
        action="store_true",
        help="Verify model artifacts were logged"
    )
    
    parser.add_argument(
        "--show-artifacts",
        action="store_true",
        help="Show artifacts for each experiment"
    )
    
    parser.add_argument(
        "--experiment",
        type=str,
        default=None,
        help="Filter by experiment name"
    )
    
    parser.add_argument(
        "--artifact-filter",
        type=str,
        default=None,
        help="Filter artifacts by name/path"
    )
    
    parser.add_argument(
        "--uri",
        type=str,
        default=None,
        help="MLflow tracking URI (default: local)"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    
    args = parser.parse_args()
    
    # If no action specified, show both
    if not args.list_experiments and not args.verify_artifacts:
        args.list_experiments = True
        args.verify_artifacts = True
    
    # Check MLflow availability
    if not MLFLOW_AVAILABLE:
        print("\n❌ MLflow is not installed!")
        print("Install with: pip install mlflow")
        print("\nNote: MLflow requires Python 3.8+")
        return 1
    
    # Set tracking URI if provided
    if args.uri:
        mlflow.set_tracking_uri(args.uri)
        print(f"Using MLflow tracking URI: {args.uri}")
    
    exit_code = 0
    
    # List experiments
    if args.list_experiments:
        print("\n" + "=" * 120)
        print("MLflow Experiments")
        print("=" * 120)
        
        experiments = list_mlflow_experiments(args.uri)
        
        if experiments:
            if args.json:
                show_experiments_json(experiments)
            else:
                show_experiments_table(experiments)
                print(f"\n✓ Found {len(experiments)} experiment(s)")
        else:
            print("✗ No experiments found")
            exit_code = 1
        
        # Show artifacts if requested
        if args.show_artifacts:
            print("\n" + "=" * 140)
            print("Artifacts in Experiments")
            print("=" * 140)
            
            artifacts = verify_model_artifacts(
                experiment_name=args.experiment,
                artifact_filter=args.artifact_filter,
                tracking_uri=args.uri
            )
            
            if artifacts:
                if args.json:
                    show_artifacts_json(artifacts)
                else:
                    show_artifacts_table(artifacts)
                    print(f"\n✓ Found {len(artifacts)} artifact(s)")
            else:
                print("✗ No artifacts found")
    
    # Verify artifacts
    if args.verify_artifacts and not args.list_experiments:
        print("\n" + "=" * 140)
        print("Verifying Model Artifacts")
        print("=" * 140)
        
        artifacts = verify_model_artifacts(
            experiment_name=args.experiment,
            artifact_filter=args.artifact_filter,
            tracking_uri=args.uri
        )
        
        if artifacts:
            if args.json:
                show_artifacts_json(artifacts)
            else:
                show_artifacts_table(artifacts)
                print(f"\n✓ Found {len(artifacts)} artifact(s)")
        else:
            print("✗ No artifacts found")
            exit_code = 1
    
    return exit_code


if __name__ == "__main__":
    exit(main())
