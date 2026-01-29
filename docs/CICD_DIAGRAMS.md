# CI/CD Workflow: Visual Diagrams & Architecture

## Overall Workflow Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                          MLflow Model Registry                          │
│                       (Version Control System)                          │
│                                                                          │
│    Data Scientist trains model → Registers in MLflow → Stages           │
│                                                          │               │
│                                                    ┌─────▼─────┐        │
│                                                    │  Staging  │        │
│                                                    │  (Testing)│        │
│                                                    └─────┬─────┘        │
│                                                          │               │
│                                     Data Scientist      │               │
│                                     Approves Model      │               │
│                                                    ┌─────▼─────┐        │
│                                                    │Production │        │
│                                                    │ (READY)   │        │
│                                                    └─────┬─────┘        │
│                                                          │               │
└──────────────────────────────────────────────────────────┼───────────────┘
                                                           │
                                  ┌────────────────────────▼──────────────┐
                                  │   MLflow Webhook Event Fired          │
                                  │   (Model Transition to Production)    │
                                  └────────────────────────┬───────────────┘
                                                           │
                                  ┌────────────────────────▼──────────────┐
                                  │    GitHub Actions / Azure DevOps      │
                                  │      CI/CD Platform Triggered         │
                                  └────────────────────────┬───────────────┘
                                                           │
        ┌──────────────────┬──────────────────┬───────────┴────────┬────────────┐
        │                  │                  │                    │            │
    ┌───▼──┐          ┌───▼──┐          ┌───▼──┐            ┌───▼──┐      ┌───▼──┐
    │Extract│          │Validate          │ Build           │ Push  │      │Deploy │
    │ Model │          │ Model            │ Image           │ Image │      │ to AKS│
    │ Info  │          │                  │                 │       │      │       │
    └────┬──┘          └───┬──┘          └───┬──┘            └───┬──┘      └───┬──┘
         │                 │                 │                  │             │
         └─────────────────┴─────────────────┴──────────────────┴─────────────┘
                                           │
                          ┌────────────────▼──────────────┐
                          │   Health Checks & Tests       │
                          │   (30 attempts, 3s intervals) │
                          └────────────┬───────────────────┘
                                       │
                    ┌──────────────────┴────────────────────┐
                    │                                       │
                ┌───▼──┐                               ┌───▼──┐
                │SUCCESS                               │FAILURE
                │ Model                                │
                │ Live                                 │ Rollback
                │ in Prod                              │ Previous
                └─────┘                                │ Version
                                                       └────┘
```

## GitHub Actions Workflow Pipeline

```
┌────────────────────────────────────────────────────────────────────────┐
│                   GitHub Actions Workflow Graph                        │
└────────────────────────────────────────────────────────────────────────┘

STAGE 1: EXTRACT & VALIDATE
┌─────────────────────────────────────┐
│  extract-model-info                 │
│  ├─ Checkout code                   │
│  ├─ Install Python & MLflow         │
│  ├─ Extract model from webhook      │
│  └─ Set output variables            │
│      (model_name, version, tag)     │
└──────────────┬──────────────────────┘
               │
     ┌─────────▼─────────┐
     │ validate-model    │
     │ ├─ Install MLflow │
     │ └─ Check model    │
     │    in Production  │
     │    stage          │
     └──────────┬────────┘
                │
STAGE 2: BUILD & PUSH IMAGE
                │
     ┌──────────▼─────────────┐
     │ build-and-push-image   │
     │ ├─ Docker Buildx setup │
     │ ├─ Login to ACR        │
     │ ├─ Build image         │
     │ │ (with cache)         │
     │ └─ Push to ACR         │
     └──────────┬─────────────┘
                │
STAGE 3: DEPLOY TO AKS
                │
     ┌──────────▼─────────────┐
     │ deploy-to-aks         │
     │ ├─ Get AKS creds      │
     │ ├─ Verify deployment  │
     │ ├─ Update image       │
     │ ├─ Update env vars    │
     │ ├─ Wait for rollout   │
     │ ├─ Wait pod ready     │
     │ ├─ Health checks      │
     │ └─ Verify endpoint    │
     └──────────┬─────────────┘
                │
