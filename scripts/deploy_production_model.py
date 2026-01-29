#!/usr/bin/env python
"""
Production Model Deployment Script

Pulls the latest Production model from MLflow and updates the inference service container.
Supports both Docker and Kubernetes deployments.

Usage:
    # Docker deployment
    python scripts/deploy_production_model.py --deployment docker

    # Kubernetes deployment
    python scripts/deploy_production_model.py --deployment k8s --namespace production

    # Dry run (simulate without actual changes)
    python scripts/deploy_production_model.py --deployment docker --dry-run

    # With custom model and service names
    python scripts/deploy_production_model.py --deployment docker \
        --model-name yolov8-detector \
        --service-name inference-api
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

import mlflow
import mlflow.pytorch
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class DeploymentConfig:
    """Deployment configuration"""

    deployment_type: str  # 'docker' or 'k8s'
    mlflow_uri: str
    model_name: str
    model_stage: str
    service_name: str
    namespace: Optional[str]
    registry: Optional[str]  # For Docker: registry URL
    image_tag: Optional[str]  # Custom image tag
    dry_run: bool = False
    timeout: int = 300  # Deployment timeout in seconds
    rollback_on_failure: bool = True


class MLFlowModelManager:
    """Manages MLflow model operations"""

    def __init__(self, mlflow_uri: str):
        self.mlflow_uri = mlflow_uri
        mlflow.set_tracking_uri(mlflow_uri)
        self.client = mlflow.tracking.MlflowClient(tracking_uri=mlflow_uri)

    def get_production_model_uri(self, model_name: str) -> str:
        """Get URI of the latest Production model"""
        try:
            model_version = self.client.get_model_version_by_stage(
                name=model_name, stage="Production"
            )
            model_uri = f"models:/{model_name}/Production"
            logger.info(f"Found Production model: {model_uri}")
            logger.info(
                f"  Model URI: models://{model_name}/Production"
            )
            logger.info(f"  Version: {model_version.version}")
            logger.info(f"  Created: {model_version.creation_timestamp}")
            return model_uri
        except Exception as e:
            logger.error(f"Failed to get Production model: {e}")
            raise

    def get_production_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get detailed info about Production model"""
        try:
            model_version = self.client.get_model_version_by_stage(
                name=model_name, stage="Production"
            )
            return {
                "name": model_name,
                "version": model_version.version,
                "uri": f"models:/{model_name}/Production",
                "created_at": datetime.fromtimestamp(
                    model_version.creation_timestamp / 1000
                ).isoformat(),
                "status": model_version.status,
                "description": model_version.description,
            }
        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            raise

    def validate_model(self, model_name: str) -> bool:
        """Validate that Production model exists and is ready"""
        try:
            self.get_production_model_info(model_name)
            logger.info("✓ Production model validation passed")
            return True
        except Exception as e:
            logger.error(f"✗ Production model validation failed: {e}")
            return False


