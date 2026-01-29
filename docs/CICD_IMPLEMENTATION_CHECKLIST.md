# CI/CD Implementation Checklist

## Pre-Setup Verification

- [ ] MLflow tracking server is running and accessible
  - Test: `curl $MLFLOW_TRACKING_URI/health`
- [ ] Azure Container Registry (ACR) is created
  - Test: `az acr show --name myregistry`
- [ ] AKS cluster exists and is accessible
  - Test: `kubectl cluster-info`
- [ ] GitHub repository (with admin access) OR Azure DevOps (with project admin)
  - Test: Can see **Settings** tab / **Project Settings**
- [ ] Azure CLI installed and authenticated
  - Test: `az account show`
- [ ] kubectl installed and configured
  - Test: `kubectl config current-context`
- [ ] Docker installed locally
  - Test: `docker version`

## GitHub Actions Setup

### Secrets Configuration

- [ ] Add ACR credentials to GitHub Secrets
  ```bash
  # Get credentials
  az acr credential show -n myregistry --query "[username, passwords[0].value]"
  ```
  
  - [ ] `ACR_LOGIN_SERVER` = `myregistry.azurecr.io`
  - [ ] `ACR_USERNAME` = `<from above>`
  - [ ] `ACR_PASSWORD` = `<from above>`

- [ ] Add AKS information
  ```bash
  # Get cluster info
  az aks show -g my-resource-group -n my-cluster
  ```
  
  - [ ] `AKS_CLUSTER_NAME` = `my-cluster`
  - [ ] `AKS_RESOURCE_GROUP` = `my-resource-group`

- [ ] Add Azure Service Principal
  ```bash
  # Create if needed
  az ad sp create-for-rbac --role "Azure Kubernetes Service Cluster Admin Role" \
    --scopes /subscriptions/YOUR_SUBSCRIPTION_ID
  ```
  
  - [ ] `AZURE_SUBSCRIPTION_ID` = `<your subscription>`
  - [ ] `AZURE_TENANT_ID` = `<from sp output>`
  - [ ] `AZURE_CLIENT_ID` = `<appId from sp output>`

- [ ] Add MLflow URI
  - [ ] `MLFLOW_TRACKING_URI` = `http://mlflow.example.com:5000` or `http://127.0.0.1:5000`

### Workflow File

- [ ] Verify workflow file exists: `.github/workflows/deploy-on-model-promotion.yml`
  ```bash
  ls -la .github/workflows/deploy-on-model-promotion.yml
  ```

- [ ] Commit and push to main branch
  ```bash
  git add .github/workflows/deploy-on-model-promotion.yml
  git commit -m "Add CI/CD workflow for model promotion"
  git push origin main
  ```

- [ ] Verify workflow appears in GitHub UI
  - Go to **Actions** tab
  - Should see "Deploy on Model Promotion" in workflow list

### MLflow Webhook Configuration

- [ ] Create GitHub Personal Access Token
  - Go to **GitHub Settings → Developer settings → Personal access tokens**
  - Click **Generate new token (classic)**
  - Select scope: `repo`
  - Copy token

- [ ] Configure MLflow webhook
  - MLflow UI → **Settings → Webhooks**
  - Click **Create Webhook**
  - Fill in:
    ```
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
  - Click **Test** to verify

- [ ] Webhook test successful
  - Check GitHub repository events (not in UI, but webhook was sent)

## Azure DevOps Setup (Alternative)

### Service Connections

- [ ] Create Docker Registry connection
  - **Project Settings → Service connections → New service connection**
  - Type: **Azure Container Registry**
  - Select your Azure subscription
  - Select your registry
  - Name: `acr-service-connection`

- [ ] Create Azure Subscription connection
  - Type: **Azure Resource Manager**
  - Choose service principal (auto or create new)
  - Name: `azure-subscription`

- [ ] Create Kubernetes connection
  - Type: **Kubernetes**
  - Server URL: Get from `kubectl cluster-info` (use HTTPS URL)
  - Kubeconfig: Paste contents of `~/.kube/config`
  - Name: `aks-connection`

### Pipeline Variables

- [ ] Create variable group: `deployment-variables`
  - `ACR_LOGIN_SERVER` = `myregistry.azurecr.io`
  - `aksClusterName` = `my-cluster`
  - `aksResourceGroup` = `my-resource-group`
  - `MLFLOW_TRACKING_URI` = `http://mlflow.example.com:5000` (mark as secure)

### Pipeline Creation

- [ ] Verify `azure-pipelines.yml` exists in repo
  ```bash
  ls -la azure-pipelines.yml
  ```

- [ ] Create pipeline in Azure DevOps
  - **Pipelines → New pipeline**
  - Select **Existing Azure Pipelines YAML**
  - Branch: `main`
  - Path: `azure-pipelines.yml`
  - Name: `Deploy on Model Promotion`

- [ ] Configure pipeline settings
  - YAML path verified
  - Default branch set to `main`

## Kubernetes Deployment

