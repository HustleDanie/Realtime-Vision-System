# CI/CD Workflow Guide: Model Promotion to Production

Complete guide for setting up automated CI/CD workflows that deploy models when promoted to Production in MLflow.

## Overview

This guide covers:
- **GitHub Actions** workflow for automated deployment on model promotion
- **Azure DevOps** pipeline as an alternative
- **MLflow Webhook Handler** for triggering deployments
- **Kubernetes manifests** with health checks and auto-scaling
- **Setup, configuration, and troubleshooting**

## Architecture

```
┌─────────────────┐
│  MLflow Registry│
│   (Production)  │
└────────┬────────┘
         │ Model Promotion Event
         │
    ┌────▼────────────────┐
    │ Webhook Handler     │
    │ (Flask Service)     │
    └────┬────────────────┘
         │ Trigger Deployment
         │
    ┌────▼──────────────────┐
    │ CI/CD Platform        │
    │ (GitHub Actions / ADO) │
    └────┬──────────────────┘
         │ 1. Validate Model
         │ 2. Build Docker Image
         │ 3. Push to ACR
         │ 4. Deploy to AKS
         │ 5. Health Check
         │ 6. Rollback (on failure)
         │
    ┌────▼──────────────────┐
    │ AKS Cluster           │
    │ (Production)          │
    └───────────────────────┘
```

## Prerequisites

### Required Services
- **MLflow Tracking Server** (accessible from your CI/CD platform)
- **Azure Container Registry (ACR)** for storing Docker images
- **Azure Kubernetes Service (AKS)** cluster (v1.20+)
- **GitHub** repository (for GitHub Actions) OR **Azure DevOps** (for pipelines)

### Required Access
- **MLflow**: Model registry read access
- **ACR**: Push access to image repository
- **AKS**: Cluster admin access for deployments
- **Azure**: Service Principal with AKS contributor role
- **GitHub/Azure DevOps**: Repository admin for secrets

### Tools
```bash
# Local development
pip install mlflow requests flask

# Docker (for image building)
docker --version  # 20.10+

# Kubernetes CLI
kubectl version --client  # 1.20+

# Azure CLI
az version  # 2.30+
```

## Setup: GitHub Actions

### 1. Create GitHub Secrets

Navigate to: **Settings → Secrets and variables → Actions**

Add these secrets:

```
ACR_LOGIN_SERVER          # e.g., myregistry.azurecr.io
ACR_USERNAME              # ACR username
ACR_PASSWORD              # ACR password (or token)
AKS_CLUSTER_NAME          # Your AKS cluster name
AKS_RESOURCE_GROUP        # Azure resource group
MLFLOW_TRACKING_URI       # e.g., http://mlflow.example.com:5000
AZURE_SUBSCRIPTION_ID     # Your Azure subscription ID
AZURE_TENANT_ID           # Your Azure tenant ID
AZURE_CLIENT_ID           # Service Principal client ID
```

**Get credentials:**

```bash
# ACR credentials
az acr credential show -n myregistry --query "[username, passwords[0].value]"

# Service Principal
az ad sp create-for-rbac --role "Azure Kubernetes Service Cluster Admin Role" \
  --scopes /subscriptions/YOUR_SUBSCRIPTION_ID
```

### 2. Verify Workflow File

Check `.github/workflows/deploy-on-model-promotion.yml` exists and is valid:

```bash
# View workflow
cat .github/workflows/deploy-on-model-promotion.yml

# Check syntax
curl -H "Authorization: token YOUR_GITHUB_TOKEN" \
  https://api.github.com/repos/YOUR_ORG/YOUR_REPO/actions/workflows
```

### 3. Configure MLflow Webhooks

**In MLflow UI (Admin Panel):**

1. Go to **Settings → Webhooks**
2. Click **Create Webhook**
3. Configure:
   - **Event**: Model Transition Request
   - **Target URL**: `https://api.github.com/repos/YOUR_ORG/YOUR_REPO/dispatches`
   - **HTTP Method**: POST
   - **Headers**:
     ```
     Authorization: token YOUR_GITHUB_TOKEN
     Content-Type: application/json
     ```
   - **Payload**:
     ```json
     {
       "event_type": "model-promoted",
       "client_payload": {
         "model_name": "{{model_name}}",
         "model_version": "{{model_version}}"
       }
     }
     ```

**Webhook Verification:**
```bash
# Test webhook
curl -X POST https://api.github.com/repos/YOUR_ORG/YOUR_REPO/dispatches \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "model-promoted",
    "client_payload": {
      "model_name": "simple-cnn-demo",
      "model_version": "1"
    }
  }'
```

