# Production Model Deployment Scripts

Complete deployment automation for pulling the latest Production model from MLflow and updating the inference service container.

## Overview

These scripts provide three ways to deploy the latest Production model to your inference service:

1. **Python Script** (`deploy_production_model.py`) - Full-featured with detailed logging
2. **PowerShell Script** (`deploy-production-model.ps1`) - Windows-friendly with interactive feedback
3. **Bash Script** (`deploy-production-model.sh`) - Linux/Mac with POSIX compatibility

All three support:
- ✅ **Docker Deployment**: Build, push, and run container with new model
- ✅ **Kubernetes Deployment**: Build, push, patch deployment, wait for rollout
- ✅ **Model Validation**: Confirm Production model exists before deployment
- ✅ **Health Checks**: Verify container/pods are healthy after deployment
- ✅ **Dry Run Mode**: Simulate deployment without making changes
- ✅ **Automatic Rollback**: Rollback on Kubernetes failure (optional)
- ✅ **Timeout Control**: Configurable deployment timeout

## Prerequisites

### Common Requirements
- MLflow tracking server running (default: `http://127.0.0.1:5000`)
- Python 3.8+ with MLflow installed
- Production model registered in MLflow

### Docker Deployment
- Docker installed and running
- Docker credentials configured (if using remote registry)
- Dockerfile in project root

### Kubernetes Deployment
- kubectl configured and authenticated
- Deployment already exists in cluster
- Registry credentials configured (if using private registry)

## Installation

Scripts are ready to use in the `scripts/` directory. Make bash scripts executable:

```bash
chmod +x scripts/deploy-production-model.sh
```

## Usage

### Quick Start

#### Docker Deployment (Python)
```bash
python scripts/deploy_production_model.py --deployment docker
```

#### Kubernetes Deployment (Python)
```bash
python scripts/deploy_production_model.py --deployment k8s --namespace production
```

#### Docker Deployment (PowerShell)
```powershell
.\scripts\deploy-production-model.ps1 -Deployment docker
```

#### Docker Deployment (Bash)
```bash
./scripts/deploy-production-model.sh docker
```

### Common Options

#### Dry Run (Simulate without changes)
```bash
# Python
python scripts/deploy_production_model.py --deployment docker --dry-run

# PowerShell
.\scripts\deploy-production-model.ps1 -Deployment docker -DryRun

# Bash
./scripts/deploy-production-model.sh docker --dry-run
```

#### Custom Model Name
```bash
# Python
python scripts/deploy_production_model.py --deployment docker --model-name yolov8-detector

# PowerShell
.\scripts\deploy-production-model.ps1 -Deployment docker -ModelName yolov8-detector

# Bash
./scripts/deploy-production-model.sh docker --model-name yolov8-detector
```

#### Custom MLflow URI
```bash
# Python
python scripts/deploy_production_model.py --deployment docker --mlflow-uri http://mlflow.company.com:5000

# PowerShell
.\scripts\deploy-production-model.ps1 -Deployment docker -MlflowUri "http://mlflow.company.com:5000"

# Bash
./scripts/deploy-production-model.sh docker --mlflow-uri http://mlflow.company.com:5000
```

#### Kubernetes with Custom Namespace
```bash
# Python
python scripts/deploy_production_model.py --deployment k8s --namespace production

# PowerShell
.\scripts\deploy-production-model.ps1 -Deployment k8s -Namespace production

# Bash
./scripts/deploy-production-model.sh k8s --namespace production
```

#### Custom Docker Registry
```bash
# Python
python scripts/deploy_production_model.py --deployment docker --registry myregistry.azurecr.io

# PowerShell
.\scripts\deploy-production-model.ps1 -Deployment docker -Registry "myregistry.azurecr.io"

# Bash
./scripts/deploy-production-model.sh docker --registry myregistry.azurecr.io
```

### Advanced Options