- [ ] Apply production manifest
  ```bash
  kubectl apply -f k8s/deployment-production.yaml
  ```

- [ ] Verify resources created
  ```bash
  # Should show: namespace, configmap, secret, serviceaccount, role, rolebinding, deployment, service, hpa, pdb, networkpolicy
  kubectl get all -n production
  ```

- [ ] Check deployment is running
  ```bash
  kubectl get deployment inference-service -n production
  # Should show: 3 replicas READY 3 AVAILABLE
  ```

- [ ] Verify pods are starting
  ```bash
  kubectl get pods -n production -l app=inference-service
  # Should show 3 pods in Running/Ready state
  ```

- [ ] Check service
  ```bash
  kubectl get service inference-service -n production
  # Note the EXTERNAL-IP or CLUSTER-IP
  ```

- [ ] Verify ConfigMap
  ```bash
  kubectl get configmap inference-config -n production -o yaml
  ```

- [ ] Verify Secret
  ```bash
  kubectl get secret inference-secrets -n production
  ```

- [ ] Check HPA
  ```bash
  kubectl get hpa inference-service-hpa -n production
  ```

## Health Endpoint Implementation

Your FastAPI application must implement these endpoints:

- [ ] `GET /health` endpoint
  ```python
  @app.get("/health")
  async def health():
      return {"status": "healthy"}
  ```

- [ ] `GET /ready` endpoint
  ```python
  @app.get("/ready")
  async def ready():
      # Check model is loaded, database is accessible, etc.
      return {"status": "ready"}
  ```

- [ ] `GET /metrics` endpoint (for Prometheus, optional)
  ```python
  from prometheus_client import make_asgi_app
  app.mount("/metrics", make_asgi_app())
  ```

- [ ] Test endpoints locally
  ```bash
  # After starting your app
  curl http://localhost:8000/health
  curl http://localhost:8000/ready
  ```

## Testing Before Production

### Test 1: Manual Workflow Trigger

- [ ] Trigger workflow manually
  - **GitHub Actions:**
    - Go to **Actions → Deploy on Model Promotion**
    - Click **Run workflow**
    - Enter `model_name` and `namespace`
    - Click **Run workflow**

- [ ] Watch workflow execution
  - All jobs should complete: extract → validate → build → deploy → test
  - Status should be ✓ (green)

### Test 2: Verify AKS Deployment

- [ ] Check pod status
  ```bash
  kubectl get pods -n production -l app=inference-service -o wide
  # All pods should be Running and Ready
  ```

- [ ] View pod logs
  ```bash
  kubectl logs -n production -l app=inference-service | head -50
  # Should show model loading, workers starting, etc.
  ```

- [ ] Port-forward to service
  ```bash
  kubectl port-forward svc/inference-service 8000:8000 -n production &
  ```

- [ ] Test health endpoint
  ```bash
  curl http://localhost:8000/health
  # Should return: {"status": "healthy"}
  ```

- [ ] Test ready endpoint
  ```bash
  curl http://localhost:8000/ready
  # Should return: {"status": "ready"}
  ```

### Test 3: Promote Model and Verify Auto-Deployment

- [ ] Promote model to Production (in MLflow or via script)
  ```python
  import mlflow
  mlflow.set_tracking_uri('http://127.0.0.1:5000')
  client = mlflow.tracking.MlflowClient()
  client.transition_model_version_stage(
      name='simple-cnn-demo',
      version='1',
      stage='Production'
  )
  ```

- [ ] Workflow should trigger automatically
  - Check **GitHub Actions** or **Azure Pipelines** for new run
  - Wait for workflow to complete (3-5 minutes)

- [ ] Verify deployment updated
  ```bash
  kubectl get deployment inference-service -n production
  # Should show updated replicas rolling out
  ```

- [ ] Verify pod health
  ```bash
  kubectl get pods -n production -l app=inference-service
  # All pods should transition to Running/Ready
  ```

- [ ] Check deployment history
  ```bash
  kubectl rollout history deployment/inference-service -n production
  # Should show multiple revisions
  ```

### Test 4: Rollback Behavior

- [ ] Simulate failure (optional test)
  - Kill a pod: `kubectl delete pod POD_NAME -n production`
  - Watch new pod auto-restart
  - Verify HPA scales if needed

- [ ] Manual rollback
  ```bash
  kubectl rollout undo deployment/inference-service -n production
  # Should revert to previous working version
  ```

- [ ] Verify rollback successful
  ```bash
  kubectl rollout status deployment/inference-service -n production
  ```

## Monitoring & Observability

### Logging

- [ ] Check pod logs
  ```bash
  kubectl logs -n production -l app=inference-service --tail=100 -f
  ```

- [ ] View pod events
  ```bash
  kubectl describe pods -n production -l app=inference-service
  ```

- [ ] Stream logs from all replicas
  ```bash
  kubectl logs -n production -l app=inference-service -f --all-containers=true --timestamps=true
  ```

### Metrics (if Prometheus configured)