### 4. Trigger Workflow Manually (for testing)

**Via GitHub UI:**
1. Go to **Actions → Deploy on Model Promotion**
2. Click **Run workflow**
3. Fill in model name and namespace
4. Click **Run workflow**

**Via GitHub API:**
```bash
curl -X POST https://api.github.com/repos/YOUR_ORG/YOUR_REPO/actions/workflows/deploy-on-model-promotion.yml/dispatches \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ref": "main",
    "inputs": {
      "model_name": "simple-cnn-demo",
      "namespace": "production"
    }
  }'
```

## Setup: Azure DevOps

### 1. Create Service Connections

**In Azure DevOps:**

1. Go to **Project Settings → Service connections**
2. Create **Docker Registry** connection:
   - Registry type: Azure Container Registry
   - Name: `acr-service-connection`
3. Create **Kubernetes** connection:
   - Server URL: Get from AKS
   - Name: `aks-connection`
4. Create **Azure Subscription** connection:
   - Name: `azure-subscription`

### 2. Create Pipeline Variables

**In Pipeline:**

1. Go to **Pipelines → Pipeline settings**
2. Add variables:
   ```
   ACR_LOGIN_SERVER     = myregistry.azurecr.io
   aksClusterName       = my-aks-cluster
   aksResourceGroup     = my-resource-group
   azureSubscription    = azure-subscription
   kubeConnection       = aks-connection
   MLFLOW_TRACKING_URI  = http://mlflow.example.com:5000 (secure)
   ```

### 3. Configure Pipeline Schedule (Optional)

Create a scheduled trigger to retry deployments:

```yaml
schedules:
  - cron: "0 2 * * *"  # Daily at 2 AM
    displayName: Daily deployment check
    branches:
      include:
        - main
    always: false
```

### 4. Configure Environments (for approvals)

1. Go to **Pipelines → Environments**
2. Create **staging** and **production** environments
3. Add approvers for production deployments

### 5. Trigger Pipeline Manually

```bash
# Get pipeline ID
az pipelines build list --org https://dev.azure.com/YOUR_ORG --project YOUR_PROJECT

# Queue pipeline
az pipelines build queue \
  --id PIPELINE_ID \
  --org https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT \
  --variables environment=production modelName=simple-cnn-demo
```

## Setup: MLflow Webhook Handler (Self-Hosted)

For organizations that want to self-host the webhook handler:

### 1. Install Flask

```bash
pip install flask mlflow requests
```

### 2. Start Webhook Handler

```bash
python scripts/mlflow_webhook_handler.py \
  --port 5001 \
  --github-token YOUR_GITHUB_TOKEN \
  --github-repo YOUR_ORG/YOUR_REPO
```

### 3. Configure MLflow Webhook to Point to Handler

```bash
# In MLflow UI, set webhook URL to:
# http://your-handler-url:5001/webhook/mlflow
```

### 4. Verify Handler is Running

```bash
curl http://localhost:5001/health
# Response: {"status": "healthy"}

# Test handler
curl -X POST http://localhost:5001/webhook/mlflow \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "model_promoted",
    "model_name": "simple-cnn-demo",
    "model_version": "1"
  }'
```

### 5. Deploy Handler (Production)

**Docker:**
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY scripts/mlflow_webhook_handler.py .
CMD ["python", "mlflow_webhook_handler.py", "--host", "0.0.0.0", "--port", "5001"]
```

**Kubernetes:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: mlflow-webhook-handler
spec:
  ports:
    - port: 5001
      targetPort: 5001
  selector:
    app: mlflow-webhook-handler
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mlflow-webhook-handler
spec:
  replicas: 2
  selector:
    matchLabels:
      app: mlflow-webhook-handler
  template:
    metadata:
      labels:
        app: mlflow-webhook-handler
    spec:
      containers:
        - name: handler
          image: YOUR_REGISTRY/mlflow-webhook-handler:latest
          ports:
            - containerPort: 5001
          env:
            - name: GITHUB_TOKEN
              valueFrom:
                secretKeyRef:
                  name: github-secrets
                  key: token
            - name: GITHUB_REPO
              value: "YOUR_ORG/YOUR_REPO"
          livenessProbe:
            httpGet:
              path: /health
              port: 5001
            initialDelaySeconds: 10
            periodSeconds: 10
```

## Kubernetes Deployment Manifest

The production-ready manifest includes:

