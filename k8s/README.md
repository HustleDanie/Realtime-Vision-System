# Kubernetes Deployment Guide

## Overview

This directory contains production-ready Kubernetes manifests for deploying the Vision System microservices:
- **YOLO Inference Service** (GPU-accelerated object detection)
- **Logging Service** (prediction storage and metadata)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                    │
├─────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────┐ │
│  │           vision-system Namespace                   │ │
│  ├────────────────────────────────────────────────────┤ │
│  │                                                     │ │
│  │  ┌──────────────────┐    ┌──────────────────────┐ │ │
│  │  │  YOLO Inference  │    │  Logging Service     │ │ │
│  │  │  (2-4 replicas)  │───▶│  (2-5 replicas)      │ │ │
│  │  │  (GPU-required)  │    │                      │ │ │
│  │  └──────────────────┘    └──────────────────────┘ │ │
│  │         │                        │                │ │
│  │         ▼                        ▼                │ │
│  │  ┌──────────────────────────────────────────────┐ │ │
│  │  │     Persistent Volumes (PVC)                 │ │ │
│  │  │  • yolo-models (10Gi)                        │ │ │
│  │  │  • logging-data (20Gi)                       │ │ │
│  │  │  • prediction-images (50Gi)                  │ │ │
│  │  └──────────────────────────────────────────────┘ │ │
│  │                                                     │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Files

### Core Manifests

1. **namespace.yaml** - Creates `vision-system` namespace
2. **configmaps.yaml** - Configuration and environment variables for all services
3. **persistent-volumes.yaml** - PersistentVolumeClaims for data storage
4. **deployments.yaml** - Deployment definitions for YOLO and Logging services
5. **services.yaml** - Kubernetes Services (ClusterIP, LoadBalancer, Headless)
6. **rbac.yaml** - Role-Based Access Control (ServiceAccounts, Roles, RoleBindings)

### Advanced Features

7. **autoscaling.yaml** - Horizontal Pod Autoscaler (HPA) for both services
8. **network-policies.yaml** - Network segmentation and traffic control
9. **ingress.yaml** - External API exposure with TLS
10. **monitoring.yaml** - Prometheus monitoring and alerting rules

## Quick Start

### Prerequisites

```bash
# Check Kubernetes cluster connectivity
kubectl cluster-info

# Verify GPU support (for YOLO service)
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\.com/gpu

# Install metrics-server (required for HPA)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### Deploy All Services

```bash
# 1. Create namespace and base resources
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmaps.yaml
kubectl apply -f k8s/persistent-volumes.yaml

# 2. Deploy applications
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/deployments.yaml
kubectl apply -f k8s/services.yaml

# 3. Enable autoscaling
kubectl apply -f k8s/autoscaling.yaml

# 4. (Optional) Setup networking and monitoring
kubectl apply -f k8s/network-policies.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/monitoring.yaml
```

### Verify Deployment

```bash
# Check namespace
kubectl get ns vision-system

# Check pods
kubectl get pods -n vision-system
kubectl get pods -n vision-system -o wide

# Check services
kubectl get svc -n vision-system

# Check PVCs
kubectl get pvc -n vision-system

# Check HPA status
kubectl get hpa -n vision-system
kubectl describe hpa yolo-hpa -n vision-system

# Monitor logs
kubectl logs -n vision-system -l app=yolo -f
kubectl logs -n vision-system -l app=logging -f

# Check resource usage
kubectl top nodes
kubectl top pods -n vision-system
```

## Configuration

### Update Environment Variables

Edit `configmaps.yaml`:

```yaml
data:
  LOG_LEVEL: "DEBUG"  # Change log level
  MODEL_PATH: "yolov8m.pt"  # Use larger model
  MLFLOW_TRACKING_URI: "http://mlflow-service:5000"
```

Apply changes:

```bash
kubectl apply -f k8s/configmaps.yaml
# Restart pods to pick up new config
kubectl rollout restart deployment/yolo-inference -n vision-system
kubectl rollout restart deployment/logging-service -n vision-system
```

### Update Database Credentials

```bash
# Edit secret
kubectl edit secret db-credentials -n vision-system

# Or update from file
kubectl create secret generic db-credentials \
  --from-literal=DATABASE_URL="postgresql://..." \
  -n vision-system --dry-run=client -o yaml | kubectl apply -f -
```

### Scale Services Manually

```bash
# Scale YOLO to 4 replicas
kubectl scale deployment yolo-inference --replicas=4 -n vision-system