#### Skip Image Build (use existing image)
```bash
# Python
python scripts/deploy_production_model.py --deployment k8s --skip-build

# PowerShell
.\scripts\deploy-production-model.ps1 -Deployment k8s -SkipBuild

# Bash
./scripts/deploy-production-model.sh k8s --skip-build
```

#### Custom Image Tag
```bash
# Python
python scripts/deploy_production_model.py --deployment docker --image-tag v2.0.0

# PowerShell
.\scripts\deploy-production-model.ps1 -Deployment docker -ImageTag "v2.0.0"

# Bash
./scripts/deploy-production-model.sh docker --image-tag v2.0.0
```

#### Disable Automatic Rollback (Kubernetes)
```bash
# Python
python scripts/deploy_production_model.py --deployment k8s --no-rollback

# PowerShell
.\scripts\deploy-production-model.ps1 -Deployment k8s -NoRollback

# Bash
./scripts/deploy-production-model.sh k8s --no-rollback
```

#### Custom Timeout
```bash
# Python
python scripts/deploy_production_model.py --deployment k8s --timeout 600

# PowerShell
.\scripts\deploy-production-model.ps1 -Deployment k8s -Timeout 600

# Bash
./scripts/deploy-production-model.sh k8s --timeout 600
```

## Docker Deployment

### How It Works

1. **Validate Model**: Check Production model exists in MLflow
2. **Build Image**: Run `docker build` with latest code
3. **Push Image**: Push to registry (skipped for localhost)
4. **Stop Container**: Stop currently running container
5. **Start Container**: Run new container with new image
6. **Health Check**: Verify container responds to health endpoint

### Example: Deploy to Local Docker

```bash
python scripts/deploy_production_model.py \
  --deployment docker \
  --mlflow-uri http://127.0.0.1:5000 \
  --model-name simple-cnn-demo \
  --service-name inference-service \
  --registry localhost
```

### Example: Deploy to Azure Container Registry

```bash
python scripts/deploy_production_model.py \
  --deployment docker \
  --mlflow-uri https://mlflow.westus.cloudapp.azure.com:5000 \
  --model-name yolov8-detector \
  --registry myregistry.azurecr.io \
  --image-tag 1.0.0
```

### Docker Environment Variables

The container is started with these environment variables:

```bash
MLFLOW_TRACKING_URI=<mlflow-uri>
MODEL_NAME=<model-name>
MODEL_STAGE=Production
```

These are read by `realtime_inference_service.py` on startup.

## Kubernetes Deployment

### How It Works

1. **Validate Model**: Check Production model exists in MLflow
2. **Build Image**: Run `docker build` with latest code
3. **Push Image**: Push to registry
4. **Check Deployment**: Verify deployment exists in cluster
5. **Patch Deployment**: Update image reference
6. **Update Env Vars**: Set MLFLOW_TRACKING_URI, MODEL_NAME, MODEL_STAGE
7. **Wait for Rollout**: Monitor deployment rollout
8. **Rollback on Failure**: Auto-rollback if rollout fails

### Example: Deploy to Kubernetes

```bash
python scripts/deploy_production_model.py \
  --deployment k8s \
  --mlflow-uri http://mlflow.default.svc.cluster.local:5000 \
  --model-name yolov8-detector \
  --service-name inference-api \
  --namespace production \
  --registry myregistry.azurecr.io
```

### Example: Deploy to AKS

```powershell
.\scripts\deploy-production-model.ps1 `
  -Deployment k8s `
  -MlflowUri "http://mlflow-service:5000" `
  -ModelName "yolov8-detector" `
  -ServiceName "inference-api" `
  -Namespace "production" `
  -Registry "myregistry.azurecr.io"
```

### Kubernetes Requirements

The deployment must already exist:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference-api
  namespace: production
spec:
  replicas: 2
  selector:
    matchLabels:
      app: inference-api
  template:
    metadata:
      labels:
        app: inference-api
    spec:
      containers:
      - name: inference-api
        image: myregistry.azurecr.io/inference-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: MLFLOW_TRACKING_URI
          value: "http://mlflow-service:5000"
        - name: MODEL_NAME
          value: "yolov8-detector"
        - name: MODEL_STAGE
          value: "Production"