### Health Checks
```yaml
# Startup probe: Allow time for model loading (150s max)
startupProbe:
  httpGet:
    path: /health
  failureThreshold: 30
  periodSeconds: 5

# Liveness probe: Restart if unhealthy (failure after 30s)
livenessProbe:
  httpGet:
    path: /health
  initialDelaySeconds: 30
  failureThreshold: 3
  periodSeconds: 10

# Readiness probe: Only route traffic to ready pods
readinessProbe:
  httpGet:
    path: /ready
  initialDelaySeconds: 10
  failureThreshold: 2
  periodSeconds: 5
```

### Resource Management
```yaml
resources:
  requests:
    cpu: "500m"          # Reserve 0.5 CPU
    memory: "512Mi"      # Reserve 512 MB
  limits:
    cpu: "2000m"         # Max 2 CPU
    memory: "2Gi"        # Max 2 GB
```

### Auto-Scaling
```yaml
minReplicas: 3           # Always run 3 instances
maxReplicas: 10          # Scale up to 10
scaleOnCPU: 70%          # Scale when CPU > 70%
scaleOnMemory: 80%       # Scale when memory > 80%
```

### High Availability
```yaml
# Pod anti-affinity: Spread pods across nodes
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchLabels:
              app: inference-service
          topologyKey: kubernetes.io/hostname

# PodDisruptionBudget: Keep at least 2 pods running
minAvailable: 2

# Graceful shutdown: Allow 30s for cleanup
terminationGracePeriodSeconds: 30
```

**Deploy manifest:**
```bash
kubectl apply -f k8s/deployment-production.yaml

# Verify
kubectl get deployment inference-service -n production -o wide
kubectl get pods -n production -l app=inference-service
kubectl describe deployment inference-service -n production
```

## CI/CD Workflow Steps

### Automatic Deployment (Model Promotion)

```
1. Model Promoted to Production in MLflow
   ↓
2. MLflow Webhook Triggered
   ↓
3. GitHub Actions Workflow Started
   ├─ Extract Model Information
   ├─ Validate Model
   ├─ Build Docker Image
   ├─ Push to ACR
   ├─ Deploy to AKS
   ├─ Health Check
   ├─ Run Tests
   └─ Notify Success/Failure
   ↓
4. Model Live in Production
```

### Manual Deployment

```
GitHub Actions → Run workflow → Enter model name → Deploy
```

## Monitoring & Observability

### Check Deployment Status

```bash
# Watch deployment progress
kubectl rollout status deployment/inference-service -n production

# View pod logs
kubectl logs -n production -l app=inference-service -f

# Check pod events
kubectl describe pods -n production -l app=inference-service

# View deployment history
kubectl rollout history deployment/inference-service -n production

# Check resource usage
kubectl top nodes
kubectl top pods -n production
```

### Metrics Collection

If Prometheus is installed:
```bash
# Port-forward to Prometheus
kubectl port-forward -n monitoring svc/prometheus 9090:9090

# Query metrics
# http://localhost:9090/graph
# Query: rate(http_requests_total[5m])
```

### View Logs in Azure Monitor

```bash
# Container Insights logs
az monitor metrics list-definitions \
  --resource /subscriptions/SUB_ID/resourceGroups/GROUP/providers/Microsoft.ContainerService/managedClusters/CLUSTER

# Application Insights (if configured)
az monitor app-insights component show --app APP_NAME
```

## Troubleshooting

### Workflow Not Triggered

**Problem**: Model promoted but workflow not started

**Diagnosis:**
```bash
# Check webhook events
curl -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/repos/YOUR_ORG/YOUR_REPO/events | grep -i dispatch

# Check workflow file syntax
git check-ignore .github/workflows/deploy-on-model-promotion.yml

# View recent workflow runs
curl -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/repos/YOUR_ORG/YOUR_REPO/actions/runs?limit=10
```

**Solutions:**
- Verify webhook URL is correct: `https://api.github.com/repos/YOUR_ORG/YOUR_REPO/dispatches`
- Check GitHub token has `repo` scope
- Verify workflow file is in `main` branch
- Test webhook manually (see setup section)

### Model Validation Fails

**Problem**: `❌ Model validation failed`

**Diagnosis:**
```bash
# Check MLflow connectivity
curl $MLFLOW_TRACKING_URI/health

# List registered models
mlflow models list

# Check model status
mlflow models versions-list -n MODEL_NAME
```

**Solutions:**
- Verify `MLFLOW_TRACKING_URI` environment variable
- Ensure model is in Production stage
- Check MLflow server is accessible from CI/CD platform
- Verify model name matches exactly

