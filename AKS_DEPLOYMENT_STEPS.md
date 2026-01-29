# Azure Kubernetes Service (AKS) Deployment - Step-by-Step Commands

## Prerequisites

```bash
# Verify installed tools
az --version              # Azure CLI 2.50+
kubectl version --client  # kubectl 1.28+
docker --version          # Docker 24+

# Set environment variables
export AZURE_SUBSCRIPTION_ID="your-subscription-id"
export RESOURCE_GROUP="vision-rg"
export ACR_NAME="realtime-vision"
export AKS_NAME="vision-aks"
export LOCATION="eastus"
export NAMESPACE="vision-system"
```

## Phase 1: Azure Resource Setup

### Step 1: Login to Azure

```bash
# Interactive login (opens browser)
az login

# Verify login
az account show --query '{Name:name, SubscriptionId:id}'

# Set active subscription
az account set --subscription $AZURE_SUBSCRIPTION_ID
```

### Step 2: Create Resource Group

```bash
# Create resource group
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

# Verify creation
az group list --query "[].name"
```

### Step 3: Create Azure Container Registry (ACR)

```bash
# Create ACR (Basic SKU = $5/month)
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled false

# Get login server (needed later)
ACR_LOGIN_SERVER=$(az acr show \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --query loginServer \
  --output tsv)

echo "ACR Login Server: $ACR_LOGIN_SERVER"

# Verify ACR creation
az acr show --resource-group $RESOURCE_GROUP --name $ACR_NAME
```

### Step 4: Create Azure Kubernetes Service (AKS)

```bash
# Create AKS cluster (3 nodes, auto-scaling enabled)
az aks create \
  --resource-group $RESOURCE_GROUP \
  --name $AKS_NAME \
  --node-count 3 \
  --vm-set-type VirtualMachineScaleSets \
  --load-balancer-sku standard \
  --enable-managed-identity \
  --enable-cluster-autoscaler \
  --min-count 1 \
  --max-count 5 \
  --enable-addons monitoring \
  --generate-ssh-keys \
  --zones 1 2 3

# This takes ~10-15 minutes, grab coffee!
```

**Monitor progress:**
```bash
# In another terminal, watch the deployment
watch -n 5 'az aks show --resource-group $RESOURCE_GROUP --name $AKS_NAME --query "provisioningState"'
```

### Step 5: Attach ACR to AKS

```bash
# Link ACR to AKS for image pull
az aks update \
  --resource-group $RESOURCE_GROUP \
  --name $AKS_NAME \
  --attach-acr $ACR_NAME

# Verify
az aks show --resource-group $RESOURCE_GROUP --name $AKS_NAME \
  --query "acrProfiles"
```

### Step 6: Get AKS Credentials

```bash
# Download kubeconfig and set current context
az aks get-credentials \
  --resource-group $RESOURCE_GROUP \
  --name $AKS_NAME

# Verify connection
kubectl cluster-info
kubectl get nodes

# Expected output:
# NAME                                STATUS   ROLES   AGE     VERSION
# aks-nodepool1-12345678-vmss000000   Ready    agent   2m      v1.28.x
# aks-nodepool1-12345678-vmss000001   Ready    agent   2m      v1.28.x
# aks-nodepool1-12345678-vmss000002   Ready    agent   2m      v1.28.x
```

## Phase 2: Build & Push Docker Images to ACR

### Step 7: Login to ACR

```bash
# Authenticate Docker with ACR
az acr login --name $ACR_NAME

# Test login
docker run hello-world
```

### Step 8: Build Docker Images

```bash
# From project root directory
cd /path/to/realtime-vision-system

# Build YOLO Inference image
docker build \
  --file docker/Dockerfile.yolo \
  --tag yolo-inference:latest \
  .

# Build Logging Service image
docker build \
  --file docker/Dockerfile.logging \
  --tag logging-service:latest \
  .

# Build MLflow Server image
docker build \
  --file docker/Dockerfile.mlflow \
  --tag mlflow-server:latest \
  .

# Build Camera Stream image
docker build \
  --file docker/Dockerfile.camera \
  --tag camera-stream:latest \
  .

# Build Preprocessing image
docker build \
  --file docker/Dockerfile.preprocessing \
  --tag preprocessing-service:latest \
  .

# Verify all images built
docker images | grep -E "(yolo|logging|mlflow|camera|preprocessing)"
```