class DockerDeployment:
    """Manages Docker container deployment"""

    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.container_name = config.service_name
        self.image_name = config.service_name
        self.registry = config.registry or "localhost"
        self.image_tag = config.image_tag or "latest"
        self.full_image_name = f"{self.registry}/{self.image_name}:{self.image_tag}"

    def build_image(self) -> bool:
        """Build Docker image with latest model"""
        logger.info("Building Docker image...")

        cmd = ["docker", "build", "-t", self.full_image_name, "."]

        if self.config.dry_run:
            logger.info(f"[DRY-RUN] Would execute: {' '.join(cmd)}")
            return True

        try:
            result = subprocess.run(
                cmd,
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode != 0:
                logger.error(f"Docker build failed: {result.stderr}")
                return False

            logger.info(f"✓ Docker image built: {self.full_image_name}")
            return True

        except subprocess.TimeoutExpired:
            logger.error("Docker build timeout")
            return False
        except Exception as e:
            logger.error(f"Docker build error: {e}")
            return False

    def push_image(self) -> bool:
        """Push image to registry"""
        if self.registry == "localhost" or self.registry == "127.0.0.1":
            logger.info("Skipping push (local registry)")
            return True

        logger.info(f"Pushing image to {self.registry}...")

        cmd = ["docker", "push", self.full_image_name]

        if self.config.dry_run:
            logger.info(f"[DRY-RUN] Would execute: {' '.join(cmd)}")
            return True

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode != 0:
                logger.error(f"Docker push failed: {result.stderr}")
                return False

            logger.info(f"✓ Image pushed: {self.full_image_name}")
            return True

        except subprocess.TimeoutExpired:
            logger.error("Docker push timeout")
            return False
        except Exception as e:
            logger.error(f"Docker push error: {e}")
            return False

    def get_running_container(self) -> Optional[str]:
        """Get ID of running container"""
        try:
            result = subprocess.run(
                ["docker", "ps", "-q", "-f", f"name={self.container_name}"],
                capture_output=True,
                text=True,
            )
            container_id = result.stdout.strip()
            return container_id if container_id else None
        except Exception as e:
            logger.error(f"Failed to get running container: {e}")
            return None

    def stop_container(self) -> bool:
        """Stop running container"""
        container_id = self.get_running_container()

        if not container_id:
            logger.info("No running container found")
            return True

        logger.info(f"Stopping container {container_id}...")

        cmd = ["docker", "stop", container_id]

        if self.config.dry_run:
            logger.info(f"[DRY-RUN] Would execute: {' '.join(cmd)}")
            return True

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                logger.error(f"Failed to stop container: {result.stderr}")
                return False

            logger.info(f"✓ Container stopped")
            time.sleep(2)  # Give it time to stop
            return True

        except Exception as e:
            logger.error(f"Error stopping container: {e}")
            return False

    def start_container(self, env_vars: Optional[Dict[str, str]] = None) -> bool:
        """Start new container with latest image"""
        logger.info(f"Starting container from {self.full_image_name}...")

        # Build docker run command
        cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            self.container_name,
            "-p",
            "8000:8000",
            "-e",
            f"MLFLOW_TRACKING_URI={self.config.mlflow_uri}",
            "-e",
            f"MODEL_NAME={self.config.model_name}",
            "-e",
            f"MODEL_STAGE={self.config.model_stage}",
        ]

        # Add custom environment variables
        if env_vars:
            for key, value in env_vars.items():
                cmd.extend(["-e", f"{key}={value}"])

        cmd.append(self.full_image_name)

        if self.config.dry_run:
            logger.info(f"[DRY-RUN] Would execute: {' '.join(cmd)}")
            return True

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                logger.error(f"Failed to start container: {result.stderr}")
                return False

            container_id = result.stdout.strip()
            logger.info(f"✓ Container started: {container_id}")

            # Wait for container to be healthy
            return self.wait_for_health()

        except Exception as e:
            logger.error(f"Error starting container: {e}")
            return False

    def wait_for_health(self, retries: int = 10) -> bool:
        """Wait for container to be healthy"""
        logger.info("Waiting for container health check...")

        for attempt in range(retries):
            try:
                result = subprocess.run(
                    [
                        "docker",
                        "exec",
                        self.container_name,
                        "curl",
                        "-f",
                        "http://localhost:8000/health",
                    ],
                    capture_output=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    logger.info("✓ Container is healthy")
                    return True

            except Exception:
                pass

            if attempt < retries - 1:
                time.sleep(3)
                logger.info(
                    f"  Health check attempt {attempt + 1}/{retries}..."
                )

        logger.error("Container health check failed")
        return False

    def deploy(self) -> bool:
        """Execute full deployment"""
        logger.info("=" * 60)
        logger.info("DOCKER DEPLOYMENT")
        logger.info("=" * 60)

        # Build image
        if not self.build_image():
            return False

        # Push to registry (if not local)
        if not self.push_image():
            return False

        # Stop old container
        if not self.stop_container():
            return False

        # Start new container
        env_vars = {
            "MLFLOW_TRACKING_URI": self.config.mlflow_uri,
            "MODEL_NAME": self.config.model_name,
            "MODEL_STAGE": self.config.model_stage,
        }

        if not self.start_container(env_vars):
            logger.error("Deployment failed")
            return False

        logger.info("✓ Docker deployment successful")
        return True


class KubernetesDeployment:
    """Manages Kubernetes deployment"""

    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.namespace = config.namespace or "default"
        self.deployment_name = config.service_name
        self.image_name = config.service_name
        self.registry = config.registry or "localhost:5000"
        self.image_tag = config.image_tag or "latest"
        self.full_image_name = f"{self.registry}/{self.image_name}:{self.image_tag}"

    def build_and_push_image(self) -> bool:
        """Build and push image for K8s"""
        logger.info("Building and pushing image for Kubernetes...")

        # Build
        cmd = ["docker", "build", "-t", self.full_image_name, "."]

        if not self.config.dry_run:
            try:
                result = subprocess.run(
                    cmd,
                    cwd=Path(__file__).parent.parent,
                    capture_output=True,
                    text=True,
                    timeout=600,
                )

                if result.returncode != 0:
                    logger.error(f"Docker build failed: {result.stderr}")
                    return False

                logger.info(f"✓ Image built: {self.full_image_name}")

            except Exception as e:
                logger.error(f"Build error: {e}")
                return False
        else:
            logger.info(f"[DRY-RUN] Would build: {self.full_image_name}")

        # Push
        cmd = ["docker", "push", self.full_image_name]

        if not self.config.dry_run:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600,
                )

                if result.returncode != 0:
                    logger.error(f"Docker push failed: {result.stderr}")
                    return False

                logger.info(f"✓ Image pushed: {self.full_image_name}")
                return True

            except Exception as e:
                logger.error(f"Push error: {e}")
                return False
        else:
            logger.info(f"[DRY-RUN] Would push: {self.full_image_name}")
            return True

    def get_current_deployment(self) -> Optional[Dict[str, Any]]:
        """Get current deployment info"""
        cmd = [
            "kubectl",
            "get",
            "deployment",
            self.deployment_name,
            "-n",
            self.namespace,
            "-o",
            "json",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                logger.warning(f"Deployment not found: {result.stderr}")
                return None

            return json.loads(result.stdout)

        except Exception as e:
            logger.error(f"Failed to get deployment: {e}")
            return None

    def patch_deployment(self) -> bool:
        """Patch deployment with new image"""
        logger.info(f"Patching Kubernetes deployment {self.deployment_name}...")

        cmd = [
            "kubectl",
            "set",
            "image",
            f"deployment/{self.deployment_name}",
            f"{self.deployment_name}={self.full_image_name}",
            "-n",
            self.namespace,
        ]

        if self.config.dry_run:
            logger.info(f"[DRY-RUN] Would execute: {' '.join(cmd)}")
            return True

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                logger.error(f"Failed to patch deployment: {result.stderr}")
                return False

            logger.info("✓ Deployment patched")
            return True

        except Exception as e:
            logger.error(f"Error patching deployment: {e}")
            return False

    def rollout_status(self) -> bool:
        """Wait for rollout to complete"""
        logger.info("Waiting for rollout to complete...")

        cmd = [
            "kubectl",
            "rollout",
            "status",
            f"deployment/{self.deployment_name}",
            "-n",
            self.namespace,
            f"--timeout={self.config.timeout}s",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout + 10,
            )

            if result.returncode != 0:
                logger.error(f"Rollout failed: {result.stderr}")
                return False

            logger.info("✓ Rollout completed successfully")
            return True

        except subprocess.TimeoutExpired:
            logger.error("Rollout timeout")
            return False
        except Exception as e:
            logger.error(f"Error checking rollout status: {e}")
            return False

    def update_environment_variables(self) -> bool:
        """Update deployment environment variables"""
        logger.info("Updating environment variables...")

        # Get current deployment
        deployment = self.get_current_deployment()
        if not deployment:
            logger.error("Failed to get current deployment")
            return False

        # Update model-related env vars
        containers = deployment["spec"]["template"]["spec"]["containers"]
        for container in containers:
            if "env" not in container:
                container["env"] = []

            # Update or add env vars
            env_dict = {e["name"]: e for e in container["env"]}
            env_dict["MLFLOW_TRACKING_URI"] = {
                "name": "MLFLOW_TRACKING_URI",
                "value": self.config.mlflow_uri,
            }
            env_dict["MODEL_NAME"] = {
                "name": "MODEL_NAME",
                "value": self.config.model_name,
            }
            env_dict["MODEL_STAGE"] = {
                "name": "MODEL_STAGE",
                "value": self.config.model_stage,
            }

            container["env"] = list(env_dict.values())

        # Apply updated deployment
        cmd = [
            "kubectl",
            "apply",
            "-f",
            "-",
            "-n",
            self.namespace,
        ]

        if self.config.dry_run:
            logger.info(f"[DRY-RUN] Would update deployment with:")
            logger.info(yaml.dump(deployment, default_flow_style=False))
            return True

        try:
            result = subprocess.run(
                cmd,
                input=yaml.dump(deployment),
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                logger.error(f"Failed to apply deployment: {result.stderr}")
                return False

            logger.info("✓ Environment variables updated")
            return True

        except Exception as e:
            logger.error(f"Error updating env vars: {e}")
            return False

    def deploy(self) -> bool:
        """Execute full Kubernetes deployment"""
        logger.info("=" * 60)
        logger.info("KUBERNETES DEPLOYMENT")
        logger.info("=" * 60)
        logger.info(f"Namespace: {self.namespace}")
        logger.info(f"Deployment: {self.deployment_name}")
        logger.info(f"Image: {self.full_image_name}")

        # Get current deployment
        current = self.get_current_deployment()
        if not current:
            logger.error("Deployment not found. Please create it first.")
            return False

        # Build and push image
        if not self.build_and_push_image():
            return False

        # Update environment variables
        if not self.update_environment_variables():
            return False

        # Patch deployment with new image
        if not self.patch_deployment():
            return False

        # Wait for rollout
        if not self.rollout_status():
            if self.config.rollback_on_failure:
                logger.warning("Attempting rollback...")
                self.rollback()
            return False

        logger.info("✓ Kubernetes deployment successful")
        return True

    def rollback(self) -> bool:
        """Rollback to previous deployment"""
        logger.info("Rolling back deployment...")

        cmd = [
            "kubectl",
            "rollout",
            "undo",
            f"deployment/{self.deployment_name}",
            "-n",
            self.namespace,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                logger.error(f"Rollback failed: {result.stderr}")
                return False

            logger.info("✓ Rollback completed")
            return True

        except Exception as e:
            logger.error(f"Rollback error: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Production model from MLflow to inference service"
    )

    # Required arguments
    parser.add_argument(
        "--deployment",
        choices=["docker", "k8s"],
        required=True,
        help="Deployment type (docker or k8s)",
    )

    # Optional arguments
    parser.add_argument(
        "--mlflow-uri",
        default=os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"),
        help="MLflow tracking URI",
    )
    parser.add_argument(
        "--model-name",
        default=os.getenv("MODEL_NAME", "simple-cnn-demo"),
        help="MLflow model name",
    )
    parser.add_argument(
        "--model-stage",
        default="Production",
        help="MLflow model stage (default: Production)",
    )
    parser.add_argument(
        "--service-name",
        default="inference-service",
        help="Service/deployment name",
    )
    parser.add_argument(
        "--namespace",
        help="Kubernetes namespace (only for k8s)",
    )
    parser.add_argument(
        "--registry",
        help="Docker/K8s registry URL",
    )
    parser.add_argument(
        "--image-tag",
        default="latest",
        help="Docker image tag",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate deployment without making changes",
    )
    parser.add_argument(
        "--no-rollback",
        action="store_true",
        help="Don't rollback on failure (K8s only)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Deployment timeout in seconds",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip image build step",
    )

    args = parser.parse_args()

    # Create configuration
    config = DeploymentConfig(
        deployment_type=args.deployment,
        mlflow_uri=args.mlflow_uri,
        model_name=args.model_name,
        model_stage=args.model_stage,
        service_name=args.service_name,
        namespace=args.namespace,
        registry=args.registry,
        image_tag=args.image_tag,
        dry_run=args.dry_run,
        timeout=args.timeout,
        rollback_on_failure=not args.no_rollback,
    )

    logger.info(f"Configuration: {config}")

    try:
        # Validate MLflow model
        logger.info("Validating MLflow model...")
        mlflow_manager = MLFlowModelManager(config.mlflow_uri)

        if not mlflow_manager.validate_model(config.model_name):
            logger.error("MLflow validation failed")
            return 1

        model_info = mlflow_manager.get_production_model_info(
            config.model_name
        )
        logger.info(f"Model to deploy: {json.dumps(model_info, indent=2)}")

        # Execute deployment
        if config.deployment_type == "docker":
            deployer = DockerDeployment(config)
            success = deployer.deploy()
        else:  # k8s
            deployer = KubernetesDeployment(config)
            success = deployer.deploy()

        if success:
            logger.info("=" * 60)
            logger.info("✓ DEPLOYMENT SUCCESSFUL")
            logger.info("=" * 60)
            logger.info(f"Model: {config.model_name}")
            logger.info(f"Stage: {config.model_stage}")
            logger.info(f"Deployment: {config.deployment_type}")
            return 0
        else:
            logger.error("=" * 60)
            logger.error("✗ DEPLOYMENT FAILED")
            logger.error("=" * 60)
            return 1

    except Exception as e:
        logger.error(f"Deployment error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
