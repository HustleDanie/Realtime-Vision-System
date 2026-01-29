# Azure Container Registry & AKS Deployment Guide

## Overview

This guide explains how to build Docker images, push them to Azure Container Registry (ACR), and deploy them to Azure Kubernetes Service (AKS).

## Architecture

```
┌──────────────────────────────────────┐
│   Local Development Machine          │
│  (Docker Desktop / Docker Engine)    │
│   - docker build                     │
│   - docker tag                       │
│   - docker push                      │
└──────────────┬──────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│   Azure Container Registry (ACR)     │
│   (realtime-vision.azurecr.io)       │
│   - YOLO:latest                      │
│   - logging:latest                   │
│   - mlflow:latest                    │
│   - camera:latest                    │
│   - preprocessing:latest             │
└──────────────┬──────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│   Azure Kubernetes Service (AKS)     │
│   - Pod pulls from ACR               │
│   - kubectl apply -f deployment.yaml │
│   - Services expose endpoints        │
└──────────────────────────────────────┘
```

## Prerequisites

### Azure Setup

1. **Create Azure Resource Group:**
   ```bash
   az group create --name vision-rg --location eastus
   ```

2. **Create Azure Container Registry:**
   ```bash
   az acr create --resource-group vision-rg \
     --name realtime-vision \
     --sku Basic
   ```

3. **Create Azure Kubernetes Service:**
   ```bash
   az aks create --resource-group vision-rg \
     --name vision-aks \
     --node-count 3 \
     --enable-managed-identity \
     --vm-set-type VirtualMachineScaleSets \
     --load-balancer-sku standard \
     --enable-addons monitoring \
     --workspace-resource-id <log-analytics-workspace-id>
   ```

4. **Attach ACR to AKS:**
   ```bash
   az aks update -n vision-aks \
     --resource-group vision-rg \
     --attach-acr realtime-vision
   ```

5. **Get AKS Credentials:**
   ```bash
   az aks get-credentials --resource-group vision-rg --name vision-aks
   ```

### Local Tools

```bash
# Install Azure CLI
# Windows: choco install azure-cli
# macOS: brew install azure-cli
# Linux: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Install kubectl
az aks install-cli

# Install Docker Desktop
# https://www.docker.com/products/docker-desktop

# Verify installation
az --version
kubectl version --client
docker --version
```

## Build Docker Images

### 1. Build YOLO Inference Image

```bash
# From project root directory
docker build \
  --file docker/Dockerfile.yolo \
  --tag yolo-inference:latest \
  .

# Verify image
docker images | grep yolo-inference
```

### 2. Build Logging Service Image

```bash
docker build \
  --file docker/Dockerfile.logging \
  --tag logging-service:latest \
  .
```

### 3. Build MLflow Image

```bash
docker build \
  --file docker/Dockerfile.mlflow \
  --tag mlflow-server:latest \
  .
```

### 4. Build Camera Service Image

```bash
docker build \
  --file docker/Dockerfile.camera \
  --tag camera-stream:latest \
  .
```

### 5. Build Preprocessing Service Image

```bash
docker build \
  --file docker/Dockerfile.preprocessing \
  --tag preprocessing-service:latest \
  .
```

### Build All Images (Script)

**build-all.sh (Linux/Mac):**
```bash
#!/bin/bash

SERVICES=("yolo-inference" "logging-service" "mlflow-server" "camera-stream" "preprocessing-service")
DOCKERFILES=(
  "docker/Dockerfile.yolo"
  "docker/Dockerfile.logging"
  "docker/Dockerfile.mlflow"
  "docker/Dockerfile.camera"
  "docker/Dockerfile.preprocessing"
)

for i in "${!SERVICES[@]}"; do
  echo "Building ${SERVICES[$i]}..."
  docker build --file ${DOCKERFILES[$i]} --tag ${SERVICES[$i]}:latest .
  if [ $? -eq 0 ]; then
    echo "✓ ${SERVICES[$i]} built successfully"
  else
    echo "✗ Failed to build ${SERVICES[$i]}"
    exit 1
  fi
done

echo "All images built successfully!"
docker images | grep -E "(yolo|logging|mlflow|camera|preprocessing)"
```

