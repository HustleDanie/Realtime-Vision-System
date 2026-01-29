# CI/CD Workflow: Quick Start Guide

Get your CI/CD pipeline running in 10 minutes.

## What You'll Get

```
MLflow Model Promotion → Automatic Build → Push to ACR → Deploy to AKS → Live in Production
```

## Prerequisites Checklist

- [ ] MLflow tracking server running (accessible)
- [ ] Azure Container Registry (ACR) created
- [ ] AKS cluster created and accessible
- [ ] GitHub repository created
- [ ] GitHub admin access
- [ ] Azure CLI installed and authenticated
- [ ] kubectl configured to access your AKS cluster

## 5-Minute Setup: GitHub Actions

### Step 1: Add Secrets (2 minutes)

```bash
# Get ACR credentials
az acr credential show -n myregistry --query "[username, passwords[0].value]"
# Output:
# "username"
# "password"

# Get Service Principal
az ad sp create-for-rbac --role "Azure Kubernetes Service Cluster Admin Role" \
  --scopes /subscriptions/YOUR_SUBSCRIPTION_ID
# Output:
# {
#   "appId": "AZURE_CLIENT_ID",
#   "password": "AZURE_CLIENT_SECRET",
#   "tenant": "AZURE_TENANT_ID"
# }
```

Add to GitHub: **Settings → Secrets and variables → Actions → New repository secret**

```
ACR_LOGIN_SERVER      = myregistry.azurecr.io
ACR_USERNAME          = USERNAME_FROM_ABOVE
ACR_PASSWORD          = PASSWORD_FROM_ABOVE
AKS_CLUSTER_NAME      = my-aks-cluster
AKS_RESOURCE_GROUP    = my-resource-group
MLFLOW_TRACKING_URI   = http://mlflow.example.com:5000
AZURE_SUBSCRIPTION_ID = YOUR_SUBSCRIPTION_ID
AZURE_TENANT_ID       = YOUR_TENANT_ID
AZURE_CLIENT_ID       = YOUR_CLIENT_ID
```

### Step 2: Deploy Workflow File (1 minute)

File: `.github/workflows/deploy-on-model-promotion.yml`

Already provided in your repository. Push to main:

```bash
git add .github/workflows/deploy-on-model-promotion.yml
git commit -m "Add model promotion CI/CD workflow"
git push origin main
```

### Step 3: Deploy Kubernetes Manifests (1 minute)

```bash
# Create production namespace and resources
kubectl apply -f k8s/deployment-production.yaml

# Verify
kubectl get deployment inference-service -n production
kubectl get pods -n production
```

### Step 4: Configure MLflow Webhook (1 minute)

**In MLflow UI:**

1. Go to **Settings → Webhooks**
2. Click **Create Webhook**
3. Fill in:
   ```
   Event: Model Transition Request
   Destination URL: https://api.github.com/repos/YOUR_ORG/YOUR_REPO/dispatches
   HTTP Method: POST
   Headers:
     Authorization: token YOUR_GITHUB_TOKEN
     Content-Type: application/json
   Payload:
     {
       "event_type": "model-promoted",
       "client_payload": {
         "model_name": "{{model_name}}",
         "model_version": "{{model_version}}"
       }
     }
   ```

**Get GitHub Token:**
1. Go to **GitHub Settings → Developer settings → Personal access tokens**
2. Click **Generate new token**
3. Select scope: `repo`
4. Copy token and use in webhook

### Step 5: Test It! (Done!)

Promote a model:

```python
import mlflow

mlflow.set_tracking_uri('http://127.0.0.1:5000')
client = mlflow.tracking.MlflowClient()

# Promote to Production
client.transition_model_version_stage(
    name='simple-cnn-demo',
    version='1',
    stage='Production'
)

print("✓ Model promoted! Check GitHub Actions...")
```

**Watch deployment:**

```bash
# GitHub UI: Actions → Deploy on Model Promotion → Latest run
# Or terminal:
watch kubectl get deployment inference-service -n production -o wide
```

## 5-Minute Setup: Azure DevOps (Alternative)

### Step 1: Create Service Connections (2 minutes)

**In Azure DevOps:**

1. **Project Settings → Service connections**
2. **New service connection → Docker Registry**
   - Registry type: Azure Container Registry
   - Azure subscription: Select yours
   - Registry name: myregistry
   - Service connection name: `acr-service-connection`

3. **New service connection → Azure Resource Manager**
   - Subscription: Select yours
   - Resource group: (leave empty)
   - Service connection name: `azure-subscription`

4. **New service connection → Kubernetes**
   - Server URL: `https://YOUR_CLUSTER_DNS:443`
   - Kubeconfig: Paste from `kubectl config view`
   - Service connection name: `aks-connection`

### Step 2: Add Secrets (1 minute)

**Pipelines → Library → Variable groups**

Create group: `deployment-secrets`

Add variables:
```
MLFLOW_TRACKING_URI = http://mlflow.example.com:5000 (secure)
```

### Step 3: Create Pipeline (1 minute)

**Pipelines → New pipeline → Existing Azure Pipelines YAML**

