#!/usr/bin/env python3
"""
Extract model information from MLflow promotion webhook.

This script is called by GitHub Actions when a model is promoted to Production.
It extracts the model name and version, then sets GitHub Actions output variables.

Usage:
    python extract_model_info.py
    
Environment Variables:
    WEBHOOK_PAYLOAD: JSON payload from GitHub dispatch event
    MLFLOW_TRACKING_URI: MLflow tracking server URI
"""

import json
import os
import sys
import subprocess
from datetime import datetime


def setup_github_output(key, value):
    """Set GitHub Actions output variable."""
    output_file = os.getenv('GITHUB_OUTPUT')
    if output_file:
        with open(output_file, 'a') as f:
            f.write(f'{key}={value}\n')
    print(f"::set-output name={key}::{value}")


def get_production_model_info():
    """Get latest Production model from MLflow."""
    try:
        import mlflow
        
        mlflow_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://127.0.0.1:5000')
        mlflow.set_tracking_uri(mlflow_uri)
        
        client = mlflow.tracking.MlflowClient()
        
        # Get all registered models
        registered_models = client.search_registered_models()
        
        if not registered_models:
            print("❌ No registered models found in MLflow")
            return None, None, None
            
        # Try to find Production model from webhook first
        webhook_payload = os.getenv('WEBHOOK_PAYLOAD', '{}')
        try:
            payload = json.loads(webhook_payload)
            model_name = payload.get('model_name')
            model_version = payload.get('model_version')
            
            if model_name and model_version:
                # Validate model exists and version is Production
                versions = client.get_latest_versions(model_name, stages=['Production'])
                if versions:
                    prod_version = versions[0]
                    print(f"✓ Using model from webhook: {model_name} v{prod_version.version}")
                    return model_name, prod_version.version, None
        except (json.JSONDecodeError, KeyError, AttributeError):
            pass
        
        # Fallback: Get the latest Production model across all models
        print("Searching for Production model in MLflow...")
        latest_prod_model = None
        latest_timestamp = 0
        
        for model in registered_models:
            try:
                versions = client.get_latest_versions(model.name, stages=['Production'])
                if versions:
                    version = versions[0]
                    timestamp = version.creation_timestamp or 0
                    
                    if timestamp > latest_timestamp:
                        latest_timestamp = timestamp
                        latest_prod_model = (model.name, version.version)
                        
                        print(f"  - {model.name} v{version.version} (created: {version.creation_timestamp})")
            except Exception as e:
                print(f"  ⚠ Error checking {model.name}: {e}")
        
        if not latest_prod_model:
            print("❌ No Production model found")
            return None, None, None
        
        model_name, model_version = latest_prod_model
        print(f"✓ Using latest Production model: {model_name} v{model_version}")
        
        return model_name, model_version, None
        
    except ImportError:
        print("❌ mlflow not installed. Run: pip install mlflow")
        return None, None, None
    except Exception as e:
        print(f"❌ Error getting model info: {e}")
        return None, None, None


def generate_image_tag(model_name, model_version):
    """Generate Docker image tag from model info."""
    timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
    # Sanitize model name for Docker tag (replace invalid characters)
    safe_name = model_name.lower().replace('_', '-').replace('.', '-')
    return f"{safe_name}-v{model_version}-{timestamp}"


def main():
    """Main entry point."""
    print("=" * 60)
    print("Extracting Model Information")
    print("=" * 60)
    
    model_name, model_version, error = get_production_model_info()
    
    if not model_name or not model_version:
        print("❌ Failed to extract model information")
        sys.exit(1)
    
    image_tag = generate_image_tag(model_name, model_version)
    
    print()
    print("Extracted Information:")
    print(f"  Model Name: {model_name}")
    print(f"  Model Version: {model_version}")
    print(f"  Image Tag: {image_tag}")
    print()
    
    # Set GitHub Actions outputs
    setup_github_output('model_name', model_name)
    setup_github_output('model_version', model_version)
    setup_github_output('image_tag', image_tag)
    
    print("✓ Model information extracted and set as outputs")
    return 0


if __name__ == '__main__':
    sys.exit(main())