**build-all.ps1 (Windows PowerShell):**
```powershell
$SERVICES = @(
    @{ Name = "yolo-inference"; Dockerfile = "docker/Dockerfile.yolo" },
    @{ Name = "logging-service"; Dockerfile = "docker/Dockerfile.logging" },
    @{ Name = "mlflow-server"; Dockerfile = "docker/Dockerfile.mlflow" },
    @{ Name = "camera-stream"; Dockerfile = "docker/Dockerfile.camera" },
    @{ Name = "preprocessing-service"; Dockerfile = "docker/Dockerfile.preprocessing" }
)

foreach ($service in $SERVICES) {
    Write-Host "Building $($service.Name)..." -ForegroundColor Green
    docker build --file $service.Dockerfile --tag "$($service.Name):latest" .
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ $($service.Name) built successfully" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to build $($service.Name)" -ForegroundColor Red
        exit 1
    }
}

Write-Host "All images built successfully!" -ForegroundColor Green
docker images | Select-String -Pattern "yolo|logging|mlflow|camera|preprocessing"
```

## Push to Azure Container Registry

### 1. Login to ACR

```bash
# Method 1: Using Azure CLI
az acr login --name realtime-vision

# Method 2: Using Docker with service principal (CI/CD)
# az acr credential show --resource-group vision-rg --name realtime-vision
# docker login realtime-vision.azurecr.io -u <username> -p <password>
```

### 2. Tag Images for ACR

ACR images must follow format: `<registry>.azurecr.io/<image>:<tag>`

```bash
# Get ACR login server
ACR_REGISTRY=$(az acr show --resource-group vision-rg --name realtime-vision --query loginServer -o tsv)
echo "ACR Registry: $ACR_REGISTRY"

# Tag images
docker tag yolo-inference:latest $ACR_REGISTRY/yolo-inference:latest
docker tag yolo-inference:latest $ACR_REGISTRY/yolo-inference:v1.0
docker tag logging-service:latest $ACR_REGISTRY/logging-service:latest
docker tag mlflow-server:latest $ACR_REGISTRY/mlflow-server:latest
docker tag camera-stream:latest $ACR_REGISTRY/camera-stream:latest
docker tag preprocessing-service:latest $ACR_REGISTRY/preprocessing-service:latest

# Verify tags
docker images | grep $ACR_REGISTRY
```

### 3. Push Images to ACR

```bash
# Push individual images
docker push $ACR_REGISTRY/yolo-inference:latest
docker push $ACR_REGISTRY/yolo-inference:v1.0
docker push $ACR_REGISTRY/logging-service:latest
docker push $ACR_REGISTRY/mlflow-server:latest
docker push $ACR_REGISTRY/camera-stream:latest
docker push $ACR_REGISTRY/preprocessing-service:latest

# Verify in ACR
az acr repository list --resource-group vision-rg --name realtime-vision
az acr repository show-tags --resource-group vision-rg --name realtime-vision --repository yolo-inference
```

### Push All Images (Script)

**push-to-acr.sh (Linux/Mac):**
```bash
#!/bin/bash

REGISTRY="${1:-}"

if [ -z "$REGISTRY" ]; then
    REGISTRY=$(az acr show --resource-group vision-rg --name realtime-vision --query loginServer -o tsv)
    if [ $? -ne 0 ]; then
        echo "ERROR: Could not get ACR login server. Ensure Azure CLI is configured."
        exit 1
    fi
fi

echo "Pushing to ACR: $REGISTRY"
echo ""

IMAGES=(
    "yolo-inference:latest"
    "yolo-inference:v1.0"
    "logging-service:latest"
    "mlflow-server:latest"
    "camera-stream:latest"
    "preprocessing-service:latest"
)

# Login to ACR
echo "Logging in to ACR..."
az acr login --name realtime-vision

# Push images
for image in "${IMAGES[@]}"; do
    echo "Pushing $image..."
    docker push $REGISTRY/$image
    if [ $? -eq 0 ]; then
        echo "✓ Pushed $image"
    else
        echo "✗ Failed to push $image"
        exit 1
    fi
done

echo ""
echo "All images pushed successfully!"
echo ""
echo "Repositories in ACR:"
az acr repository list --resource-group vision-rg --name realtime-vision
```

**push-to-acr.ps1 (Windows PowerShell):**
```powershell
param(
    [string]$Registry = ""
)

if ([string]::IsNullOrEmpty($Registry)) {
    Write-Host "Getting ACR login server..." -ForegroundColor Yellow
    $Registry = az acr show --resource-group vision-rg --name realtime-vision --query loginServer -o tsv
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Could not get ACR login server." -ForegroundColor Red
        exit 1
    }
}

Write-Host "Pushing to ACR: $Registry" -ForegroundColor Cyan
Write-Host ""

$IMAGES = @(
    "yolo-inference:latest",
    "yolo-inference:v1.0",
    "logging-service:latest",
    "mlflow-server:latest",
    "camera-stream:latest",
    "preprocessing-service:latest"
)

# Login to ACR
Write-Host "Logging in to ACR..." -ForegroundColor Yellow
az acr login --name realtime-vision

# Push images
foreach ($image in $IMAGES) {
    Write-Host "Pushing $image..." -ForegroundColor Green
    docker push "$Registry/$image"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Pushed $image" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to push $image" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "All images pushed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Repositories in ACR:" -ForegroundColor Yellow
az acr repository list --resource-group vision-rg --name realtime-vision
```

