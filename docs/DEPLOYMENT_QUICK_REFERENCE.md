# Deployment Scripts: Quick Command Reference

Quick lookup for common deployment commands.

## Status: Production Ready ✅

## File Locations

```
scripts/
├── deploy_production_model.py      # Python (recommended)
├── deploy-production-model.ps1     # PowerShell
└── deploy-production-model.sh      # Bash

docs/
└── DEPLOYMENT_SCRIPTS_README.md    # Full documentation
```

## Quick Commands

### Docker - Deploy Latest Production Model

```bash
# Python (Linux/Mac/Windows)
python scripts/deploy_production_model.py --deployment docker

# PowerShell (Windows)
.\scripts\deploy-production-model.ps1 -Deployment docker

# Bash (Linux/Mac)
./scripts/deploy-production-model.sh docker
```

### Kubernetes - Deploy Latest Production Model

```bash
# Python (to production namespace)
python scripts/deploy_production_model.py --deployment k8s --namespace production

# PowerShell
.\scripts\deploy-production-model.ps1 -Deployment k8s -Namespace production

# Bash
./scripts/deploy-production-model.sh k8s --namespace production
```

## Common Tasks

### Dry Run (Test without changes)

```bash
# Python
python scripts/deploy_production_model.py --deployment docker --dry-run

# PowerShell
.\scripts\deploy-production-model.ps1 -Deployment docker -DryRun

# Bash
./scripts/deploy-production-model.sh docker --dry-run
```

### Deploy Specific Model

```bash
# Python
python scripts/deploy_production_model.py --deployment docker --model-name yolov8

# PowerShell
.\scripts\deploy-production-model.ps1 -Deployment docker -ModelName yolov8

# Bash
./scripts/deploy-production-model.sh docker --model-name yolov8
```

### Custom MLflow Server

```bash
# Python
python scripts/deploy_production_model.py --deployment docker \
  --mlflow-uri http://mlflow.example.com:5000

# PowerShell
.\scripts\deploy-production-model.ps1 -Deployment docker `
  -MlflowUri "http://mlflow.example.com:5000"

# Bash
./scripts/deploy-production-model.sh docker \
  --mlflow-uri http://mlflow.example.com:5000
```

### Custom Registry

```bash
# Python (Azure)
python scripts/deploy_production_model.py --deployment docker \
  --registry myregistry.azurecr.io

# PowerShell
.\scripts\deploy-production-model.ps1 -Deployment docker `
  -Registry "myregistry.azurecr.io"

# Bash
./scripts/deploy-production-model.sh docker \
  --registry myregistry.azurecr.io
```

### Custom Service Name

```bash
# Python
python scripts/deploy_production_model.py --deployment docker \
  --service-name my-inference-api

# PowerShell
.\scripts\deploy-production-model.ps1 -Deployment docker `
  -ServiceName "my-inference-api"

# Bash
./scripts/deploy-production-model.sh docker \
  --service-name my-inference-api
```

### Skip Docker Build (Use Existing Image)

```bash
# Python
python scripts/deploy_production_model.py --deployment k8s --skip-build

# PowerShell
.\scripts\deploy-production-model.ps1 -Deployment k8s -SkipBuild

# Bash
./scripts/deploy-production-model.sh k8s --skip-build
```

### Extended Timeout (for slow networks)

```bash
# Python (10 minutes)
python scripts/deploy_production_model.py --deployment k8s --timeout 600

# PowerShell
.\scripts\deploy-production-model.ps1 -Deployment k8s -Timeout 600

# Bash
./scripts/deploy-production-model.sh k8s --timeout 600
```

### No Automatic Rollback

```bash
# Python
python scripts/deploy_production_model.py --deployment k8s --no-rollback

# PowerShell
.\scripts\deploy-production-model.ps1 -Deployment k8s -NoRollback

# Bash
./scripts/deploy-production-model.sh k8s --no-rollback
```

## Combined Examples

### Deploy to Azure Registry in AKS

```bash
python scripts/deploy_production_model.py \
  --deployment k8s \
  --namespace production \
  --registry myregistry.azurecr.io \
  --model-name yolov8-detector \
  --mlflow-uri https://mlflow.westus.cloudapp.azure.com:5000
```

### Deploy Multiple Models (Script)

```bash
#!/bin/bash
# deploy-all-models.sh

models=("model-1" "model-2" "model-3")

for model in "${models[@]}"; do
  echo "Deploying $model..."
  python scripts/deploy_production_model.py \
    --deployment docker \
    --model-name "$model" \
    --registry myregistry.azurecr.io
done
```

### Deploy with Health Verification

```bash
#!/bin/bash
# deploy-and-verify.sh

# Deploy
python scripts/deploy_production_model.py --deployment docker

# Verify health
sleep 5
curl -f http://localhost:8000/health && echo "✓ Healthy" || echo "✗ Failed"
```

## Troubleshooting Commands

### Check Model Status

```bash
# See available models
python -c "
import mlflow
mlflow.set_tracking_uri('http://127.0.0.1:5000')
client = mlflow.tracking.MlflowClient()
for model in client.search_registered_models():
    for v in client.get_latest_versions(model.name):
        print(f'{model.name:20} v{v.version:3} {v.current_stage}')
"
```

### Check Docker Container

```bash
# Running containers
docker ps | grep inference

# Container logs
docker logs inference-service

# Health check
docker exec inference-service curl http://localhost:8000/health

# Stop container
docker stop inference-service
```

### Check Kubernetes Deployment

```bash
# Deployment status
kubectl get deployments -n production

