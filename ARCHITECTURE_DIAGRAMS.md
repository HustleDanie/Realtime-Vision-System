# Health Check Architecture

## System Architecture with Health Probes

```
┌─────────────────────────────────────────────────────────────────┐
│                     KUBERNETES CLUSTER (AKS)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────┐      ┌──────────────────────────┐  │
│  │   Inference Pod (8000)   │      │   Logging Pod (8001)     │  │
│  ├──────────────────────────┤      ├──────────────────────────┤  │
│  │  ┌────────────────────┐  │      │  ┌────────────────────┐  │  │
│  │  │  FastAPI Service   │  │      │  │  FastAPI Service   │  │  │
│  │  └────────────────────┘  │      │  └────────────────────┘  │  │
│  │         ▲                 │      │         ▲                 │  │
│  │         │                 │      │         │                 │  │
│  │  ┌──────┴──────────┐      │      │  ┌──────┴──────────┐      │  │
│  │  │  State Tracking │      │      │  │  State Tracking │      │  │
│  │  ├──────────────────┤     │      │  ├──────────────────┤     │  │
│  │  │ model_loaded    │     │      │  │ db_initialized  │     │  │
│  │  │ prediction_cnt  │     │      │  │ prediction_cnt  │     │  │
│  │  │ error_count     │     │      │  │ defect_count    │     │  │
│  │  │ startup_time    │     │      │  │ error_count     │     │  │
│  │  └──────────────────┘     │      │  └──────────────────┘     │  │
│  │         ▲                 │      │         ▲                 │  │
│  │         └─────────────────┼──────┘         │                 │  │
│  │                           │                 │                 │  │
│  │  Health Endpoints:        │      Health Endpoints:           │  │
│  │  • /health ────────────────│─────→ • /health                 │  │
│  │  • /ready  ────────────────│─────→ • /ready                  │  │
│  │  • /metrics                │      • /metrics                 │  │
│  └─────────────┬──────────────┘      └──────────────────────────┘  │
│                │                                                    │
│                └────────────────────────────────────────────────┐   │
│                                                                 │   │
│  ┌─────────────────────────────────────────────────────────────┴┐  │
│  │                  KUBERNETES CONTROL PLANE                    │  │
│  ├────────────────────────────────────────────────────────────┐ │  │
│  │  Probe Manager                                             │ │  │
│  ├────────────────────────────────────────────────────────────┤ │  │
│  │                                                            │ │  │
│  │  Startup Probe (0-150s):                                 │ │  │
│  │  └─ calls /health every 5 seconds                         │ │  │
│  │     └─ waits for model to load                            │ │  │
│  │                                                            │ │  │
│  │  Liveness Probe (every 10s after 30s delay):             │ │  │
│  │  └─ calls /health                                         │ │  │
│  │     └─ restarts pod if 3 consecutive failures             │ │  │
│  │        (fail for 30 seconds)                              │ │  │
│  │                                                            │ │  │
│  │  Readiness Probe (every 5s after 10s delay):             │ │  │
│  │  └─ calls /ready                                          │ │  │
│  │     └─ removes from service if 2 consecutive failures      │ │  │
│  │        (fail for 10 seconds)                              │ │  │
│  │     └─ re-adds when /ready returns 200 OK                │ │  │
│  │                                                            │ │  │
│  └────────────────────────────────────────────────────────────┘ │  │
│                                                                   │  │
└─────────────────────────────────────────────────────────────────┘  │
                                                                      │
           ┌──────────────────────────────────────────────────┐      │
           │          EXTERNAL MONITORING STACK               │      │
           ├──────────────────────────────────────────────────┤      │
           │  ┌─────────────────────────────────────────┐    │      │
           │  │  Prometheus (scrapes /metrics)          │    │      │
           │  │  • inference_predictions_total          │    │      │
           │  │  • inference_errors_total               │    │      │
           │  │  • logging_predictions_total            │    │      │
           │  │  • logging_defects_total                │    │      │
           │  └─────────────────────────────────────────┘    │      │
           │           ▲                                       │      │
           │           │ scrape every 15s                     │      │
           │           │                                       │      │
           │  ┌────────┴────────────────────────────────┐    │      │
           │  │  Grafana (dashboards)                   │    │      │
           │  │  • Service health overview              │    │      │
           │  │  • Prediction throughput                │    │      │
           │  │  • Error rate trends                    │    │      │
           │  └─────────────────────────────────────────┘    │      │
           │           ▲                                       │      │
           │           │ queries metrics                      │      │
           │           │                                       │      │
           │  ┌────────┴────────────────────────────────┐    │      │
           │  │  Alert Manager (alerting rules)         │    │      │
           │  │  • Model not loaded (>2 min)            │    │      │
           │  │  • High error rate (>10%)               │    │      │
           │  │  • Database not accessible              │    │      │
           │  │  • Pod not ready                        │    │      │
           │  └─────────────────────────────────────────┘    │      │
           │                                                   │      │
           └──────────────────────────────────────────────────┘      │
```

