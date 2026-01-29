# CI/CD Workflow: Visual Quick Reference

## What You Get (At a Glance)

```
┌──────────────────────────────────────────────────────────────────┐
│  Complete CI/CD System for ML Model Deployment                   │
│  - Fully Automated                                               │
│  - Production-Ready                                              │
│  - Zero-Downtime Deployments                                    │
│  - Automatic Rollback on Failure                                │
│  - High Availability (3-10 replicas)                            │
└──────────────────────────────────────────────────────────────────┘

Files Provided:
├── Workflows/Pipelines
│   ├── .github/workflows/deploy-on-model-promotion.yml (GitHub Actions)
│   └── azure-pipelines.yml (Azure DevOps)
│
├── Scripts
│   ├── scripts/extract_model_info.py
│   └── scripts/mlflow_webhook_handler.py (optional)
│
├── Infrastructure
│   └── k8s/deployment-production.yaml (Kubernetes)
│
└── Documentation
    ├── docs/CICD_QUICK_START.md (← START HERE - 10 min)
    ├── docs/CICD_WORKFLOW_GUIDE.md (Complete reference)
    ├── docs/CICD_IMPLEMENTATION_CHECKLIST.md (Step-by-step)
    ├── docs/CICD_DIAGRAMS.md (Architecture)
    ├── docs/CICD_IMPLEMENTATION_SUMMARY.md (Overview)
    └── docs/CICD_INDEX.md (This index)
```

## Timeline: From Promotion to Production

```
MINUTE 0:00 → Model promoted in MLflow
             ↓
MINUTE 0:02 → Webhook received by GitHub/Azure DevOps
             ↓
MINUTE 0:05 → Workflow/Pipeline started
             ├─ Extract model info from MLflow
             ├─ Validate model is ready
             └─ Display summary
             ↓
MINUTE 1:00 → Docker image built & cached
             └─ Pushed to Azure Container Registry
             ↓
MINUTE 2:00 → AKS deployment starts rolling update
             ├─ Old pods: Running image v1
             ├─ New pods: Pulling image v2
             └─ Service routes traffic to both
             ↓
MINUTE 2:30 → All pods rolled and healthy
             ├─ Health checks: ✓ Passing
             ├─ Ready checks: ✓ All pods
             └─ Service fully switched
             ↓
MINUTE 3:00 → Test predictions verify success
             ├─ 5 sample predictions: ✓ Passed
             └─ Deployment complete: ✓ Success
             ↓
MINUTE 3:30 → Team notified of successful deployment
             └─ Model live in production ✓
```

## Platform Comparison

```
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Actions vs Azure DevOps               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  GITHUB ACTIONS                    AZURE DEVOPS                 │
│  ├─ Workflow file: YAML            ├─ Pipeline file: YAML       │
│  ├─ Trigger: Webhook dispatch      ├─ Trigger: Pipeline queue   │
│  ├─ Jobs run in parallel           ├─ Stages run in sequence    │
│  ├─ Matrix builds (multi-config)   ├─ Parameters + variables    │
│  ├─ Logging: Clear & detailed      ├─ Logging: Configurable     │
│  ├─ Secrets: Repository level      ├─ Secrets: Variable groups  │
│  ├─ Free tier: ∞ minutes/month     ├─ Free tier: 1800 min/month │
│  ├─ Best for: OSS, startups        ├─ Best for: Enterprise      │
│  └─ Simplicity: ⭐⭐⭐⭐⭐          └─ Power: ⭐⭐⭐⭐⭐         │
│                                                                  │
│  CHOOSE IF:                        CHOOSE IF:                   │
│  → You use GitHub                  → You're on Azure stack      │
│  → You want simplicity             → You want advanced features │
│  → You like configuration as code  → You have Azure governance  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Deployment Stages

```
STAGE 1: VALIDATE
┌─────────────────────────────────────┐
│ ✓ Connect to MLflow                │
│ ✓ Get latest Production model      │
│ ✓ Verify model is READY            │
│ ✓ Extract version & timestamp      │
└─────────────────────────────────────┘
         Time: 2-3 seconds
         Can Fail: Yes (→ Abort)

STAGE 2: BUILD
┌─────────────────────────────────────┐
│ ✓ Checkout code (Dockerfile)        │
│ ✓ Docker Buildx setup               │
│ ✓ Build image with layers cache    │
│ ✓ Tag with model version           │
└─────────────────────────────────────┘
         Time: 30-60 seconds
         Can Fail: Yes (→ Abort)

STAGE 3: PUSH
┌─────────────────────────────────────┐
│ ✓ Authenticate to ACR               │
│ ✓ Push image + tags                 │
│ ✓ Verify checksums                  │
│ ✓ Store metadata                    │
└─────────────────────────────────────┘
         Time: 10-30 seconds
         Can Fail: Yes (→ Abort)