File: `azure-pipelines.yml` (already in your repo)

### Step 4: Configure Trigger (1 minute)

**Pipeline settings → Triggers**

Choose trigger type:
- **Webhook** (from MLflow)
- **Scheduled** (daily at 2 AM)
- **Manual** (via UI)

### Step 5: Test It! (Done!)

```bash
# Queue pipeline manually
az pipelines build queue \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT \
  --definition PIPELINE_ID

# Watch in UI: Pipelines → Recent
```

## Common Commands

### Test Webhook Trigger

```bash
# GitHub
curl -X POST https://api.github.com/repos/YOUR_ORG/YOUR_REPO/dispatches \
  -H "Authorization: token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "model-promoted",
    "client_payload": {
      "model_name": "simple-cnn-demo",
      "model_version": "1"
    }
  }'
```

### Monitor Deployment

```bash
# Watch deployment status
kubectl rollout status deployment/inference-service -n production

# View logs
kubectl logs -n production -l app=inference-service -f

# Check health
kubectl port-forward svc/inference-service 8000:8000 -n production &
curl http://localhost:8000/health
```

### Troubleshoot

```bash
# Workflow didn't trigger?
# - Check MLflow webhook logs
# - Verify GitHub token is valid
# - Test webhook manually (curl command above)

# Deployment failed?
# - Check pod logs: kubectl logs -n production POD_NAME
# - Check events: kubectl describe pods -n production
# - Check resources: kubectl top nodes

# Rollback
kubectl rollout undo deployment/inference-service -n production
```

## Workflow Status URLs

**GitHub Actions:**
```
https://github.com/YOUR_ORG/YOUR_REPO/actions
```

**Azure DevOps:**
```
https://dev.azure.com/YOUR_ORG/YOUR_PROJECT/_build
```

## What Happens During Deployment

```
1. Webhook triggered (model promoted to Production)
2. Extract model version from MLflow
3. Validate model exists and is ready
4. Build Docker image with new model
5. Push image to ACR
6. Get AKS credentials
7. Update deployment image
8. Wait for rollout (RollingUpdate strategy)
9. Check pod health and readiness
10. Run test predictions
11. Notify success or trigger rollback
```

**Typical time:** 3-5 minutes

## Environment Variables Required

Set in GitHub/Azure DevOps secrets:

```bash
# Azure credentials (for AKS access)
AZURE_SUBSCRIPTION_ID    # Azure subscription ID
AZURE_TENANT_ID          # Azure tenant ID
AZURE_CLIENT_ID          # Service Principal client ID

# Container Registry
ACR_LOGIN_SERVER         # myregistry.azurecr.io
ACR_USERNAME             # Registry username
ACR_PASSWORD             # Registry password (or token)

# Kubernetes
AKS_CLUSTER_NAME         # Your AKS cluster
AKS_RESOURCE_GROUP       # Azure resource group

# MLflow
MLFLOW_TRACKING_URI      # http://mlflow.example.com:5000
```

## Verify Everything is Working

### 1. Check workflow file exists
```bash
ls -la .github/workflows/deploy-on-model-promotion.yml
```

### 2. Check K8s deployment
```bash
kubectl get deployment inference-service -n production
# Should show: 3 replicas running
```

### 3. Check MLflow webhook
```python
import mlflow

mlflow.set_tracking_uri('http://127.0.0.1:5000')
client = mlflow.tracking.MlflowClient()

# List recent registered models
models = client.search_registered_models()
for model in models[:5]:
    print(f"- {model.name}")
```

### 4. Test manual deployment
```bash
# GitHub: Actions → Deploy on Model Promotion → Run workflow
# Azure: Pipelines → Run → Enter parameters
```

### 5. Verify AKS access
```bash
kubectl cluster-info
kubectl get nodes
```

## Next Steps

1. ✅ Complete setup above
2. ✅ Test with manual deployment trigger
3. ✅ Promote a model to Production
4. ✅ Watch CI/CD workflow run
5. ✅ Verify pod is healthy: `curl SERVICE_IP:8000/health`
6. ✅ Read full guide: [CICD_WORKFLOW_GUIDE.md](CICD_WORKFLOW_GUIDE.md)
7. ✅ Set up monitoring and alerts

## Troubleshooting Quick Links

| Problem | Check |
|---------|-------|
| Workflow not triggered | Webhook configuration, GitHub token |
| Build fails | Dockerfile, ACR connectivity |
| Deployment fails | AKS access, Service Principal, RBAC |
| Health check fails | Pod logs, model loading time, resources |
| Image pull fails | ACR credentials, imagePullSecrets |

See [CICD_WORKFLOW_GUIDE.md](CICD_WORKFLOW_GUIDE.md) for detailed troubleshooting.

## Support

- **GitHub Actions**: https://docs.github.com/actions
- **Azure DevOps**: https://learn.microsoft.com/azure/devops
- **MLflow**: https://mlflow.org/docs
- **Kubernetes**: https://kubernetes.io/docs

---

**Status**: ✅ Ready to Deploy  
**Time to Setup**: 10 minutes  
**First Deployment Time**: 3-5 minutes