### Step 9: Tag Images for ACR

```bash
# Tag all images for ACR
docker tag yolo-inference:latest $ACR_LOGIN_SERVER/yolo-inference:latest
docker tag yolo-inference:latest $ACR_LOGIN_SERVER/yolo-inference:v1.0
docker tag logging-service:latest $ACR_LOGIN_SERVER/logging-service:latest
docker tag mlflow-server:latest $ACR_LOGIN_SERVER/mlflow-server:latest
docker tag camera-stream:latest $ACR_LOGIN_SERVER/camera-stream:latest
docker tag preprocessing-service:latest $ACR_LOGIN_SERVER/preprocessing-service:latest

# Verify tags
docker images | grep $ACR_LOGIN_SERVER
```

### Step 10: Push Images to ACR

```bash
# Push all images
docker push $ACR_LOGIN_SERVER/yolo-inference:latest
docker push $ACR_LOGIN_SERVER/yolo-inference:v1.0
docker push $ACR_LOGIN_SERVER/logging-service:latest
docker push $ACR_LOGIN_SERVER/mlflow-server:latest
docker push $ACR_LOGIN_SERVER/camera-stream:latest
docker push $ACR_LOGIN_SERVER/preprocessing-service:latest

# Verify images in ACR
az acr repository list --resource-group $RESOURCE_GROUP --name $ACR_NAME

# Check image tags
az acr repository show-tags \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --repository yolo-inference

# Check image details
az acr repository show \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --repository yolo-inference
```

## Phase 3: Update Kubernetes Manifests

### Step 11: Update Deployment Images

```bash
# Update deployments.yaml with ACR image URLs
sed -i "s|realtime-vision-system:yolo-latest|$ACR_LOGIN_SERVER/yolo-inference:latest|g" k8s/deployments.yaml
sed -i "s|realtime-vision-system:logging-latest|$ACR_LOGIN_SERVER/logging-service:latest|g" k8s/deployments.yaml

# Verify changes
grep "image:" k8s/deployments.yaml | head -10

# Expected output:
# image: realtime-vision.azurecr.io/yolo-inference:latest
# image: realtime-vision.azurecr.io/logging-service:latest
```

## Phase 4: Deploy to AKS

### Step 12: Create Namespace

```bash
# Create dedicated namespace for vision system
kubectl create namespace $NAMESPACE

# Verify
kubectl get namespace $NAMESPACE

# Set as default namespace
kubectl config set-context --current --namespace=$NAMESPACE
```

### Step 13: Create ConfigMaps

```bash
# Apply configuration maps
kubectl apply -f k8s/configmaps.yaml -n $NAMESPACE

# Verify ConfigMaps
kubectl get configmaps -n $NAMESPACE
kubectl describe configmap yolo-config -n $NAMESPACE
```

### Step 14: Create Persistent Volumes

```bash
# Create PersistentVolumeClaims for data storage
kubectl apply -f k8s/persistent-volumes.yaml -n $NAMESPACE

# Verify PVCs
kubectl get pvc -n $NAMESPACE

# Check PVC details
kubectl describe pvc yolo-models-pvc -n $NAMESPACE
```

### Step 15: Create RBAC Resources

```bash
# Create ServiceAccounts, Roles, RoleBindings
kubectl apply -f k8s/rbac.yaml -n $NAMESPACE

# Verify RBAC
kubectl get serviceaccount -n $NAMESPACE
kubectl get role -n $NAMESPACE
kubectl get rolebinding -n $NAMESPACE
```

### Step 16: Deploy Applications

```bash
# Deploy YOLO Inference and Logging Service
kubectl apply -f k8s/deployments.yaml -n $NAMESPACE

# Verify deployments
kubectl get deployments -n $NAMESPACE

# Expected output:
# NAME                READY   UP-TO-DATE   AVAILABLE   AGE
# yolo-inference      0/2     2            0           10s
# logging-service     0/2     2            0           10s
```