### Docker Build Fails

**Problem**: `❌ Docker build failed`

**Diagnosis:**
```bash
# Test build locally
docker build -t inference-service:test .

# Check Dockerfile syntax
docker run --rm -i hadolint/hadolint < Dockerfile

# View build logs
az acr build --registry myregistry -t inference-service:test . --file Dockerfile
```

**Solutions:**
- Ensure `Dockerfile` exists in repo root
- Test Dockerfile builds locally first
- Check dependencies in requirements.txt
- Increase ACR build timeout if needed

### Container Health Check Fails

**Problem**: `❌ Health check failed after 30 attempts`

**Diagnosis:**
```bash
# Port-forward and test manually
kubectl port-forward svc/inference-service 8000:8000 -n production

# Test health endpoint
curl http://localhost:8000/health

# View container logs
kubectl logs -n production -l app=inference-service

# Check if pods are running
kubectl get pods -n production -l app=inference-service
```

**Solutions:**
- Ensure health endpoint is implemented (`/health` and `/ready`)
- Check if model loading is taking too long (increase `startupProbe.failureThreshold`)
- Verify environment variables are set correctly
- Check disk space and memory limits

### Deployment Not Found

**Problem**: `❌ Deployment not found in namespace production`

**Diagnosis:**
```bash
# Check if namespace exists
kubectl get namespace production

# List deployments
kubectl get deployment -n production

# Check RBAC permissions
kubectl auth can-i get deployments --namespace production
```

**Solutions:**
- Create namespace: `kubectl create namespace production`
- Apply deployment manifest: `kubectl apply -f k8s/deployment-production.yaml`
- Verify service principal has AKS permissions
- Check kubectl context: `kubectl config current-context`

### Rollout Timeout

**Problem**: `❌ Rollout failed: timeout waiting for condition`

**Diagnosis:**
```bash
# Check pod status
kubectl describe pods -n production -l app=inference-service

# View recent events
kubectl get events -n production --sort-by='.lastTimestamp' | tail -20

# Check pod logs for errors
kubectl logs -n production POD_NAME --previous  # If crashed
```

**Solutions:**
- Increase timeout: `--timeout 600` (10 minutes)
- Check if image pull is slow (use `imagePullPolicy: IfNotPresent`)
- Verify model loading time and increase `startupProbe.failureThreshold`
- Check cluster resources: `kubectl top nodes`
- Consider increasing pod resource requests

### Automatic Rollback Triggered

**Problem**: Deployment rolled back after failing health checks

**Diagnosis:**
```bash
# View rollout history
kubectl rollout history deployment/inference-service -n production

# View revision details
kubectl rollout history deployment/inference-service -n production --revision=X

# Check what revision was rolled back to
kubectl describe rs -n production -l app=inference-service | grep "Revision:"
```

**Solutions:**
- Review logs from failed pods: `kubectl logs -n production -l app=inference-service --tail=100`
- Increase health check timeouts if model is slow to load
- Verify all dependencies (MLflow, resources) are available
- Test model locally before promoting to Production
- Check resource limits aren't preventing pod startup

## Examples

### Example 1: Promoting a Model

```bash
# Assume model 'yolov8-detector' v3 is in Staging

# Promote to Production in MLflow
python << 'EOF'
import mlflow

mlflow.set_tracking_uri('http://127.0.0.1:5000')
client = mlflow.tracking.MlflowClient()

# Transition model stage
client.transition_model_version_stage(
    name='yolov8-detector',
    version='3',
    stage='Production'
)

print("✓ Model promoted to Production")
print("  Webhook should trigger automatically...")
EOF

# Check GitHub Actions
# Navigate to: https://github.com/YOUR_ORG/YOUR_REPO/actions

# Watch deployment
watch -n 5 'kubectl get deployment inference-service -n production -o wide'
```

### Example 2: Manual Deployment

```bash
# Trigger via GitHub Actions UI
# 1. Go to Actions → Deploy on Model Promotion
# 2. Click "Run workflow"
# 3. Enter:
#    - Model name: simple-cnn-demo
#    - Namespace: production
# 4. Click "Run workflow"

# Or via CLI
gh workflow run deploy-on-model-promotion.yml \
  -f model_name=simple-cnn-demo \
  -f namespace=production
```

### Example 3: Blue-Green Deployment

