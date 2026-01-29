#!/bin/bash
# Kubernetes deployment script for Vision System

set -e

NAMESPACE="vision-system"
CONTEXT=$(kubectl config current-context)

echo "=================================================="
echo "Vision System - Kubernetes Deployment"
echo "=================================================="
echo "Cluster Context: $CONTEXT"
echo "Target Namespace: $NAMESPACE"
echo "=================================================="
echo ""

# Check prerequisites
echo "[1/7] Checking prerequisites..."
if ! command -v kubectl &> /dev/null; then
    echo "ERROR: kubectl not found. Please install kubectl."
    exit 1
fi

if ! kubectl cluster-info &> /dev/null; then
    echo "ERROR: Cannot connect to Kubernetes cluster."
    exit 1
fi

echo "✓ Kubernetes cluster is accessible"

# Create namespace
echo ""
echo "[2/7] Creating namespace..."
kubectl apply -f k8s/namespace.yaml
echo "✓ Namespace created"

# Apply ConfigMaps and Secrets
echo ""
echo "[3/7] Applying ConfigMaps and Secrets..."
kubectl apply -f k8s/configmaps.yaml
echo "✓ ConfigMaps and Secrets applied"

# Create Persistent Volumes
echo ""
echo "[4/7] Creating Persistent Volume Claims..."
kubectl apply -f k8s/persistent-volumes.yaml
echo "✓ PVCs created"

# Apply RBAC
echo ""
echo "[5/7] Applying RBAC policies..."
kubectl apply -f k8s/rbac.yaml
echo "✓ RBAC policies applied"

# Deploy services
echo ""
echo "[6/7] Deploying applications..."
kubectl apply -f k8s/deployments.yaml
kubectl apply -f k8s/services.yaml
echo "✓ Deployments and Services created"

# Enable autoscaling
echo ""
echo "[7/7] Enabling autoscaling..."
kubectl apply -f k8s/autoscaling.yaml
echo "✓ HPA configured"

# Optional: Network policies and monitoring
read -p "Enable network policies? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    kubectl apply -f k8s/network-policies.yaml
    echo "✓ Network policies applied"
fi

read -p "Apply Ingress and monitoring? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    kubectl apply -f k8s/ingress.yaml
    echo "✓ Ingress applied"
    
    if kubectl api-resources | grep -q servicemonitor; then
        kubectl apply -f k8s/monitoring.yaml
        echo "✓ Monitoring rules applied"
    else
        echo "⚠ Prometheus Operator not found, skipping monitoring"
    fi
fi

echo ""
echo "=================================================="
echo "Deployment complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Check pod status:"
echo "   kubectl get pods -n $NAMESPACE"
echo ""
echo "2. Monitor logs:"
echo "   kubectl logs -n $NAMESPACE -l app=yolo -f"
echo ""
echo "3. Wait for pods to be ready (~2-3 minutes):"
echo "   kubectl wait --for=condition=Ready pod -l app=yolo -n $NAMESPACE --timeout=300s"
echo ""
echo "4. Get service endpoints:"
echo "   kubectl get svc -n $NAMESPACE"
echo ""

# Verify deployment
echo "Waiting for pods to be ready..."
kubectl wait --for=condition=Ready pod -l app=yolo -n $NAMESPACE --timeout=300s 2>/dev/null || true
kubectl wait --for=condition=Ready pod -l app=logging -n $NAMESPACE --timeout=300s 2>/dev/null || true

echo ""
echo "Pod status:"
kubectl get pods -n $NAMESPACE
echo ""
echo "Service status:"
kubectl get svc -n $NAMESPACE