### Step 17: Wait for Pods to Be Ready

```bash
# Watch pod creation (press Ctrl+C to exit)
kubectl get pods -n $NAMESPACE -w

# Or wait for specific deployment
kubectl wait --for=condition=Ready pod \
  --selector app=yolo \
  --namespace $NAMESPACE \
  --timeout=300s

# Check pod status
kubectl get pods -n $NAMESPACE -o wide

# Expected output:
# NAME                              READY   STATUS    RESTARTS   AGE
# yolo-inference-7d8f9c4c7b-xxxxx   1/1     Running   0          2m
# yolo-inference-7d8f9c4c7b-yyyyy   1/1     Running   0          2m
# logging-service-5b6f7g8h9i-xxxxx  1/1     Running   0          2m
# logging-service-5b6f7g8h9i-yyyyy  1/1     Running   0          2m
```

### Step 18: Check Pod Logs

```bash
# View YOLO pod logs
kubectl logs -n $NAMESPACE deployment/yolo-inference --tail=50

# View Logging service logs
kubectl logs -n $NAMESPACE deployment/logging-service --tail=50

# Follow logs in real-time
kubectl logs -n $NAMESPACE -l app=yolo -f

# Show logs from all replicas
kubectl logs -n $NAMESPACE --all-containers=true deployment/yolo-inference
```

### Step 19: Create Internal Services

```bash
# Create Kubernetes Services for internal communication
kubectl apply -f k8s/services.yaml -n $NAMESPACE

# Verify services
kubectl get svc -n $NAMESPACE

# Expected output:
# NAME                  TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)    AGE
# yolo-service          LoadBalancer   10.0.100.50      <pending>    8000:30123/TCP   30s
# logging-service       ClusterIP      10.0.101.20      <none>       8001/TCP         30s
# yolo-headless         ClusterIP      None             <none>       8000/TCP         30s
# logging-headless      ClusterIP      None             <none>       8001/TCP         30s
```

### Step 20: Get Service Details

```bash
# Get YOLO service details
kubectl get svc yolo-service -n $NAMESPACE -o wide
kubectl describe svc yolo-service -n $NAMESPACE

# Get Logging service details
kubectl describe svc logging-service -n $NAMESPACE

# Get service IP addresses
kubectl get svc -n $NAMESPACE -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.clusterIP}{"\n"}{end}'

# Expected output:
# yolo-service         10.0.100.50
# logging-service      10.0.101.20
```

## Phase 5: Enable Autoscaling

### Step 21: Create Horizontal Pod Autoscaler (HPA)

```bash
# Apply HPA configuration
kubectl apply -f k8s/autoscaling.yaml -n $NAMESPACE

# Verify HPA
kubectl get hpa -n $NAMESPACE

# Expected output:
# NAME                REFERENCE                          TARGETS         MINPODS   MAXPODS
# yolo-hpa            Deployment/yolo-inference         10%/70%         2         4
# logging-hpa         Deployment/logging-service        15%/75%         2         5
```

### Step 22: Monitor Autoscaling

```bash
# Watch HPA status
kubectl get hpa -n $NAMESPACE -w

# Check detailed HPA status
kubectl describe hpa yolo-hpa -n $NAMESPACE

# Get current resource metrics
kubectl top pods -n $NAMESPACE
kubectl top nodes
```

## Phase 6: Internal Service Communication

### Step 23: Test Internal Service Discovery

```bash
# DNS service discovery (from within cluster)
kubectl run -it --rm --image=busybox:1.35 \
  --restart=Never \
  -n $NAMESPACE \
  dns-test -- nslookup yolo-service

# Expected output:
# Server:		10.0.0.10
# Address:	10.0.0.10#53
# Name:	yolo-service.vision-system.svc.cluster.local
# Address: 10.0.100.50

# Test connectivity to YOLO service
kubectl run -it --rm --image=curlimages/curl:latest \
  --restart=Never \
  -n $NAMESPACE \
  curl-test -- curl http://yolo-service:8000/health

# Test connectivity to Logging service
kubectl run -it --rm --image=curlimages/curl:latest \
  --restart=Never \
  -n $NAMESPACE \
  curl-test -- curl http://logging-service:8001/health
```