```

The script will update the image and environment variables.

## Configuration

### Environment Variables

Scripts read these environment variables by default:

```bash
MLFLOW_TRACKING_URI    # MLflow tracking server URL
MODEL_NAME             # MLflow model name
```

Override with command-line arguments.

### Configuration File (Optional)

Create `.deployment.env`:

```bash
MLFLOW_TRACKING_URI=http://127.0.0.1:5000
MODEL_NAME=simple-cnn-demo
REGISTRY=myregistry.azurecr.io
NAMESPACE=production
```

Load with:

```bash
source .deployment.env
python scripts/deploy_production_model.py --deployment docker
```

## Troubleshooting

### "Model validation failed"

**Cause**: Production model doesn't exist in MLflow

**Solution**:
```bash
# Check available models
python -c "
import mlflow
mlflow.set_tracking_uri('http://127.0.0.1:5000')
client = mlflow.tracking.MlflowClient()
for reg_model in client.search_registered_models():
    print(f'Model: {reg_model.name}')
    for version in client.get_latest_versions(reg_model.name):
        print(f'  v{version.version}: {version.current_stage}')
"
```

### "Docker build failed"

**Cause**: Invalid Dockerfile or missing dependencies

**Solution**:
```bash
# Test build directly
docker build -t test:latest .

# Check Dockerfile exists
ls -la Dockerfile
```

### "Container health check failed"

**Cause**: Container not responding to health endpoint

**Solution**:
```bash
# Check container logs
docker logs inference-service

# Test health endpoint manually
docker exec inference-service curl http://localhost:8000/health

# Verify FastAPI is running
docker exec inference-service ps aux | grep uvicorn
```

### "Deployment not found" (Kubernetes)

**Cause**: Deployment doesn't exist in cluster

**Solution**:
```bash
# Check existing deployments
kubectl get deployments -n production

# Create deployment first
kubectl apply -f k8s/deployment.yaml

# Then run deploy script
```

### "Rollout failed" (Kubernetes)

**Cause**: Pod didn't become ready within timeout

**Solution**:
```bash
# Check pod status
kubectl get pods -n production

# Check pod logs
kubectl logs -n production deployment/inference-api

# Increase timeout
python scripts/deploy_production_model.py --deployment k8s --timeout 600

# Manually rollback if needed
kubectl rollout undo deployment/inference-api -n production
```

### "Permission denied" (Bash script)

**Cause**: Script not executable

**Solution**:
```bash
chmod +x scripts/deploy-production-model.sh
./scripts/deploy-production-model.sh docker
```

## Examples

### Example 1: Continuous Deployment

Deploy when new model is promoted to Production:

```bash
#!/bin/bash
# ci-cd-deploy.sh

set -e

# Configure
export MLFLOW_TRACKING_URI="http://mlflow.example.com:5000"
export MODEL_NAME="yolov8-detector"
export REGISTRY="myregistry.azurecr.io"

# Deploy
python scripts/deploy_production_model.py \
  --deployment k8s \
  --namespace production

# Verify
kubectl rollout status deployment/inference-service -n production

echo "✓ Deployment successful"
```

### Example 2: Blue-Green Deployment

Deploy to blue environment, then switch traffic:

```bash
#!/bin/bash
# blue-green-deploy.sh

# Deploy to blue
python scripts/deploy_production_model.py \
  --deployment k8s \
  --service-name inference-blue \
  --namespace production

# Run tests
./run-tests.sh http://inference-blue:8000

# Switch traffic
kubectl patch service inference-router -p '{"spec":{"selector":{"deployment":"blue"}}}'

echo "✓ Blue-green deployment complete"
```

### Example 3: Rolling Deployment with Health Checks

```bash
#!/bin/bash
# rolling-deploy.sh