## Probe Sequence Diagram

```
CONTAINER STARTUP
│
├─ 0s: Container starts
│   └─ startup() initializes (model/database)
│
├─ 0s: Kubernetes starts probes
│   └─ startupProbe calls /health every 5s
│
├─ 30s: Model/DB initialization completes
│   └─ /health returns 200 OK ✓
│   └─ ServiceState.model_loaded = true ✓
│
├─ 150s: startupProbe succeeds (or times out)
│   └─ livenessProbe starts checking /health every 10s
│   └─ readinessProbe starts checking /ready every 5s
│
├─ 160s: /ready called, model is loaded
│   └─ Returns 200 OK ✓
│   └─ Pod added to service
│   └─ Traffic starts flowing to pod
│
├─ 160s-300s: Normal operation
│   └─ livenessProbe calls /health: ✓ ✓ ✓ (OK)
│   └─ readinessProbe calls /ready: ✓ ✓ ✓ (OK)
│   └─ Prometheus scrapes /metrics every 15s
│   └─ Prediction counter increments
│   └─ Defect counter increments
│
├─ 300s: MLflow becomes unreachable
│   └─ /ready called, checks MLflow
│   └─ Returns 503 Service Unavailable ✗
│
├─ 310s: /ready still fails
│   └─ 2 consecutive failures detected
│   └─ Pod removed from service
│   └─ Traffic stops flowing to pod
│   └─ Kubernetes alert fires: "Ready probe failed"
│
├─ 315s: MLflow comes back online
│   └─ /ready called again
│   └─ Returns 200 OK ✓
│   └─ Pod re-added to service
│   └─ Traffic resumes
│
├─ 400s: Pod crashes
│   └─ livenessProbe calls /health: ✗
│   └─ livenessProbe calls /health: ✗
│   └─ livenessProbe calls /health: ✗ (3 failures)
│   └─ Kubernetes restarts pod
│   └─ Goes back to container startup sequence
│
└─ REPEAT
```

## Probe Timing Timeline

```
Time (seconds)
│
├─ 0s ──────────────────── Container starts
│        │
│        └─ startup() runs, model/DB init begins
│           └─ state.startup_time = NOW
│           └─ state.model_loaded = false
│
├─ 0s ──────────────────── startupProbe begins
│        │
│        ├─ 0s: /health call 1 → 503 (not ready)
│        │
│        ├─ 5s: /health call 2 → 503 (not ready)
│        │
│        ├─ 10s: /health call 3 → 503 (not ready)
│        │
│        ├─ 15s: /health call 4 → 503 (not ready)
│        │
│        ├─ 20s: /health call 5 → 503 (not ready)
│        │
│        ├─ 25s: /health call 6 → 503 (not ready)
│        │
│        ├─ 30s: Model load completes
│        │   └─ state.model_loaded = true
│        │   └─ state.mlflow_accessible = true
│        │
│        ├─ 30s: /health call 7 → 200 OK ✓
│        │
│        ├─ 35s: /health call 8 → 200 OK ✓
│        │
│        ├─ 40s: /health call 9+ → 200 OK ✓
│        │
│        └─ After 30 success threshold reached:
│           └─ startupProbe succeeds
│
├─ 30s ──────────────────── livenessProbe begins
│        │                   (after 30s initial delay)
│        │
│        ├─ 30s: /health call 1 → 200 OK ✓
│        │
│        ├─ 40s: /health call 2 → 200 OK ✓
│        │
│        ├─ 50s: /health call 3 → 200 OK ✓
│        │
│        └─ Continues checking every 10s
│
├─ 10s ──────────────────── readinessProbe begins
│        │                   (after 10s initial delay)
│        │
│        ├─ 10s: /ready call 1 → 503 (model not loaded yet)
│        │
│        ├─ 15s: /ready call 2 → 503 (model not loaded yet)
│        │
│        ├─ 20s: /ready call 3 → 503 (model not loaded yet)
│        │
│        ├─ 25s: /ready call 4 → 503 (model not loaded yet)
│        │
│        ├─ 30s: /ready call 5 → 503 (initializing)
│        │
│        ├─ 30s: Model load completes
│        │   └─ state.model_loaded = true
│        │   └─ state.mlflow_accessible = true
│        │
│        ├─ 35s: /ready call 6 → 200 OK ✓ (READY)
│        │   └─ Pod added to service
│        │   └─ Traffic begins
│        │
│        ├─ 40s: /ready call 7 → 200 OK ✓
│        │
│        └─ Continues checking every 5s
│
└────────────────────────── Normal operation continues
```