STAGE 4: DEPLOY
┌─────────────────────────────────────┐
│ ✓ Get AKS credentials              │
│ ✓ kubectl set image                │
│ ✓ kubectl set env                  │
│ ✓ kubectl rollout wait             │
└─────────────────────────────────────┘
         Time: 1-2 minutes
         Can Fail: Yes (→ Rollback)

STAGE 5: VERIFY
┌─────────────────────────────────────┐
│ ✓ Health checks (30 retries)        │
│ ✓ Readiness verification            │
│ ✓ Test predictions (5 samples)      │
│ ✓ Confirm all pods ready            │
└─────────────────────────────────────┘
         Time: 20-30 seconds
         Can Fail: Yes (→ Rollback)

TOTAL TIME: 3-5 minutes typical
```

## Kubernetes Pod Lifecycle During Deployment

```
OLD POD (v1)                    NEW POD (v2)
Running ✓                       Pending...
Ready ✓                         ContainerCreating...
Serving traffic                 Pulling image...
                               → 30s: Loading model
                               → Startup probe failing (expected)
                               
Draining traffic slowly...      Container ready ✓
Readiness probe fails           → Startup probe passes
                               → Readiness probe passes
                               → Ready ✓
Waiting for graceful close      
(terminationGracePeriod: 30s)   Serving traffic
                               ↓
Terminating...                  Running ✓
                               Ready ✓
                               Fully operational

Result: Zero downtime ✓
```

## Health Check Pattern

```
REQUEST FLOW:
User → Load Balancer → Service → Pod (Only if Ready)
                                  ↓
                            Container Running?
                                  ↓ Yes
                            GET /ready
                                  ↓ 200 OK
                            GET /metrics
                                  ↓
                            GET /predict
                                  ↓ Response

FAILURE HANDLING:
User → Service → Pod-1 (Ready: ✓)
                 Pod-2 (Ready: ✓)
                 Pod-3 (Ready: ✗ → Skip)
                 Pod-4 (Ready: ✓)

PROBE TYPES:
1. startupProbe (150s max)
   Waits for app to start (model loading)
   
2. livenessProbe (restart if fails)
   Checks if container is alive
   
3. readinessProbe (only route traffic here)
   Checks if ready to serve requests
```

## Scaling in Action

```
LOAD PATTERN:
Requests/sec
    │     ┏━━━━┓
    │    ┃      ┃
30  │   ┃        ┃
    │  ┃          ┃
20  │ ┃            ┃   ┏━━━━┓
    │                 ┃    ┃
10  │                ┃      ┃
    │               ┃        ┃
 0  │______________┃__________┃___time
    0              5    10     15

POD COUNT RESPONSE:
Pods
    │     ┏━━━━┓
    │    ┃      ┃
10  │   ┃        ┃
    │  ┃          ┃
 8  │ ┃            ┃   ┏━━━━┓
    │                 ┃    ┃
 5  │                ┃      ┃
    │               ┃        ┃
 3  │______________┃__________┃___time
    0              5    10     15

SCALE UP:   70% CPU → add pods (100% per cycle)
SCALE DOWN: 30% CPU → remove 50% of pods (after 5min stable)
MIN: 3 pods | MAX: 10 pods
```

## Failure & Recovery

```
SCENARIO: Image Pull Failed
└─ Action: Automatic rollback triggered
   └─ kubectl rollout undo deployment/inference-service
   └─ Back to previous version in < 30 seconds
   └─ Team notified immediately

SCENARIO: Health Check Failed
└─ Action: Automatic rollback triggered
   └─ Pod did not pass readiness
   └─ Service doesn't route traffic
   └─ Rollback to previous working version
   └─ Manual investigation required

SCENARIO: Prediction Test Failed
└─ Action: Automatic rollback triggered
   └─ New model not producing valid outputs
   └─ Revert to previous model
   └─ Team notified with error details
   └─ Investigate new model before retry

SCENARIO: Partial Deployment Failed
└─ Action: Automatic rollback triggered
   └─ Some pods rolled, some failed
   └─ kubectl rollout undo handles mismatch
   └─ Back to consistent previous state
```

## Configuration Checklist (Simple)

```
SECRETS TO CREATE (GitHub Actions):
☐ ACR_LOGIN_SERVER         = myregistry.azurecr.io
☐ ACR_USERNAME              = your-username
☐ ACR_PASSWORD              = your-password
☐ AKS_CLUSTER_NAME          = my-cluster
☐ AKS_RESOURCE_GROUP        = my-group
☐ MLFLOW_TRACKING_URI       = http://mlflow.com:5000
☐ AZURE_SUBSCRIPTION_ID     = 12345...
☐ AZURE_TENANT_ID           = 67890...
☐ AZURE_CLIENT_ID           = abcde...

CONNECTIONS TO CREATE (Azure DevOps):
☐ acr-service-connection    (Docker Registry)
☐ azure-subscription        (Azure Resource Manager)
☐ aks-connection           (Kubernetes)

