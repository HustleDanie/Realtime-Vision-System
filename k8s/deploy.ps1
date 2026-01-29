@echo off
REM Kubernetes deployment script for Vision System (Windows PowerShell)

$NAMESPACE = "vision-system"
$CONTEXT = kubectl config current-context

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Vision System - Kubernetes Deployment" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Cluster Context: $CONTEXT" -ForegroundColor Yellow
Write-Host "Target Namespace: $NAMESPACE" -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Write-Host "[1/7] Checking prerequisites..." -ForegroundColor Green
try {
    kubectl cluster-info | Out-Null
    Write-Host "`u{2713} Kubernetes cluster is accessible" -ForegroundColor Green
}
catch {
    Write-Host "ERROR: Cannot connect to Kubernetes cluster." -ForegroundColor Red
    exit 1
}

# Create namespace
Write-Host ""
Write-Host "[2/7] Creating namespace..." -ForegroundColor Green
kubectl apply -f k8s/namespace.yaml
Write-Host "`u{2713} Namespace created" -ForegroundColor Green

# Apply ConfigMaps and Secrets
Write-Host ""
Write-Host "[3/7] Applying ConfigMaps and Secrets..." -ForegroundColor Green
kubectl apply -f k8s/configmaps.yaml
Write-Host "`u{2713} ConfigMaps and Secrets applied" -ForegroundColor Green

# Create Persistent Volumes
Write-Host ""
Write-Host "[4/7] Creating Persistent Volume Claims..." -ForegroundColor Green
kubectl apply -f k8s/persistent-volumes.yaml
Write-Host "`u{2713} PVCs created" -ForegroundColor Green

# Apply RBAC
Write-Host ""
Write-Host "[5/7] Applying RBAC policies..." -ForegroundColor Green
kubectl apply -f k8s/rbac.yaml
Write-Host "`u{2713} RBAC policies applied" -ForegroundColor Green

# Deploy services
Write-Host ""
Write-Host "[6/7] Deploying applications..." -ForegroundColor Green
kubectl apply -f k8s/deployments.yaml
kubectl apply -f k8s/services.yaml
Write-Host "`u{2713} Deployments and Services created" -ForegroundColor Green

# Enable autoscaling
Write-Host ""
Write-Host "[7/7] Enabling autoscaling..." -ForegroundColor Green
kubectl apply -f k8s/autoscaling.yaml
Write-Host "`u{2713} HPA configured" -ForegroundColor Green

# Optional: Network policies and monitoring
$response = Read-Host "Enable network policies? (y/n)"
if ($response -eq "y" -or $response -eq "Y") {
    kubectl apply -f k8s/network-policies.yaml
    Write-Host "`u{2713} Network policies applied" -ForegroundColor Green
}

$response = Read-Host "Apply Ingress and monitoring? (y/n)"
if ($response -eq "y" -or $response -eq "Y") {
    kubectl apply -f k8s/ingress.yaml
    Write-Host "`u{2713} Ingress applied" -ForegroundColor Green
    
    $hasPrometheus = kubectl api-resources 2>/dev/null | Select-String servicemonitor
    if ($hasPrometheus) {
        kubectl apply -f k8s/monitoring.yaml
        Write-Host "`u{2713} Monitoring rules applied" -ForegroundColor Green
    } else {
        Write-Host "`u{26a0} Prometheus Operator not found, skipping monitoring" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Deployment complete!" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Check pod status:" -ForegroundColor White
Write-Host "   kubectl get pods -n $NAMESPACE" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Monitor logs:" -ForegroundColor White
Write-Host "   kubectl logs -n $NAMESPACE -l app=yolo -f" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Wait for pods to be ready (2-3 minutes):" -ForegroundColor White
Write-Host "   kubectl wait --for=condition=Ready pod -l app=yolo -n $NAMESPACE --timeout=300s" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. Get service endpoints:" -ForegroundColor White
Write-Host "   kubectl get svc -n $NAMESPACE" -ForegroundColor Cyan
Write-Host ""

# Verify deployment
Write-Host "Waiting for pods to be ready..." -ForegroundColor Yellow
kubectl wait --for=condition=Ready pod -l app=yolo -n $NAMESPACE --timeout=300s 2>/dev/null
kubectl wait --for=condition=Ready pod -l app=logging -n $NAMESPACE --timeout=300s 2>/dev/null

Write-Host ""
Write-Host "Pod status:" -ForegroundColor Yellow
kubectl get pods -n $NAMESPACE
Write-Host ""
Write-Host "Service status:" -ForegroundColor Yellow
kubectl get svc -n $NAMESPACE
