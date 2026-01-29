# Kubernetes Health Check Endpoints

This document describes the health check endpoints added to both inference and logging services for Kubernetes container monitoring and orchestration.

## Overview

Health checks enable Kubernetes to:
- **Detect dead containers** (liveness probes)
- **Ensure services are ready** before routing traffic (readiness probes)
- **Wait for startup completion** (startup probes)
- **Monitor service metrics** for dashboards and alerting

## Probe Types

Kubernetes uses three types of probes configured in [k8s/deployment-production.yaml](k8s/deployment-production.yaml):

### 1. Startup Probe
- **Purpose**: Allow time for model loading during container startup
- **When**: Called immediately when container starts
- **Success Criteria**: Endpoint returns 200 OK
- **Max Duration**: 150 seconds (30 failures × 5 second interval)
- **Effect of Failure**: Other probes don't run; container keeps trying to start

### 2. Liveness Probe  
- **Purpose**: Detect dead/stuck containers that need restart
- **When**: Calls every 10 seconds after 30 second initial delay
- **Success Criteria**: Endpoint returns 200 OK
- **Failure Effect**: Kubernetes restarts the container after 3 consecutive failures (30 seconds)
- **Endpoint**: `GET /health`

### 3. Readiness Probe
- **Purpose**: Determine if pod should receive traffic
- **When**: Calls every 5 seconds after 10 second initial delay  
- **Success Criteria**: Endpoint returns 200 OK
- **Failure Effect**: Pod removed from service (traffic stops) after 2 failures (10 seconds)
- **Endpoint**: `GET /ready`

---

## Inference Service (Port 8000)

### Endpoints

#### 1. `/health` - Liveness Check
```
GET /health
```

**Purpose**: Basic container alive check. Used by Kubernetes livenessProbe.

**Success Response (200 OK)**:
```json
{
  "status": "healthy",
  "service": "inference-service",
  "timestamp": "2026-01-28T15:30:45.123456",
  "uptime_seconds": 1234.5
}
```

**Failure Response (500)**: 
```json
{
  "status": "unhealthy",
  "error": "error message"
}
```

**Checks Performed**:
- ✅ Container is running
- ✅ Python environment is functional
- ✅ FastAPI is responsive

**When to Fail**: 
- Critical system errors that crash the service

---

#### 2. `/ready` - Readiness Check
```
GET /ready
```

**Purpose**: Verify service is ready to handle predictions. Used by Kubernetes readinessProbe.

**Success Response (200 OK)**:
```json
{
  "status": "ready",
  "model_loaded": true,
  "mlflow_accessible": true,
  "predictions_served": 1523,
  "errors": 2,
  "last_prediction": "2026-01-28T15:30:42.987654",
  "timestamp": "2026-01-28T15:30:45.123456"
}
```

**Not Ready Response (503 Service Unavailable)**:
```json
{
  "status": "not_ready",
  "reason": "model_not_loaded"
}
```

**Checks Performed**:
- ✅ Model is loaded from MLflow
- ✅ MLflow is accessible
- ✅ Error rate < 50%

**Possible "Not Ready" Reasons**:
- `model_not_loaded`: Model still loading (during startup)
- `mlflow_not_accessible`: Cannot reach MLflow Model Registry
- `high_error_rate`: Too many prediction errors (>50%)

**When Used**:
- On container startup (waits up to 150 seconds for model to load)
- During normal operation (removes pod from service if dependencies fail)
- After deployment (ensures traffic only routes to ready pods)

---

#### 3. `/metrics` - Prometheus Metrics
```
GET /metrics
```

**Purpose**: Expose service metrics in Prometheus format for monitoring dashboards.

**Response (200 OK, text/plain)**:
```
# HELP inference_model_loaded Whether model is loaded
# TYPE inference_model_loaded gauge
inference_model_loaded{model="cifar10-model",stage="Production"} 1

# HELP inference_predictions_total Total predictions served
# TYPE inference_predictions_total counter
inference_predictions_total{model="cifar10-model"} 1523

# HELP inference_errors_total Total prediction errors
# TYPE inference_errors_total counter
inference_errors_total{model="cifar10-model"} 2

# HELP inference_mlflow_accessible Whether MLflow is accessible
# TYPE inference_mlflow_accessible gauge
inference_mlflow_accessible 1
```