KUBERNETES APPLY:
☐ kubectl apply -f k8s/deployment-production.yaml

MLFLOW WEBHOOK:
☐ Configure webhook in MLflow Admin panel
☐ URL: https://api.github.com/repos/ORG/REPO/dispatches
☐ Add GitHub token to headers
☐ Test webhook

READY TO GO: All checked → Test deployment!
```

## Success Indicators

```
✓ WORKFLOW/PIPELINE STARTS
  └─ Check: GitHub Actions / Azure DevOps shows job running

✓ MODEL VALIDATED
  └─ Check: "Model validation passed" in logs

✓ IMAGE BUILT
  └─ Check: "Docker image built" and "Image tag: ..."

✓ IMAGE PUSHED
  └─ Check: "Pushed to ACR" and image visible in registry

✓ DEPLOYMENT STARTED
  └─ Check: kubectl shows new replicaset created

✓ PODS ROLLING
  └─ Check: Old pods terminating, new pods starting

✓ PODS HEALTHY
  └─ Check: All pods "Running" and "Ready"

✓ HEALTH CHECKS PASS
  └─ Check: "Health check passed" in logs

✓ TESTS PASS
  └─ Check: "Prediction tests successful" in logs

✓ DEPLOYMENT COMPLETE
  └─ Check: All pods on new image version

MODEL LIVE IN PRODUCTION ✓✓✓
```

## File Quick Reference

```
TO UNDERSTAND                      READ THIS
─────────────────────────────────────────────────────
What is this package?              CICD_INDEX.md
Getting started (10 min)?          CICD_QUICK_START.md
Setting up (step-by-step)?         CICD_IMPLEMENTATION_CHECKLIST.md
Full documentation?                CICD_WORKFLOW_GUIDE.md
Architecture diagrams?             CICD_DIAGRAMS.md
Executive summary?                 CICD_IMPLEMENTATION_SUMMARY.md
```

## Common Commands

```bash
# Test if everything is working
kubectl get deployment inference-service -n production
kubectl get pods -n production -l app=inference-service
kubectl logs -n production -l app=inference-service

# Port-forward to test health endpoint
kubectl port-forward svc/inference-service 8000:8000 -n production &
curl http://localhost:8000/health

# Watch deployment progress
watch kubectl get deployment inference-service -n production

# Check rollout history
kubectl rollout history deployment/inference-service -n production

# Manual rollback if needed
kubectl rollout undo deployment/inference-service -n production

# Scale up/down (emergency only)
kubectl scale deployment inference-service --replicas=5 -n production
```

## What's Automated

```
HUMAN ACTION                    AUTOMATED PIPELINE
─────────────────────────────────────────────────────
1. Promote model to             2. Webhook sent
   Production (MLflow)             ↓
                                3. Extract model info
                                   ↓
                                4. Validate model
                                   ↓
                                5. Build Docker image
                                   ↓
                                6. Push to ACR
                                   ↓
                                7. Patch AKS deployment
                                   ↓
                                8. Wait for rollout
                                   ↓
                                9. Health checks
                                   ↓
                                10. Test predictions
                                    ↓
                                11. Success notification
                                    ↓
                        [Model live in production]
```

## Performance Baseline

```
TYPICAL TIMES:
Validation:        2-3 seconds
Docker build:      30-60 seconds (first), 5-10 seconds (cached)
Push to ACR:       10-30 seconds
AKS rollout:       1-2 minutes
Health checks:     10-20 seconds
Tests:             5-10 seconds
─────────────────────────────────
TOTAL:             3-5 minutes

BOTTLENECKS:
1. First Docker build (no cache)    → Use cache layer
2. Large image push (if slow net)   → Optimize Dockerfile
3. Long model loading               → Increase startupProbe.failureThreshold
4. Many pods scaling                → Adjust HPA targetAverageUtilization
```

## Next Steps (In Order)

```
1. READ QUICK START      → docs/CICD_QUICK_START.md (10 min)
   Learn the basics

2. RUN CHECKLIST        → docs/CICD_IMPLEMENTATION_CHECKLIST.md (30 min)
   Set up your environment

3. TEST MANUAL          → GitHub/Azure UI (5 min)
   Trigger a test deployment

4. PROMOTE MODEL        → MLflow (1 min)
   See auto-deployment work

5. MONITOR FIRST RUN    → Logs & dashboard (5 min)
   Watch it deploy

6. CELEBRATE            → 🎉
   Model live in production!
```

---

**STATUS**: ✅ PRODUCTION READY  
**SETUP TIME**: 10-45 minutes  
**FIRST DEPLOYMENT**: 3-5 minutes  
**MAINTENANCE**: ~5 minutes/deployment  

**START HERE**: [docs/CICD_QUICK_START.md](docs/CICD_QUICK_START.md)