## Update Kubernetes Manifests

Replace image references in `k8s/deployments.yaml`:

### Before:
```yaml
containers:
  - name: yolo
    image: realtime-vision-system:yolo-latest
```

### After:
```yaml
containers:
  - name: yolo
    image: realtime-vision.azurecr.io/yolo-inference:latest
    imagePullPolicy: Always
```

**Script to update all manifests:**

```bash
#!/bin/bash

ACR_REGISTRY="realtime-vision.azurecr.io"

# Update deployments.yaml
sed -i "s|image: realtime-vision-system:yolo-latest|image: $ACR_REGISTRY/yolo-inference:latest|g" k8s/deployments.yaml
sed -i "s|image: realtime-vision-system:logging-latest|image: $ACR_REGISTRY/logging-service:latest|g" k8s/deployments.yaml

# Verify changes
grep "image:" k8s/deployments.yaml
```

## Deploy to AKS

### 1. Verify AKS Connection

```bash
# Check cluster info
kubectl cluster-info
kubectl get nodes

# Verify ACR integration
kubectl get secrets -n vision-system | grep acr-auth
```

### 2. Deploy Kubernetes Manifests

```bash
# Apply manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmaps.yaml
kubectl apply -f k8s/persistent-volumes.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/deployments.yaml
kubectl apply -f k8s/services.yaml
kubectl apply -f k8s/autoscaling.yaml

# Verify deployment
kubectl get pods -n vision-system
kubectl get svc -n vision-system
```

### 3. Monitor Deployment

```bash
# Check pod status
kubectl get pods -n vision-system -w

# Check logs
kubectl logs -n vision-system -l app=yolo -f

# Troubleshoot image pull errors
kubectl describe pod <pod-name> -n vision-system
```

## Azure DevOps Pipeline (CI/CD)

**azure-pipelines.yml:**

```yaml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

variables:
  dockerRegistryServiceConnection: 'vision-acr'
  imageRepository: 'yolo-inference'
  containerRegistry: 'realtime-vision.azurecr.io'
  dockerfilePath: '$(Build.SourcesDirectory)/docker/Dockerfile.yolo'
  tag: '$(Build.BuildId)'

stages:
  - stage: Build
    displayName: Build and Push to ACR
    jobs:
      - job: Build
        displayName: Build Docker Image
        steps:
          - task: Docker@2
            displayName: Build image
            inputs:
              command: build
              repository: $(imageRepository)
              dockerfile: $(dockerfilePath)
              containerRegistry: $(dockerRegistryServiceConnection)
              tags: |
                $(tag)
                latest

          - task: Docker@2
            displayName: Push image to ACR
            inputs:
              command: push
              repository: $(imageRepository)
              containerRegistry: $(dockerRegistryServiceConnection)
              tags: |
                $(tag)
                latest

  - stage: Deploy
    displayName: Deploy to AKS
    dependsOn: Build
    jobs:
      - job: Deploy
        displayName: Deploy to AKS
        steps:
          - task: KubernetesManifest@0
            displayName: Deploy to Kubernetes
            inputs:
              action: 'deploy'
              kubernetesServiceConnection: 'vision-aks'
              namespace: 'vision-system'
              manifests: |
                $(Pipeline.Workspace)/k8s/deployments.yaml
              containers: |
                $(containerRegistry)/$(imageRepository):$(tag)
```

## GitHub Actions Workflow

**.github/workflows/build-and-deploy.yml:**

```yaml
name: Build and Deploy to AKS

on:
  push:
    branches: [main]
    paths:
      - 'docker/**'
      - 'src/**'
      - 'k8s/**'
      - '.github/workflows/build-and-deploy.yml'

env:
  REGISTRY: realtime-vision.azurecr.io
  IMAGE_NAME: yolo-inference

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Azure Login
        uses: azure/login@v1
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Login to ACR
        run: |
          az acr login --name realtime-vision

      - name: Build Docker image
        run: |
          docker build \
            --file docker/Dockerfile.yolo \
            --tag $REGISTRY/$IMAGE_NAME:${{ github.sha }} \
            --tag $REGISTRY/$IMAGE_NAME:latest \
            .

      - name: Push to ACR
        run: |
          docker push $REGISTRY/$IMAGE_NAME:${{ github.sha }}
          docker push $REGISTRY/$IMAGE_NAME:latest

      - name: Set kubeconfig
        run: |
          az aks get-credentials \
            --resource-group vision-rg \
            --name vision-aks \
            --file $KUBECONFIG

      - name: Deploy to AKS
        run: |
          kubectl set image deployment/yolo-inference \
            yolo=$REGISTRY/$IMAGE_NAME:${{ github.sha }} \
            -n vision-system

      - name: Verify deployment
        run: |
          kubectl rollout status deployment/yolo-inference -n vision-system --timeout=5m
```