**Metrics Exposed**:
- `inference_model_loaded`: 1 if loaded, 0 if not
- `inference_predictions_total`: Total predictions served
- `inference_errors_total`: Total prediction errors
- `inference_mlflow_accessible`: 1 if MLflow accessible, 0 if not

**Use Cases**:
- Grafana dashboards showing service health
- Alerting on high error rates
- Tracking model availability
- SLA monitoring

---

## Logging Service (Port 8001)

### Endpoints

#### 1. `/health` - Liveness Check
```
GET /health
```

**Purpose**: Basic container alive check. Used by Kubernetes livenessProbe.

**Success Response (200 OK)**:
```json
{
  "status": "healthy",
  "service": "cloud-logging-api",
  "timestamp": "2026-01-28T15:30:45.123456",
  "uptime_seconds": 5678.9
}
```

**Failure Response (500)**: 
```json
{
  "status": "unhealthy",
  "error": "error message"
}
```

**Checks Performed**:
- ✅ Container is running
- ✅ FastAPI is responsive

---

#### 2. `/ready` - Readiness Check  
```
GET /ready
```

**Purpose**: Verify service is ready to log predictions. Used by Kubernetes readinessProbe.

**Success Response (200 OK)**:
```json
{
  "status": "ready",
  "db_initialized": true,
  "predictions_logged": 4856,
  "defects_detected": 238,
  "errors": 1,
  "last_prediction": "2026-01-28T15:30:42.654321",
  "timestamp": "2026-01-28T15:30:45.123456"
}
```

**Not Ready Response (503 Service Unavailable)**:
```json
{
  "status": "not_ready",
  "reason": "database_not_accessible"
}
```

**Checks Performed**:
- ✅ SQLite database is initialized
- ✅ Database file is accessible and writable
- ✅ Can execute SQL queries
- ✅ Error rate < 50%

**Possible "Not Ready" Reasons**:
- `database_not_initialized`: Database not created yet
- `database_not_accessible`: Cannot read/write to database file
- `high_error_rate`: Too many logging errors (>50%)

---

#### 3. `/metrics` - Prometheus Metrics
```
GET /metrics
```

**Purpose**: Expose service metrics in Prometheus format.

**Response (200 OK, text/plain)**:
```
# HELP logging_db_initialized Whether database is initialized
# TYPE logging_db_initialized gauge
logging_db_initialized{service="cloud-logging-api"} 1

# HELP logging_predictions_total Total predictions logged
# TYPE logging_predictions_total counter
logging_predictions_total{service="cloud-logging-api"} 4856

# HELP logging_defects_total Total defects detected and logged
# TYPE logging_defects_total counter
logging_defects_total{service="cloud-logging-api"} 238

# HELP logging_errors_total Total logging errors
# TYPE logging_errors_total counter
logging_errors_total{service="cloud-logging-api"} 1
```

**Metrics Exposed**:
- `logging_db_initialized`: 1 if database ready, 0 if not
- `logging_predictions_total`: Total predictions logged
- `logging_defects_total`: Total defects detected
- `logging_errors_total`: Total logging errors

---

## Service State Tracking

Both services track internal state for health checks:

### Inference Service (ServiceState)
```python
class ServiceState:
    model: Optional[object]              # Loaded PyTorch model
    model_loaded: bool                  # Whether model successfully loaded
    startup_time: Optional[str]         # ISO timestamp of startup
    last_prediction_time: Optional[str] # ISO timestamp of last prediction
    prediction_count: int               # Total predictions served
    error_count: int                    # Total errors encountered
    mlflow_accessible: bool             # Whether MLflow is reachable
```

### Logging Service (LoggingServiceState)
```python
class LoggingServiceState:
    db_initialized: bool                # Whether database is ready
    startup_time: Optional[str]         # ISO timestamp of startup
    prediction_count: int               # Total predictions logged
    defect_count: int                   # Total defects detected
    error_count: int                    # Total logging errors
    last_prediction_time: Optional[str] # ISO timestamp of last log
```

---

## Testing Health Endpoints

### Local Testing

Test inference service:
```bash
# Liveness check
curl http://localhost:8000/health
# Expected: 200 OK with healthy status

# Readiness check (before model loads)
curl http://localhost:8000/ready
# Expected: 503 Service Unavailable (model still loading)

# Readiness check (after model loads)
curl http://localhost:8000/ready
# Expected: 200 OK with ready status

# Metrics
curl http://localhost:8000/metrics
# Expected: 200 OK with Prometheus format metrics
```