# First replica
kubectl scale deployment inference-api --replicas=3 -n production

# Deploy
python scripts/deploy_production_model.py \
  --deployment k8s \
  --namespace production \
  --timeout 600

# Verify health
for i in {1..10}; do
  healthy=$(kubectl get pods -n production -l app=inference-api \
    -o jsonpath='{.items[].status.conditions[?(@.type=="Ready")].status}' \
    | grep -o True | wc -l)
  
  if [[ $healthy -eq 3 ]]; then
    echo "✓ All replicas healthy"
    exit 0
  fi
  
  echo "Waiting... ($i/10)"
  sleep 10
done

echo "✗ Replicas not healthy"
exit 1
```

### Example 4: PowerShell CI/CD

```powershell
# PowerShell CI/CD Pipeline
$ErrorActionPreference = "Stop"

Write-Host "Deploying Production Model..."

# Set environment
$env:MLFLOW_TRACKING_URI = "http://mlflow.example.com:5000"
$env:MODEL_NAME = "yolov8-detector"

# Deploy
& .\scripts\deploy-production-model.ps1 `
  -Deployment k8s `
  -Namespace production `
  -Registry "myregistry.azurecr.io"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Deployment successful" -ForegroundColor Green
    
    # Run smoke tests
    & .\tests\smoke-tests.ps1
} else {
    Write-Host "✗ Deployment failed" -ForegroundColor Red
    exit 1
}
```

## Integration with CI/CD

### GitHub Actions

```yaml
name: Deploy Production Model

on:
  workflow_dispatch:
    inputs:
      model_name:
        description: 'Model to deploy'
        required: true
      deployment:
        description: 'Target (docker or k8s)'
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install mlflow pyyaml
      
      - name: Deploy model
        run: |
          python scripts/deploy_production_model.py \
            --deployment ${{ github.event.inputs.deployment }} \
            --model-name ${{ github.event.inputs.model_name }} \
            --mlflow-uri ${{ secrets.MLFLOW_URI }}
```

### Azure DevOps

```yaml
trigger:
  - main

jobs:
- job: DeployProductionModel
  pool:
    vmImage: 'ubuntu-latest'
  
  steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: '3.10'
  
  - script: |
      pip install mlflow pyyaml
    displayName: 'Install dependencies'
  
  - script: |
      python scripts/deploy_production_model.py \
        --deployment k8s \
        --mlflow-uri $(MLFLOW_URI) \
        --namespace production
    displayName: 'Deploy to Kubernetes'
    env:
      MLFLOW_TRACKING_URI: $(MLFLOW_URI)
      MODEL_NAME: $(MODEL_NAME)
```

## Performance Metrics

Typical deployment times:

| Operation | Duration |
|-----------|----------|
| Model validation | 2-3 seconds |
| Docker build | 30-60 seconds |
| Docker push | 10-30 seconds |
| Docker start | 5-10 seconds |
| Docker health check | 3-15 seconds |
| **Total (Docker)** | **50-115 seconds** |
| K8s patch | 2-3 seconds |
| K8s rollout (1 replica) | 30-60 seconds |
| K8s rollout (3 replicas) | 60-120 seconds |
| **Total (K8s single)** | **32-63 seconds** |
| **Total (K8s multi)** | **62-123 seconds** |

## Security Considerations

1. **MLflow Access**: Ensure MLflow is only accessible from authorized networks
2. **Registry Credentials**: Configure Docker credentials securely
3. **Kubernetes RBAC**: Ensure deployment account has minimal required permissions
4. **Model Validation**: Scripts verify Production stage before deployment
5. **Rollback Safety**: Automatic rollback prevents broken deployments
6. **Audit Logging**: All deployments logged for compliance

## Support

For issues or questions:

1. Check troubleshooting section above
2. Review logs from script output
3. Test manually with MLflow CLI
4. Verify container/deployment health directly

---

**Status**: Production Ready  
**Last Updated**: January 28, 2026