## Image Management

### List Images in ACR

```bash
# List all repositories
az acr repository list --resource-group vision-rg --name realtime-vision

# List tags for a repository
az acr repository show-tags \
  --resource-group vision-rg \
  --name realtime-vision \
  --repository yolo-inference

# Show image details
az acr repository show \
  --resource-group vision-rg \
  --name realtime-vision \
  --repository yolo-inference
```

### Clean Up Old Images

```bash
# Delete a specific tag
az acr repository delete \
  --resource-group vision-rg \
  --name realtime-vision \
  --image yolo-inference:old-tag

# Delete all untagged images
az acr purge \
  --resource-group vision-rg \
  --name realtime-vision \
  --filter ".*:.*" \
  --keep 10 \
  --ago 7d \
  --untagged
```

### Image Scanning & Security

```bash
# Enable ACR image scanning
az acr config content-trust update \
  --resource-group vision-rg \
  --registry-name realtime-vision \
  --status Enabled

# Scan an image for vulnerabilities
az acr scan \
  --resource-group vision-rg \
  --registry-name realtime-vision \
  --image yolo-inference:latest

# View scan results
az acr task logs \
  --resource-group vision-rg \
  --registry-name realtime-vision \
  --image yolo-inference:latest
```

## Troubleshooting

### Image Pull Errors

```bash
# Check pod events
kubectl describe pod yolo-inference-xxx -n vision-system

# Common issue: ImagePullBackOff
# Solution: Verify ACR login credentials
kubectl get secrets -n vision-system

# Re-authenticate
az aks update -n vision-aks \
  --resource-group vision-rg \
  --attach-acr realtime-vision
```

### Check Image Availability

```bash
# Verify image exists in ACR
az acr repository show \
  --resource-group vision-rg \
  --name realtime-vision \
  --repository yolo-inference

# Check image size
az acr repository show-manifests \
  --resource-group vision-rg \
  --name realtime-vision \
  --repository yolo-inference
```

### Debug AKS Deployment

```bash
# Check node status
kubectl get nodes -o wide

# Check pod logs
kubectl logs yolo-inference-xxx -n vision-system --previous

# Check events
kubectl get events -n vision-system --sort-by='.lastTimestamp'

# SSH into node (if needed)
# Note: Requires SSH key setup in AKS
kubectl debug node/aks-nodepool1-12345678-vmss000000 -it --image=ubuntu
```

## Production Checklist

- [ ] ACR created and configured
- [ ] AKS cluster created with ACR integration
- [ ] Docker images build successfully locally
- [ ] Images tagged correctly for ACR
- [ ] Images pushed to ACR without errors
- [ ] Kubernetes manifests updated with ACR image URLs
- [ ] Image pull policies set to `Always` or `IfNotPresent`
- [ ] AKS credentials configured locally
- [ ] Deployments apply without errors
- [ ] Pods reach `Running` state
- [ ] Services expose correctly
- [ ] HPA metrics available
- [ ] Monitoring configured
- [ ] Network policies applied
- [ ] Logging configured
- [ ] Backup strategy in place

## Cost Optimization

```bash
# Use Basic ACR (cheaper, single instance)
az acr create --sku Basic ...

# Use spot VMs for AKS nodes (80% cheaper)
az aks update --enable-cluster-autoscaler --min-count 1 --max-count 5 ...

# Enable ACR image pruning to save storage
az acr purge --keep 5 --ago 7d

# Monitor costs
az consumption usage list --query "[].{Name:name, Quantity:quantity, Unit:unit, Cost:cost}"
```

## Security Best Practices

1. **Enable ACR authentication:**
   ```bash
   az acr update --name realtime-vision --admin-enabled false
   ```

2. **Use managed identities:**
   ```bash
   az aks update -n vision-aks -g vision-rg --enable-managed-identity
   ```

3. **Enable network rules:**
   ```bash
   az acr network-rule add --name realtime-vision --action Allow --ip-address <your-ip>
   ```

4. **Scan images for vulnerabilities:**
   ```bash
   az acr scan --name realtime-vision --image yolo-inference:latest
   ```

5. **Use image signing:**
   ```bash
   az acr config content-trust update --registry realtime-vision --status Enabled
   ```