## State Transitions for /ready Endpoint

```
INFERENCE SERVICE

START
  │
  ├─ model_loaded = false
  ├─ mlflow_accessible = false
  │
  ▼
┌─────────────────────────┐
│ LOADING MODEL           │
│ /ready → 503            │
│ reason: model_not_loaded│
└─────────────────────────┘
  │
  │ (model loads)
  │
  ▼
┌─────────────────────────┐
│ TESTING MLFLOW          │
│ /ready → 503            │
│ reason: depends on MLflow
└─────────────────────────┘
  │
  │ (MLflow responds)
  │
  ▼
┌─────────────────────────┐
│ READY                   │
│ /ready → 200 OK         │
│ model_loaded = true     │
│ mlflow_accessible = true│
└─────────────────────────┘
  │                         │
  │ (normal operation)      │ (MLflow fails)
  │                         │
  ▼                         ▼
  READY ◄───────────────► NOT_READY
  200 OK                 503 Service Unavailable


LOGGING SERVICE

START
  │
  ├─ db_initialized = false
  │
  ▼
┌─────────────────────────┐
│ INITIALIZING DB         │
│ /ready → 503            │
│ reason: not_initialized │
└─────────────────────────┘
  │
  │ (database ready)
  │
  ▼
┌─────────────────────────┐
│ TESTING DB ACCESS       │
│ /ready → 503            │
│ reason: if not accessible
└─────────────────────────┘
  │
  │ (database accessible)
  │
  ▼
┌─────────────────────────┐
│ READY                   │
│ /ready → 200 OK         │
│ db_initialized = true   │
└─────────────────────────┘
  │                         │
  │ (normal operation)      │ (DB fails)
  │                         │
  ▼                         ▼
  READY ◄───────────────► NOT_READY
  200 OK                 503 Service Unavailable
```

## Health Check Decision Tree

```
CLIENT CALLS /health
│
├─ Container process running?
│  └─ YES → Check service health
│  └─ NO  → Connection refused (K8s detects and restarts)
│
├─ Service health OK?
│  └─ YES → Return 200 OK + status info
│  └─ NO  → Return 500 + error details
│
└─ Result: Container alive indicator


CLIENT CALLS /ready
│
├─ Is model loaded? (inference service)
│  └─ NO → Return 503 + "model_not_loaded"
│  └─ YES → Continue
│
├─ Are dependencies accessible?
│  │  (For inference: Is MLflow reachable?)
│  │  (For logging: Is database accessible?)
│  │
│  └─ NO → Return 503 + dependency_not_accessible
│  └─ YES → Continue
│
├─ Is error rate acceptable?
│  │  (If prediction_count > 0 and error_count/prediction_count > 50%)
│  │
│  └─ HIGH → Return 503 + "high_error_rate"
│  └─ LOW  → Continue
│
└─ Return 200 OK + metrics
   └─ K8s adds pod to service
   └─ Traffic flows to pod


CLIENT CALLS /metrics
│
├─ Format metrics in Prometheus text format
│
├─ Include gauges:
│  └─ model_loaded / db_initialized (1 or 0)
│
├─ Include counters:
│  └─ predictions_total
│  └─ errors_total
│  └─ defects_total
│
└─ Return 200 OK + text/plain response
   └─ Prometheus scrapes the data
   └─ Grafana graphs the trends
```

## Response Time Characteristics

```
┌──────────────┬──────────────┬──────────────┬───────────────────┐
│ Endpoint     │ Min Time     │ Max Time     │ Typical Time      │
├──────────────┼──────────────┼──────────────┼───────────────────┤
│ /health      │ 1ms          │ 50ms         │ 5-10ms            │
│ (inference)  │ (system OK)  │ (exception)  │ (system checks)   │
├──────────────┼──────────────┼──────────────┼───────────────────┤
│ /ready       │ 10ms         │ 150ms        │ 50-100ms          │
│ (inference)  │ (checks OK)  │ (MLflow slow)│ (with MLflow test)│
├──────────────┼──────────────┼──────────────┼───────────────────┤
│ /metrics     │ 5ms          │ 100ms        │ 20-50ms           │
│ (inference)  │ (quick format) │ (exception) │ (format output)   │
├──────────────┼──────────────┼──────────────┼───────────────────┤
│ /health      │ 1ms          │ 50ms         │ 5-10ms            │
│ (logging)    │ (system OK)  │ (exception)  │ (system checks)   │
├──────────────┼──────────────┼──────────────┼───────────────────┤
│ /ready       │ 20ms         │ 200ms        │ 100-150ms         │
│ (logging)    │ (checks OK)  │ (DB timeout) │ (with DB query)   │
├──────────────┼──────────────┼──────────────┼───────────────────┤
│ /metrics     │ 5ms          │ 100ms        │ 20-50ms           │
│ (logging)    │ (quick format) │ (exception) │ (format output)   │
└──────────────┴──────────────┴──────────────┴───────────────────┘

Kubernetes Default Timeouts:
├─ httpGet timeout: 1 second (sufficient for all endpoints)
├─ Startup probe: 150 seconds max (30 failures × 5 second period)
├─ Liveness probe: 30 seconds to trigger restart (3 failures × 10s)
├─ Readiness probe: 10 seconds to remove from service (2 failures × 5s)
└─ All endpoints respond well within timeout windows
```