STAGE 4: TEST
                │
     ┌──────────▼──────────────┐
     │ test-deployed-model    │
     │ ├─ Setup kubectl       │
     │ ├─ Port-forward svc    │
     │ └─ Run predictions     │
     │    (5 samples)         │
     └──────────┬──────────────┘
                │
STAGE 5: NOTIFY
                │
      ┌─────────┴─────────┐
      │                   │
  ┌───▼──┐            ┌───▼──┐
  │SUCCESS            │FAILURE
  │Notify             │Rollback
  │  Success          │+ Notify
  └──────┘            └────┘

TIME: ~3-5 minutes
PARALLEL JOBS: extract-model-info → validate-model + build-image → deploy-to-aks → test → notify
```

## Kubernetes Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          AKS Cluster                                    │
│                     (Production Namespace)                              │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │                    Service (LoadBalancer)                     │    │
│  │              Port 80/443 → Pod Port 8000                      │    │
│  │                                                               │    │
│  │  External Access: http://SERVICE_IP/predict                  │    │
│  └─────────────┬─────────────────────────────────────────────────┘    │
│                │                                                      │
│  ┌─────────────┴─────────────────────────────────────────────────┐   │
│  │           Deployment (inference-service)                      │   │
│  │           Strategy: RollingUpdate                             │   │
│  │           maxSurge: 1, maxUnavailable: 0                      │   │
│  │                                                               │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │   │
│  │  │  Pod 1   │  │  Pod 2   │  │  Pod 3   │  ... up to 10     │   │
│  │  │ (Ready)  │  │ (Ready)  │  │ (Ready)  │                   │   │
│  │  │          │  │          │  │          │                   │   │
│  │  │┌────────┐│  │┌────────┐│  │┌────────┐│                   │   │
│  │  ││Container││  ││Container││  ││Container││                   │   │
│  │  ││ Image   ││  ││ Image   ││  ││ Image   ││                   │   │
│  │  ││:latest ││  ││:latest ││  ││:latest ││                   │   │
│  │  │└────────┘│  │└────────┘│  │└────────┘│                   │   │
│  │  │          │  │          │  │          │                   │   │
│  │  │ Probes:  │  │ Probes:  │  │ Probes:  │                   │   │
│  │  │ ✓Startup │  │ ✓Startup │  │ ✓Startup │                   │   │
│  │  │ ✓Live    │  │ ✓Live    │  │ ✓Live    │                   │   │
│  │  │ ✓Ready   │  │ ✓Ready   │  │ ✓Ready   │                   │   │
│  │  │          │  │          │  │          │                   │   │
│  │  │ Requests │  │ Requests │  │ Requests │                   │   │
│  │  │ CPU: 500m│  │ CPU: 500m│  │ CPU: 500m│                   │   │
│  │  │ Mem: 512M│  │ Mem: 512M│  │ Mem: 512M│                   │   │
│  │  │          │  │          │  │          │                   │   │
│  │  │ Limits:  │  │ Limits:  │  │ Limits:  │                   │   │
│  │  │ CPU: 2000│  │ CPU: 2000│  │ CPU: 2000│                   │   │
│  │  │ Mem: 2Gi │  │ Mem: 2Gi │  │ Mem: 2Gi │                   │   │
│  │  │          │  │          │  │          │                   │   │
│  │  │ Env Vars:│  │ Env Vars:│  │ Env Vars:│                   │   │
│  │  │ MODEL_*  │  │ MODEL_*  │  │ MODEL_*  │                   │   │
│  │  │ MLFLOW_* │  │ MLFLOW_* │  │ MLFLOW_* │                   │   │
│  │  │ LOG_LVL  │  │ LOG_LVL  │  │ LOG_LVL  │                   │   │
│  │  │          │  │          │  │          │                   │   │
│  │  │ Volumes: │  │ Volumes: │  │ Volumes: │                   │   │
│  │  │ emptyDir │  │ emptyDir │  │ emptyDir │                   │   │
│  │  └──────────┘  └──────────┘  └──────────┘                   │   │
│  │                                                               │   │
│  │  HPA (HorizontalPodAutoscaler)                              │   │
│  │  ├─ Min: 3 pods                                             │   │
│  │  ├─ Max: 10 pods                                            │   │
│  │  ├─ Scale on CPU > 70%                                      │   │
│  │  └─ Scale on Memory > 80%                                   │   │
│  │                                                               │   │
│  │  PDB (PodDisruptionBudget)                                  │   │
│  │  └─ Keep minimum 2 pods running                             │   │
│  │                                                               │   │
│  │  Pod Anti-Affinity                                          │   │
│  │  └─ Spread pods across different nodes                      │   │
│  │                                                               │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │              ConfigMap (inference-config)                     │   │
│  │  ├─ MLFLOW_TRACKING_URI                                      │   │
│  │  ├─ MODEL_STAGE: "Production"                                │   │
│  │  ├─ LOG_LEVEL: "INFO"                                        │   │
│  │  ├─ PORT: "8000"                                             │   │
│  │  └─ WORKERS: "4"                                             │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │                Secret (inference-secrets)                     │   │
│  │  └─ MLFLOW_REGISTRY_URI (encrypted)                          │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │              NetworkPolicy (inference-service-policy)         │   │
│  │  Ingress: Allow from ingress-nginx, same namespace           │   │
│  │  Egress:  Allow to MLflow, DNS, external registries          │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │            ServiceMonitor (for Prometheus metrics)            │   │
│  │  Scrapes: /metrics endpoint every 30 seconds                 │   │
│  │  Labels:  release=prometheus                                 │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

## Probe Lifecycle

```
Pod Start
   │
   ├─ Init Container: check-mlflow
   │  └─ Wait for MLflow service
   │
   ├─ Container Start: inference-service
   │  │
   │  ├─ startupProbe (allows 150s max)
   │  │  GET /health
   │  │  Retry: Every 5s, up to 30 times
   │  │  Purpose: Wait for model to load
   │  │
   │  ├─ ✓ Startup successful
   │  │
   │  ├─ livenessProbe (every 10s after 30s)
   │  │  GET /health
   │  │  Timeout: 5s
   │  │  Failure threshold: 3
   │  │  Purpose: Restart if dead
   │  │
   │  ├─ readinessProbe (every 5s after 10s)
   │  │  GET /ready
   │  │  Timeout: 3s
   │  │  Failure threshold: 2
   │  │  Purpose: Route traffic only when ready
   │  │
   │  ├─ ✓ All probes passing
   │  │
   │  └─ Container Ready for Traffic
   │     (Service routes requests here)
   │
   └─ Pod Termination
      (terminationGracePeriodSeconds: 30s to cleanup)
      │
      └─ Container shutdown