# Scale Logging to 3 replicas
kubectl scale deployment logging-service --replicas=3 -n vision-system
```

## Autoscaling

HPA automatically scales based on CPU/memory/GPU metrics:

```bash
# Monitor HPA
kubectl get hpa -n vision-system -w

# Check current metrics
kubectl get --raw /apis/custom.metrics.k8s.io/v1beta1/namespaces/vision-system/pods/*/cpu_usage
```

### HPA Scaling Policies

**YOLO Service:**
- Min replicas: 2, Max replicas: 4
- CPU threshold: 70%, Memory: 80%, GPU: 75%
- Scale up: 100% increase or 2 pods per 30s
- Scale down: 50% reduction per 60s (after 5min stability)

**Logging Service:**
- Min replicas: 2, Max replicas: 5
- CPU threshold: 75%, Memory: 85%
- Scale up: 100% increase per 30s
- Scale down: 50% reduction per 60s (after 5min stability)

## Networking

### Service Discovery

Services are accessible within the cluster:

```bash
# From any pod in vision-system namespace
curl http://yolo-service:8000/health
curl http://logging-service:8001/health

# From other namespaces
curl http://yolo-service.vision-system:8000/health
```

### External Access

- **LoadBalancer**: `yolo-service` exposes port 8000 externally
- **ClusterIP**: `logging-service` is internal-only (accessed via YOLO)
- **Ingress**: Optional HTTPS endpoints (requires NGINX Ingress Controller)

## Monitoring

### Prometheus Metrics

Services expose `/metrics` endpoints (Prometheus format):

```bash
# Query metrics
kubectl port-forward -n vision-system svc/yolo-service 8000:8000
curl http://localhost:8000/metrics

kubectl port-forward -n vision-system svc/logging-service 8001:8001
curl http://localhost:8001/metrics
```

### Alerts

Configured alerts (in `monitoring.yaml`):
- High CPU/Memory in YOLO
- Logging service down
- High error rates
- Pod restart storms
- PVC capacity warnings

## Troubleshooting

### Pod won't start

```bash
# Check pod status
kubectl describe pod yolo-inference-xxx -n vision-system

# Check logs
kubectl logs yolo-inference-xxx -n vision-system --previous

# Check resource availability
kubectl describe nodes | grep -A 5 Allocated
```

### GPU not detected

```bash
# Verify GPU availability
kubectl get nodes -o json | jq '.items[] | {name: .metadata.name, gpu: .status.allocatable}'

# Check GPU node selector
kubectl get pod yolo-inference-xxx -n vision-system -o yaml | grep -i gpu
```

### PVC pending

```bash
# Check PVC status
kubectl describe pvc logging-data-pvc -n vision-system

# Check available StorageClasses
kubectl get storageclass

# Change StorageClass in persistent-volumes.yaml if needed
```

### High memory usage

```bash
# Check memory stats
kubectl top pods -n vision-system --containers

# Adjust resource limits in deployments.yaml
# Example: Change memory.limits from 8Gi to 6Gi
```

## Production Considerations

### Database Upgrade (SQLite → PostgreSQL)

For multi-replica deployments, upgrade to PostgreSQL:

```bash
# 1. Deploy PostgreSQL
kubectl apply -f - <<EOF
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: vision-system
spec:
  selector:
    app: postgres
  ports:
    - port: 5432
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: vision-system
spec:
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:15-alpine
          env:
            - name: POSTGRES_DB
              value: vision_logs
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db-credentials
                  key: POSTGRES_PASSWORD
          volumeMounts:
            - name: postgres-data
              mountPath: /var/lib/postgresql/data
      volumes:
        - name: postgres-data
          emptyDir: {}
EOF

# 2. Update secret and deployment
kubectl edit secret db-credentials -n vision-system
# Change DATABASE_URL to: postgresql://vision_user:password@postgres:5432/vision_logs

kubectl rollout restart deployment/logging-service -n vision-system
```

### TLS/SSL Setup

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: nginx
EOF

# Apply ingress.yaml for HTTPS
kubectl apply -f k8s/ingress.yaml
```

## Cleanup

```bash
# Delete deployments
kubectl delete deployment -n vision-system --all

# Delete namespace (removes all resources)
kubectl delete namespace vision-system

# Delete volumes (if using local storage)
kubectl delete pvc --all -n vision-system
```

## Support

For issues with Kubernetes deployment:
1. Check pod logs: `kubectl logs <pod-name> -n vision-system`
2. Describe pod: `kubectl describe pod <pod-name> -n vision-system`
3. Check events: `kubectl get events -n vision-system --sort-by='.lastTimestamp'`
4. Review resource usage: `kubectl top pods -n vision-system`