## Failure Scenarios and Recovery

```
SCENARIO 1: Model not loaded (during startup)
──────────────────────────────────────────────
Time    Event                           Result
0s      Container starts                
        startup() begins loading model
        
5s      /ready called (readinessprobe) → 503 model_not_loaded
        Pod NOT added to service
        
10s     /ready called                  → 503 model_not_loaded
        Pod still NOT in service
        
30s     Model load completes           
        state.model_loaded = true
        
35s     /ready called                  → 200 OK ✓
        Pod ADDED to service
        Traffic begins flowing

Recovery: Automatic (once model loads)


SCENARIO 2: MLflow becomes unreachable (during operation)
──────────────────────────────────────────────────────────
Time    Event                           Result
160s    Normal operation
        /ready called → 200 OK ✓
        Traffic flowing
        
300s    MLflow goes down              
        (network outage, restart, etc)
        
305s    /ready called                  → 503 mlflow_not_accessible
        state.mlflow_accessible = false
        Pod still in service (1st fail)
        
310s    /ready called                  → 503 mlflow_not_accessible
        Pod REMOVED from service (2nd fail)
        Traffic STOPS flowing
        
315s    MLflow recovers               
        state.mlflow_accessible = true
        
320s    /ready called                  → 200 OK ✓
        Pod ADDED back to service
        Traffic resumes

Recovery: Within 15-20 seconds of MLflow recovery


SCENARIO 3: Database becomes inaccessible (logging service)
────────────────────────────────────────────────────────────
Time    Event                           Result
160s    Normal operation
        /ready called → 200 OK ✓
        Predictions being logged
        
300s    Database locked/inaccessible   
        (file locks, permissions, etc)
        
305s    /ready called                  → 503 database_not_accessible
        Pod still in service (1st fail)
        /log endpoint returns errors
        
310s    /ready called                  → 503 database_not_accessible
        Pod REMOVED from service (2nd fail)
        /log requests fail
        
400s    Admin fixes database issue     
        
405s    /ready called                  → 200 OK ✓
        Pod ADDED back to service
        Predictions resume logging

Recovery: Once database issue is resolved


SCENARIO 4: Pod crashes / process dies
────────────────────────────────────────
Time    Event                           Result
160s    Normal operation
        /health called → 200 OK ✓
        
400s    Pod crashes (OOM, segfault)    
        Process terminates
        
410s    /health called                 → Connection refused
        livenessProbe sees failure (1st)
        
420s    /health called                 → Connection refused (2nd)
        livenessProbe sees failure
        
430s    /health called                 → Connection refused (3rd)
        livenessProbe triggers restart
        
435s    Container restarts
        startup() runs again
        
465s    Model loads
        /ready returns 200 OK ✓
        
470s    Pod added back to service
        Traffic resumes

Recovery: Within 60-70 seconds via pod restart


SCENARIO 5: Degraded performance (high error rate)
────────────────────────────────────────────────────
Time    Event                           Result
160s    Normal operation
        prediction_count = 0
        error_count = 0
        
165s    Invalid image received
        Prediction fails
        error_count = 1
        
170s    More invalid images
        error_count = 10
        prediction_count = 20
        error_rate = 50%
        
175s    /ready called
        error_rate (10/20) = 50% (not > 50%)
        → 200 OK ✓ (still ready)
        
180s    More errors accumulate
        error_count = 55
        prediction_count = 100
        error_rate = 55%
        
185s    /ready called
        error_rate (55/100) = 55% (> 50%)
        → 503 high_error_rate
        Pod removed from service
        
200s    Admin fixes data validation
        Errors stop occurring
        
500s    /ready called
        error_rate = 55/1000 = 5.5%
        → 200 OK ✓
        Pod added back to service

Recovery: When error rate drops below 50%
```