```

## Rolling Update Sequence

```
OLD STATE:
┌─────────────────────────────────────────┐
│ Deployment (replica count: 3)           │
├─────────────────────────────────────────┤
│ Pod-1: image:v1  ├─ ✓ Ready             │
│ Pod-2: image:v1  ├─ ✓ Ready             │
│ Pod-3: image:v1  ├─ ✓ Ready             │
└─────────────────────────────────────────┘

STEP 1: maxSurge=1 (create new pod)
┌─────────────────────────────────────────┐
│ Deployment (4 pods temporarily)         │
├─────────────────────────────────────────┤
│ Pod-1: image:v1  ├─ ✓ Ready             │
│ Pod-2: image:v1  ├─ ✓ Ready             │
│ Pod-3: image:v1  ├─ ✓ Ready             │
│ Pod-4: image:v2  ├─ ⏳ Starting         │
└─────────────────────────────────────────┘

STEP 2: Pod-4 becomes ready
┌─────────────────────────────────────────┐
│ Deployment (4 pods temporarily)         │
├─────────────────────────────────────────┤
│ Pod-1: image:v1  ├─ ✓ Ready             │
│ Pod-2: image:v1  ├─ ✓ Ready             │
│ Pod-3: image:v1  ├─ ✓ Ready             │
│ Pod-4: image:v2  ├─ ✓ Ready ← NEW      │
└─────────────────────────────────────────┘