```bash
# Create two deployments
kubectl apply -f k8s/deployment-blue.yaml
kubectl apply -f k8s/deployment-green.yaml

# Deploy new model to green
kubectl set image deployment/inference-green \
  inference-service=registry/inference:new-version

# Verify green is healthy
kubectl get pods -n production -l app=inference-service,version=green

# Switch service to green
kubectl patch service inference-service -p \
  '{"spec":{"selector":{"version":"green"}}}'

# Keep blue as rollback if needed
# To rollback, switch back: selector: {"version": "blue"}
```

### Example 4: Canary Deployment (10% Traffic)

```yaml
# Deployment with canary weight
apiVersion: v1
kind: Service
metadata:
  name: inference-service
spec:
  selector:
    app: inference-service
    # Don't specify version - routes to both

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference-service-stable
spec:
  replicas: 9  # 90% of traffic
  selector:
    matchLabels:
      app: inference-service
      version: stable

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference-service-canary
spec:
  replicas: 1  # 10% of traffic
  selector:
    matchLabels:
      app: inference-service
      version: canary
```

## Security Best Practices

### Secrets Management

**Store securely:**
- GitHub: Use **Settings → Secrets** (encrypted)
- Azure DevOps: Use **Pipelines → Library → Secure files/variables**
- Never commit secrets to git

**Rotate secrets:**
```bash
# GitHub: Regenerate ACR password
az acr credential rotate --registry myregistry --password-name password1

# Update GitHub secret
gh secret set ACR_PASSWORD -b "NEW_PASSWORD"
```

### RBAC Configuration

```bash
# Create service principal for CI/CD
az ad sp create-for-rbac \
  --name "cicd-deployer" \
  --role "Azure Kubernetes Service Cluster Admin Role" \
  --scopes /subscriptions/SUB_ID

# Verify permissions
az role assignment list --assignee SERVICE_PRINCIPAL_ID
```

### Network Security

```yaml
# NetworkPolicy: Restrict pod communication
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: inference-service-policy
spec:
  podSelector:
    matchLabels:
      app: inference-service
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: ingress-controller
      ports:
        - protocol: TCP
          port: 8000
  egress:
    # Only allow to MLflow and DNS
    - to:
        - podSelector:
            matchLabels:
              app: mlflow-tracking
    - to:
        - namespaceSelector: {}
      ports:
        - protocol: UDP
          port: 53  # DNS
```

### Container Security

```yaml
securityContext:
  runAsNonRoot: true          # Don't run as root
  runAsUser: 1000             # Run as specific user
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
      - ALL                   # Drop all capabilities
```

## Performance Optimization

### Image Caching

```yaml
# Build with cache
- uses: docker/build-push-action@v5
  with:
    cache-from: type=registry,ref=${{ registry }}/{{ image }}:buildcache
    cache-to: type=registry,ref=${{ registry }}/{{ image }}:buildcache,mode=max
```

### Multi-Stage Dockerfile

```dockerfile
# Build stage
FROM python:3.10 as builder
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.10-slim
COPY --from=builder /root/.local /root/.local
COPY . .
CMD ["python", "-m", "uvicorn", "main:app"]
```

### Pod Startup Optimization

```yaml
# Pre-pull image to nodes
apiVersion: v1
kind: Pod
metadata:
  name: image-puller
spec:
  containers:
    - name: pause
      image: registry/inference-service:latest
      imagePullPolicy: Always
  restartPolicy: Never
```

## Monitoring and Alerts

### Prometheus Rules

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: inference-alerts
spec:
  groups:
    - name: inference.rules
      rules:
        # Alert if deployment replicas don't match desired
        - alert: DeploymentReplicasMismatch
          expr: |
            kube_deployment_spec_replicas{deployment="inference-service"}
            !=
            kube_deployment_status_replicas_available{deployment="inference-service"}
          for: 10m
          
        # Alert if pod restart rate is high
        - alert: PodRestartingTooOften
          expr: |
            rate(kube_pod_container_status_restarts_total{pod=~"inference.*"}[15m]) > 0.1
          for: 5m
```

## Next Steps

1. **Configure secrets** in GitHub/Azure DevOps
2. **Test webhook** with sample promotion
3. **Monitor first deployment** closely
4. **Set up alerts** in monitoring system
5. **Document runbooks** for your team
6. **Schedule training** on deployment process

## Support

For issues or questions:
- Check troubleshooting section above
- Review logs: `kubectl logs -n production -l app=inference-service`
- Test webhook: See setup section
- Contact MLflow or platform support

---

**Last Updated**: January 28, 2026  
**Status**: Production Ready ✅