Test logging service:
```bash
# Liveness check
curl http://localhost:8001/health
# Expected: 200 OK with healthy status

# Readiness check
curl http://localhost:8001/ready  
# Expected: 200 OK with ready status (database initialized)

# Metrics
curl http://localhost:8001/metrics
# Expected: 200 OK with Prometheus format metrics
```

### Kubernetes Testing

After deployment, test probes:
```bash
# Get pod name
kubectl get pods -n mlops

# Check probe status (should be Running)
kubectl describe pod <pod-name> -n mlops | grep -A 5 "Conditions:"

# Check liveness probe logs
kubectl logs <pod-name> -n mlops | grep "health check"

# Port forward to test endpoints directly
kubectl port-forward <pod-name> 8000:8000 -n mlops
curl http://localhost:8000/ready
```

---

## Kubernetes Probe Configuration

The deployment manifest configures probes as follows:

```yaml
# Startup Probe - Allow 150s for model loading
startupProbe:
  httpGet:
    path: /health
    port: 8000
  failureThreshold: 30
  periodSeconds: 5

# Liveness Probe - Restart if unhealthy
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  failureThreshold: 3

# Readiness Probe - Remove from service if not ready
readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 2
```

---

## Monitoring Integration

### Prometheus Scraping

Add to `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'inference-service'
    static_configs:
      - targets: ['inference-service:8000']
    metrics_path: '/metrics'
    
  - job_name: 'logging-service'
    static_configs:
      - targets: ['cloud-logging-api:8001']
    metrics_path: '/metrics'
```

### Grafana Dashboards

Example queries:
```promql
# Model availability
inference_model_loaded

# Prediction throughput
rate(inference_predictions_total[1m])

# Error rate
rate(inference_errors_total[1m]) / rate(inference_predictions_total[1m])

# Defect detection rate
rate(logging_defects_total[1m]) / rate(logging_predictions_total[1m])
```

### Alerting Rules

Example alert:
```yaml
groups:
  - name: inference_alerts
    rules:
      - alert: ModelNotLoaded
        expr: inference_model_loaded == 0
        for: 2m
        annotations:
          summary: "Model not loaded in inference service"
          
      - alert: HighErrorRate
        expr: rate(inference_errors_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High error rate in inference service (>10%)"
```

---

## Troubleshooting

### Pod stuck in CrashLoopBackOff

**Symptom**: Pod crashes immediately after starting
- **Check**: `kubectl logs <pod> -n mlops`
- **Solution**: Likely startup probe failing; check model loading
- **Fix**: Increase `startupProbe.failureThreshold` if model takes >150s to load

### Pod running but no traffic

**Symptom**: Pod shows as Running but `/ready` returns 503
- **Check**: `curl http://<pod-ip>:8000/ready`
- **Solution**: Dependencies not ready; check model/database
- **Fix**: Verify MLflow is accessible, database is initialized

### High error rate alerts

**Symptom**: Grafana alert fires for high error rate
- **Check**: `curl http://<pod-ip>:8000/metrics | grep errors`
- **Solution**: Check logs for prediction failures
- **Fix**: May indicate model issues or invalid input data

### Metrics endpoint slow/unresponsive

**Symptom**: `/metrics` endpoint times out
- **Check**: `time curl http://localhost:8000/metrics`
- **Solution**: Service is overloaded or stuck
- **Fix**: Kubernetes will trigger liveness probe; pod will restart

---

## Performance Notes

- All health check endpoints are lightweight and respond in <100ms
- No database queries in `/health` (only system checks)
- `/ready` performs minimal database connectivity test
- `/metrics` formats output on-demand (consider caching for high-scale deployments)
- State tracking uses in-memory counters (very fast, no external calls)

---

## Next Steps

1. ✅ Deploy services with new health endpoints
2. ✅ Monitor Kubernetes probe events: `kubectl get events -n mlops`
3. ✅ Set up Prometheus scraping for metrics
4. ✅ Create Grafana dashboards for monitoring
5. ✅ Configure alerting rules for errors and high latency
6. ✅ Test failover scenarios (stop model, restart service, etc.)