# Pod status
kubectl get pods -n production

# Pod logs
kubectl logs -n production deployment/inference-service

# Rollout history
kubectl rollout history deployment/inference-service -n production

# Rollback
kubectl rollout undo deployment/inference-service -n production
```

## Environment Variables

Set these for automatic defaults:

```bash
export MLFLOW_TRACKING_URI="http://127.0.0.1:5000"
export MODEL_NAME="simple-cnn-demo"
export REGISTRY="localhost"
```

Then use shorter commands:

```bash
python scripts/deploy_production_model.py --deployment docker
```

## Help Commands

### Python

```bash
python scripts/deploy_production_model.py --help
```

### PowerShell

```powershell
Get-Help .\scripts\deploy-production-model.ps1 -Full
```

### Bash

```bash
./scripts/deploy-production-model.sh --help
```

## Output Examples

### Successful Docker Deployment

```
==================== DEPLOYMENT CONFIGURATION ====================
Deployment Type: docker
MLflow URI: http://127.0.0.1:5000
Model Name: simple-cnn-demo
Model Stage: Production
Service Name: inference-service
Registry: localhost
Image Tag: latest
Dry Run: False
===================================================================

[INFO] Validating MLflow model...
[✓] MLflow model validation passed
[✓] Model found: models:/simple-cnn-demo/Production
  Version: 3
  Status: READY

[INFO] ================================
[INFO] DOCKER DEPLOYMENT
[INFO] ================================
[INFO] Building Docker image...
[✓] Docker image built: localhost/inference-service:latest
[INFO] Stopping container...
[✓] Container stopped
[INFO] Starting new container...
[✓] Container started
[INFO] Waiting for container health check...
[✓] Container is healthy

==================================================
✓ DEPLOYMENT SUCCESSFUL
==================================================
Model: simple-cnn-demo
Stage: Production
Deployment: docker
```

### Successful Kubernetes Deployment

```
==================== DEPLOYMENT CONFIGURATION ====================
Deployment Type: k8s
Namespace: production
Deployment: inference-service
Image: myregistry.azurecr.io/inference-service:latest
===================================================================

[INFO] Validating MLflow model...
[✓] Model found: models:/simple-cnn-demo/Production
  Version: 3

[INFO] KUBERNETES DEPLOYMENT
[INFO] Building Docker image...
[✓] Image built: myregistry.azurecr.io/inference-service:latest
[INFO] Pushing image to registry...
[✓] Image pushed: myregistry.azurecr.io/inference-service:latest
[INFO] Patching Kubernetes deployment...
[✓] Deployment patched
[INFO] Waiting for rollout to complete...
[✓] Rollout completed successfully

==================================================
✓ DEPLOYMENT SUCCESSFUL
==================================================
Model: simple-cnn-demo
Stage: Production
Deployment: k8s
```

## Common Errors & Solutions

### "Model validation failed"
→ Check MLflow is running: `python -c "import mlflow; print(mlflow.get_tracking_uri())"`

### "Docker build failed"
→ Check Dockerfile exists: `ls -la Dockerfile`

### "Container health check failed"
→ Check logs: `docker logs inference-service`

### "Deployment not found"
→ Create first: `kubectl apply -f k8s/deployment.yaml`

### "Rollout failed"
→ Increase timeout: `--timeout 600`

### "Permission denied" (Bash)
→ Make executable: `chmod +x scripts/deploy-production-model.sh`

## Script Comparison

| Feature | Python | PowerShell | Bash |
|---------|--------|-----------|------|
| **Docker** | ✅ | ✅ | ✅ |
| **Kubernetes** | ✅ | ✅ | ✅ |
| **Dry Run** | ✅ | ✅ | ✅ |
| **Health Check** | ✅ | ✅ | ✅ |
| **Auto Rollback** | ✅ | ✅ | ✅ |
| **Logging** | Detailed | Interactive | Colored |
| **Error Handling** | Comprehensive | Good | Good |
| **Windows Native** | ✅* | ✅ | ⚠️** |
| **Linux/Mac** | ✅ | ⚠️* | ✅ |

*PowerShell Core available for Linux/Mac  
**Git Bash or WSL recommended on Windows

## CI/CD Integration

### GitHub Actions
```yaml
- run: python scripts/deploy_production_model.py --deployment k8s
  env:
    MLFLOW_TRACKING_URI: ${{ secrets.MLFLOW_URI }}
```

### Azure DevOps
```yaml
- script: python scripts/deploy_production_model.py --deployment k8s
  env:
    MLFLOW_TRACKING_URI: $(MLFLOW_URI)
```

### GitLab CI
```yaml
deploy:
  script:
    - python scripts/deploy_production_model.py --deployment k8s
```

## Performance Metrics

- **Model validation**: 2-3 seconds
- **Docker build**: 30-60 seconds
- **Docker push**: 10-30 seconds
- **Docker start + health**: 10-20 seconds
- **K8s rollout (1 replica)**: 30-60 seconds
- **K8s rollout (3 replicas)**: 60-120 seconds

**Total deployment time: 50-120 seconds** (typical)

## Next Steps

1. ✅ Review [Full Documentation](DEPLOYMENT_SCRIPTS_README.md)
2. ✅ Run dry-run first: `--dry-run`
3. ✅ Deploy to test environment
4. ✅ Verify with health checks
5. ✅ Integrate into CI/CD

---

**Status**: Production Ready ✅  
**Last Updated**: January 28, 2026  
**Supported**: Python 3.8+, PowerShell 5.1+, Bash 4.0+