### Step 24: Expose Services Internally

The services are already exposed internally via DNS. Service names accessible from any pod:

```bash
# Within cluster, services are accessible via:
# Short name (same namespace):
http://yolo-service:8000
http://logging-service:8001

# Fully qualified domain name (FQDN):
http://yolo-service.vision-system.svc.cluster.local:8000
http://logging-service.vision-system.svc.cluster.local:8001

# Example: YOLO calling Logging service
curl http://logging-service:8001/log \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"image_id": "img123", "confidence": 0.95}'
```

### Step 25: Configure Network Policies (Optional)

```bash
# Apply network policies for security
kubectl apply -f k8s/network-policies.yaml -n $NAMESPACE

# Verify network policies
kubectl get networkpolicies -n $NAMESPACE
kubectl describe networkpolicy allow-yolo-ingress -n $NAMESPACE
```

## Phase 7: Monitoring and Verification

### Step 26: Check Deployment Health

```bash
# Get all resources in namespace
kubectl get all -n $NAMESPACE

# Check deployment status
kubectl rollout status deployment/yolo-inference -n $NAMESPACE
kubectl rollout status deployment/logging-service -n $NAMESPACE

# Get detailed pod info
kubectl get pods -n $NAMESPACE -o wide

# Show resource requests/limits
kubectl get pods -n $NAMESPACE -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[*].resources}{"\n"}{end}'
```

### Step 27: Verify Service Endpoints

```bash
# Get service endpoints
kubectl get endpoints -n $NAMESPACE

# Expected output:
# NAME              ENDPOINTS                                           AGE
# yolo-service      10.244.0.10:8000,10.244.0.11:8000                 2m
# logging-service   10.244.0.12:8001,10.244.0.13:8001                 2m

# Check endpoints per pod
kubectl get endpoints yolo-service -n $NAMESPACE -o jsonpath='{.subsets[*].addresses[*].targetRef.name}' | tr ' ' '\n'
```

### Step 28: Monitor Resource Usage

```bash
# Get resource metrics for nodes
kubectl top nodes

# Get resource metrics for pods
kubectl top pods -n $NAMESPACE --containers

# Expected output:
# POD                               CPU(cores)   MEMORY(bytes)
# yolo-inference-7d8f9c4c7b-xxxxx   500m         2Gi
# logging-service-5b6f7g8h9i-xxxxx  200m         1Gi
```

### Step 29: Check Events

```bash
# Get recent cluster events
kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp'

# Watch events in real-time
kubectl get events -n $NAMESPACE -w

# Check pod-specific events
kubectl describe pod <pod-name> -n $NAMESPACE | grep -A 20 Events
```

### Step 30: View Logs from All Pods

```bash
# Stream logs from all YOLO pods
kubectl logs -n $NAMESPACE -l app=yolo --all-containers=true -f

# Stream logs from all Logging pods
kubectl logs -n $NAMESPACE -l app=logging --all-containers=true -f

# Get logs from specific pod
kubectl logs -n $NAMESPACE <pod-name>

# Get logs with timestamps
kubectl logs -n $NAMESPACE <pod-name> --timestamps=true

# Get previous logs (if pod crashed)
kubectl logs -n $NAMESPACE <pod-name> --previous
```

## Phase 8: Troubleshooting

### Step 31: Diagnose Pod Issues

```bash
# Get pod details
kubectl describe pod <pod-name> -n $NAMESPACE

# Check pod events
kubectl get events -n $NAMESPACE --field-selector involvedObject.name=<pod-name>

# Exec into running pod
kubectl exec -it <pod-name> -n $NAMESPACE -- /bin/bash

# Check resource status
kubectl get resourcequota -n $NAMESPACE
kubectl describe resourcequota -n $NAMESPACE
```

### Step 32: Check Image Pull Issues

