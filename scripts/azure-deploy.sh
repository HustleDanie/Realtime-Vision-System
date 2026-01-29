#!/bin/bash
# Complete Azure ACR & AKS deployment script for Linux/Mac

set -e

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-vision-rg}"
ACR_NAME="${ACR_NAME:-realtime-vision}"
AKS_NAME="${AKS_NAME:-vision-aks}"
LOCATION="${LOCATION:-eastus}"
NODE_COUNT="${NODE_COUNT:-3}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Azure Container Registry & AKS Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}[1/8] Checking prerequisites...${NC}"
for cmd in az docker kubectl; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}✗ $cmd is not installed${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✓ All prerequisites found${NC}"

# Login to Azure
echo ""
echo -e "${YELLOW}[2/8] Logging in to Azure...${NC}"
az login --use-device-code
az account show --query '{Name:name, ID:id}'

# Create Resource Group
echo ""
echo -e "${YELLOW}[3/8] Creating resource group...${NC}"
az group create --name $RESOURCE_GROUP --location $LOCATION || true
echo -e "${GREEN}✓ Resource group ready${NC}"

# Create ACR
echo ""
echo -e "${YELLOW}[4/8] Creating Azure Container Registry...${NC}"
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --sku Basic || true
echo -e "${GREEN}✓ ACR created${NC}"

# Get ACR login server
ACR_REGISTRY=$(az acr show --resource-group $RESOURCE_GROUP --name $ACR_NAME --query loginServer -o tsv)
echo "ACR Login Server: $ACR_REGISTRY"

# Login to ACR
echo ""
echo -e "${YELLOW}[5/8] Logging in to ACR...${NC}"
az acr login --name $ACR_NAME
echo -e "${GREEN}✓ Logged in to ACR${NC}"

# Build and push images
echo ""
echo -e "${YELLOW}[6/8] Building and pushing Docker images...${NC}"

SERVICES=(
    "yolo-inference:docker/Dockerfile.yolo"
    "logging-service:docker/Dockerfile.logging"
    "mlflow-server:docker/Dockerfile.mlflow"
    "camera-stream:docker/Dockerfile.camera"
    "preprocessing-service:docker/Dockerfile.preprocessing"
)

for service in "${SERVICES[@]}"; do
    IFS=':' read -r name dockerfile <<< "$service"
    echo ""
    echo -e "${YELLOW}Building $name...${NC}"
    
    # Build
    docker build --file $dockerfile --tag $name:latest .
    
    # Tag for ACR
    docker tag $name:latest $ACR_REGISTRY/$name:latest
    docker tag $name:latest $ACR_REGISTRY/$name:v1.0
    
    # Push
    docker push $ACR_REGISTRY/$name:latest
    docker push $ACR_REGISTRY/$name:v1.0
    
    echo -e "${GREEN}✓ Pushed $name${NC}"
done

echo -e "${GREEN}✓ All images built and pushed${NC}"

# Create AKS cluster
echo ""
echo -e "${YELLOW}[7/8] Creating AKS cluster...${NC}"
az aks create \
    --resource-group $RESOURCE_GROUP \
    --name $AKS_NAME \
    --node-count $NODE_COUNT \
    --enable-managed-identity \
    --vm-set-type VirtualMachineScaleSets \
    --load-balancer-sku standard \
    --enable-cluster-autoscaler \
    --min-count 1 \
    --max-count 5 \
    --enable-addons monitoring \
    --generate-ssh-keys || true
echo -e "${GREEN}✓ AKS cluster created/updated${NC}"

# Attach ACR to AKS
echo ""
echo -e "${YELLOW}[8/8] Attaching ACR to AKS...${NC}"
az aks update \
    --resource-group $RESOURCE_GROUP \
    --name $AKS_NAME \
    --attach-acr $ACR_NAME
echo -e "${GREEN}✓ ACR attached to AKS${NC}"

# Get AKS credentials
echo ""
echo -e "${YELLOW}Getting AKS credentials...${NC}"
az aks get-credentials \
    --resource-group $RESOURCE_GROUP \
    --name $AKS_NAME \
    --overwrite-existing
echo -e "${GREEN}✓ Credentials configured${NC}"

# Verify connection
echo ""
echo -e "${YELLOW}Verifying connection...${NC}"
kubectl cluster-info
echo -e "${GREEN}✓ Connected to AKS${NC}"

# Update Kubernetes manifests
echo ""
echo -e "${YELLOW}Updating Kubernetes manifests with ACR registry...${NC}"
sed -i "s|realtime-vision-system:yolo-latest|$ACR_REGISTRY/yolo-inference:latest|g" k8s/deployments.yaml
sed -i "s|realtime-vision-system:logging-latest|$ACR_REGISTRY/logging-service:latest|g" k8s/deployments.yaml
echo -e "${GREEN}✓ Manifests updated${NC}"

# Deploy to AKS
echo ""
echo -e "${YELLOW}Deploying to AKS...${NC}"
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmaps.yaml
kubectl apply -f k8s/persistent-volumes.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/deployments.yaml
kubectl apply -f k8s/services.yaml
kubectl apply -f k8s/autoscaling.yaml
echo -e "${GREEN}✓ Deployed to AKS${NC}"

# Show summary
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Deployment Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Azure Resources:${NC}"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  ACR: $ACR_REGISTRY"
echo "  AKS Cluster: $AKS_NAME"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Monitor pods:"
echo "     kubectl get pods -n vision-system -w"
echo ""
echo "  2. View logs:"
echo "     kubectl logs -n vision-system -l app=yolo -f"
echo ""
echo "  3. Check services:"
echo "     kubectl get svc -n vision-system"
echo ""
echo "  4. Access MLflow:"
echo "     kubectl port-forward -n vision-system svc/mlflow-service 5000:5000"
echo ""
echo -e "${BLUE}========================================${NC}"