STEP 3: Terminate old pod
┌─────────────────────────────────────────┐
│ Deployment (3 pods)                     │
├─────────────────────────────────────────┤
│ Pod-2: image:v1  ├─ ✓ Ready             │
│ Pod-3: image:v1  ├─ ✓ Ready             │
│ Pod-4: image:v2  ├─ ✓ Ready ← NEW      │
└─────────────────────────────────────────┘

STEP 4: Create new pod
┌─────────────────────────────────────────┐
│ Deployment (4 pods temporarily)         │
├─────────────────────────────────────────┤
│ Pod-2: image:v1  ├─ ✓ Ready             │
│ Pod-3: image:v1  ├─ ✓ Ready             │
│ Pod-4: image:v2  ├─ ✓ Ready             │
│ Pod-5: image:v2  ├─ ⏳ Starting         │
└─────────────────────────────────────────┘

STEP 5: Pod-5 becomes ready
┌─────────────────────────────────────────┐
│ Deployment (4 pods temporarily)         │
├─────────────────────────────────────────┤
│ Pod-2: image:v1  ├─ ✓ Ready             │
│ Pod-3: image:v1  ├─ ✓ Ready             │
│ Pod-4: image:v2  ├─ ✓ Ready             │
│ Pod-5: image:v2  ├─ ✓ Ready ← NEW      │
└─────────────────────────────────────────┘

STEP 6: Terminate old pod
┌─────────────────────────────────────────┐
│ Deployment (3 pods)                     │
├─────────────────────────────────────────┤
│ Pod-3: image:v1  ├─ ✓ Ready             │
│ Pod-4: image:v2  ├─ ✓ Ready             │
│ Pod-5: image:v2  ├─ ✓ Ready ← NEW      │
└─────────────────────────────────────────┘

STEP 7: Create final new pod
┌─────────────────────────────────────────┐
│ Deployment (4 pods temporarily)         │
├─────────────────────────────────────────┤
│ Pod-3: image:v1  ├─ ✓ Ready             │
│ Pod-4: image:v2  ├─ ✓ Ready             │
│ Pod-5: image:v2  ├─ ✓ Ready             │
│ Pod-6: image:v2  ├─ ⏳ Starting         │
└─────────────────────────────────────────┘

FINAL STATE:
┌─────────────────────────────────────────┐
│ Deployment (replica count: 3)           │
├─────────────────────────────────────────┤
│ Pod-4: image:v2  ├─ ✓ Ready             │
│ Pod-5: image:v2  ├─ ✓ Ready             │
│ Pod-6: image:v2  ├─ ✓ Ready             │
└─────────────────────────────────────────┘

Key: maxSurge=1 means 1 extra pod allowed during update
     maxUnavailable=0 means ALL pods must stay ready (zero downtime)
     Typical duration: 1-3 minutes for 3 pods
```

## Auto-Scaling Behavior

```
Normal State (3 replicas)
  3 pods ✓ Ready
  CPU: 40% | Memory: 50%

Load Increases
  CPU → 75% (crosses 70% threshold)
  ↓
  Scale UP: Add 1 pod (Percent: 100%)
  ↓
  4 pods ✓ Ready
  CPU: 60% (normalized)

More Load
  CPU → 80%
  ↓
  Scale UP: Add 1 more pod
  ↓
  5 pods ✓ Ready
  CPU: 65%

Load Decreases
  CPU → 50% (below 70%)
  No immediate scale down (stabilization window: 300s)
  ↓
  After 5 minutes stable:
  ↓
  Scale DOWN: Remove 50% (2 pods)
  ↓
  3 pods ✓ Ready
  CPU: 65%

Max Capacity (10 pods reached)
  CPU: 70%
  Memory: 85%
  ↓
  Cannot scale further
  ↓
  Alert: Check if replicas insufficient
```

---

**Visual Guide**: Use these diagrams to understand the CI/CD workflow  
**Status**: ✅ Complete & Ready for Reference  
**Last Updated**: January 28, 2026