- [ ] Verify ServiceMonitor created
  ```bash
  kubectl get servicemonitor -n production
  ```

- [ ] Check Prometheus scrapes metrics
  - Access Prometheus UI (if exposed)
  - Query: `rate(http_requests_total[5m])`

### Events

- [ ] Monitor events
  ```bash
  kubectl get events -n production --sort-by='.lastTimestamp'
  ```

- [ ] Watch for warnings/errors
  ```bash
  kubectl get events -n production --field-selector type=Warning
  ```

## Security Verification

- [ ] Verify RBAC permissions
  ```bash
  kubectl get rolebinding -n production
  kubectl get role -n production
  ```

- [ ] Check NetworkPolicy is applied
  ```bash
  kubectl get networkpolicy -n production
  ```

- [ ] Verify pods run as non-root
  ```bash
  kubectl get pods -n production -o jsonpath='{.items[*].spec.containers[*].securityContext.runAsUser}'
  # Should show 1000 for all pods
  ```

- [ ] Check secrets are used correctly
  ```bash
  kubectl get pods -n production -o jsonpath='{.items[*].spec.containers[*].env[?(@.valueFrom.secretKeyRef)]}' | jq .
  ```

## Performance Baseline

### Record baseline metrics

- [ ] Pod startup time
  ```bash
  # Create pod, measure time to Ready
  kubectl describe pods -n production | grep -i "ready\|created"
  ```

- [ ] Response latency
  ```bash
  # After port-forward
  time curl http://localhost:8000/predict -d '...'
  ```

- [ ] Throughput
  ```bash
  # Send 100 concurrent requests and measure
  ```

- [ ] Resource utilization
  ```bash
  kubectl top pods -n production
  kubectl top nodes
  ```

## Cleanup (if needed)

- [ ] Delete Kubernetes resources
  ```bash
  kubectl delete namespace production
  ```

- [ ] Delete Docker images from ACR
  ```bash
  az acr repository delete --name myregistry --image inference-service:latest
  ```

- [ ] Delete GitHub secrets
  - **Settings → Secrets and variables → Actions**
  - Delete each secret

- [ ] Delete Azure DevOps service connections
  - **Project Settings → Service connections**
  - Delete each connection

## Post-Deployment Checklist

- [ ] Team training scheduled (CI/CD process)
- [ ] Runbooks documented (how to handle failures)
- [ ] On-call rotation established (who monitors)
- [ ] Alert rules configured (MLflow, AKS, GitHub)
- [ ] Backup/recovery plan documented
- [ ] Cost monitoring set up (AKS resources)
- [ ] Security audit completed (RBAC, networking)
- [ ] Documentation updated (internal wiki/docs)

## Common Gotchas

- [ ] **Don't forget** to mark `MLFLOW_TRACKING_URI` as secure in Azure DevOps
- [ ] **Make sure** GitHub token has `repo` scope (not just `public_repo`)
- [ ] **Verify** AKS subnet has outbound access to Docker Hub/ACR
- [ ] **Ensure** MLflow is accessible from AKS (network/firewall rules)
- [ ] **Check** Docker image size (should be < 2GB)
- [ ] **Validate** model loading time (startup probe timeout)
- [ ] **Test** webhook payload format matches MLflow templates
- [ ] **Confirm** service principal has AKS Cluster Admin role (not just Contributor)
- [ ] **Remember** to apply NetworkPolicy if using strict network policies
- [ ] **Don't** commit secrets to git (use secrets manager)

## Verification Commands (Run in order)

```bash
# 1. Verify Azure connectivity
az account show
az aks get-credentials -g my-resource-group -n my-cluster

# 2. Verify kubectl access
kubectl cluster-info
kubectl get nodes

# 3. Verify Kubernetes resources
kubectl get namespace production
kubectl get deployment inference-service -n production
kubectl get pods -n production
kubectl get service inference-service -n production

# 4. Verify ACR access
az acr login --name myregistry
az acr repository list --name myregistry

# 5. Verify MLflow access
curl http://mlflow.example.com:5000/health

# 6. Verify GitHub Actions
curl -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/repos/YOUR_ORG/YOUR_REPO/actions/runs

# 7. Test health endpoint
kubectl port-forward svc/inference-service 8000:8000 -n production &
curl http://localhost:8000/health
```

## Success Criteria

✅ All checklist items completed when:

1. Secrets configured in CI/CD platform
2. Workflow/pipeline file present and valid
3. Kubernetes manifest applied (3 pods running)
4. Health endpoints responding (200 OK)
5. Manual deployment trigger works (pods updated)
6. Model promotion triggers deployment automatically
7. Rollout completes in < 5 minutes
8. All pods healthy and ready
9. Tests pass successfully
10. Team trained on deployment process

---

**Status**: Ready to Deploy ✅  
**Estimated Time**: 30-45 minutes for complete setup  
**Support**: See [CICD_WORKFLOW_GUIDE.md](CICD_WORKFLOW_GUIDE.md) for detailed help