```bash
# Verify images are in ACR
az acr repository list --resource-group $RESOURCE_GROUP --name $ACR_NAME

# Check image availability
az acr repository show \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --repository yolo-inference

# Check pod image pull status
kubectl describe pod <pod-name> -n $NAMESPACE | grep -A 5 "Image:"

# Test image pull manually
kubectl create secret docker-registry acr-secret \
  --docker-server=$ACR_LOGIN_SERVER \
  --docker-username=<username> \
  --docker-password=<password> \
  -n $NAMESPACE
```

### Step 33: Debug Service Connectivity

```bash
# Test DNS resolution
kubectl run -it --rm --image=alpine:latest \
  --restart=Never \
  -n $NAMESPACE \
  nslookup-test -- nslookup logging-service.vision-system.svc.cluster.local

# Test TCP connectivity
kubectl run -it --rm --image=busybox:latest \
  --restart=Never \
  -n $NAMESPACE \
  connectivity-test -- nc -zv logging-service 8001

# Test HTTP endpoint
kubectl run -it --rm --image=curlimages/curl:latest \
  --restart=Never \
  -n $NAMESPACE \
  http-test -- curl -v http://logging-service:8001/health
```

## Cleanup & Teardown

### Step 34: Delete Deployments

```bash
# Delete deployments (keep namespace)
kubectl delete deployment --all -n $NAMESPACE

# Delete specific deployment
kubectl delete deployment yolo-inference -n $NAMESPACE

# Delete services
kubectl delete svc --all -n $NAMESPACE

# Delete PVCs (WARNING: deletes data)
kubectl delete pvc --all -n $NAMESPACE
```

### Step 35: Delete Namespace

```bash
# Delete entire namespace (deletes all resources)
kubectl delete namespace $NAMESPACE

# Verify deletion
kubectl get namespace
```

### Step 36: Delete AKS Cluster

```bash
# Delete AKS cluster (WARNING: irreversible)
az aks delete \
  --resource-group $RESOURCE_GROUP \
  --name $AKS_NAME \
  --yes

# Delete ACR
az acr delete \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --yes

# Delete resource group (WARNING: deletes all resources)
az group delete \
  --resource-group $RESOURCE_GROUP \
  --yes
```

## Quick Reference Commands

```bash
# Common operations
kubectl apply -f <manifest.yaml> -n $NAMESPACE        # Deploy
kubectl delete -f <manifest.yaml> -n $NAMESPACE       # Undeploy
kubectl get pods -n $NAMESPACE                         # List pods
kubectl logs -n $NAMESPACE <pod-name>                 # View logs
kubectl describe pod <pod-name> -n $NAMESPACE         # Pod details
kubectl exec -it <pod-name> -n $NAMESPACE -- bash     # SSH into pod
kubectl port-forward -n $NAMESPACE svc/yolo-service 8000:8000  # Port forward
kubectl scale deployment yolo-inference --replicas=3 -n $NAMESPACE  # Scale
kubectl rollout restart deployment/yolo-inference -n $NAMESPACE  # Restart
kubectl top pods -n $NAMESPACE                        # Resource usage
```

## Service Access Patterns

### From Within Cluster (Pod-to-Pod)

```python
# Python example (from YOLO pod calling Logging service)
import requests

# Service DNS name
url = "http://logging-service:8001/log"
response = requests.post(url, json={"image_id": "img123"})
```

### From Local Machine (Port Forward)

```bash
# Forward YOLO service to localhost
kubectl port-forward -n $NAMESPACE svc/yolo-service 8000:8000 &

# Now access from local machine
curl http://localhost:8000/predict
```

### From External Clients (If LoadBalancer)

```bash
# Get external IP (if configured as LoadBalancer)
kubectl get svc yolo-service -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# Access from external
curl http://<external-ip>:8000/predict
```

## Summary Checklist

```
✓ Phase 1: Azure resources created (ACR, AKS)
✓ Phase 2: Docker images built and pushed to ACR
✓ Phase 3: Kubernetes manifests updated
✓ Phase 4: Services deployed to AKS
✓ Phase 5: Autoscaling configured
✓ Phase 6: Internal service communication verified
✓ Phase 7: Health and monitoring checks passed
✓ Phase 8: Troubleshooting commands documented
✓ Services exposed internally and accessible via DNS
✓ Ready for production use
```
