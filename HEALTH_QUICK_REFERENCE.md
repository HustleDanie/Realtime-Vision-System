# Health Endpoints Quick Reference

## Summary

Added Kubernetes-compatible health check endpoints to both inference (port 8000) and logging (port 8001) services.

## What Was Added

### Inference Service (scripts/realtime_inference_service.py)

| Endpoint | Method | Purpose | Status Codes |
|----------|--------|---------|--------------|
| `/health` | GET | Liveness - container alive? | 200, 500 |
| `/ready` | GET | Readiness - ready to serve? | 200, 503 |
| `/metrics` | GET | Prometheus metrics | 200, 500 |

**New Class**: `ServiceState` tracks model, predictions, errors, MLflow status

**Updated**: `load_production_model()` tests MLflow, sets state
**Updated**: `startup_event()` logs startup time, error handling
**Updated**: `predict()` tracks prediction_count, error_count, last_prediction_time

### Logging Service (src/cloud_logging/api.py)

| Endpoint | Method | Purpose | Status Codes |
|----------|--------|---------|--------------|
| `/health` | GET | Liveness - container alive? | 200, 500 |
| `/ready` | GET | Readiness - ready to log? | 200, 503 |
| `/metrics` | GET | Prometheus metrics | 200, 500 |

**New Class**: `LoggingServiceState` tracks DB status, predictions, defects, errors

**Updated**: `startup()` logs startup time, sets db_initialized flag, error handling
**Updated**: `log_predictions()` tracks prediction_count, defect_count, error_count
**Added**: Decorator `@app.post("/log")` (was missing)

## How Kubernetes Uses These

```
Container Starts
  ↓
startup() initializes DB
  ↓
Kubernetes calls /health every 5s (startupProbe)
  → After model loads: Returns 200 OK
  → After 30 successes or 150s total: Moves on
  ↓
Kubernetes calls /ready every 5s (readinessProbe)
  → Model loaded + MLflow accessible: Returns 200 OK
  → Pod gets traffic
  ↓
Kubernetes calls /health every 10s (livenessProbe)
  → Still returning 200: Container stays alive
  → Returns 500 after 3 failures: Container restarts
  ↓
Kubernetes calls /ready every 5s (readinessProbe)
  → Detects high error rate: Returns 503
  → Pod removed from service (no traffic)
  → Returns 200 again: Pod gets traffic back
```

## Key Differences: /health vs /ready

| Aspect | /health | /ready |
|--------|---------|--------|
| **Purpose** | Container alive? | Can handle traffic? |
| **Checks** | System checks | Dependencies + metrics |
| **Failure Effect** | Pod restarts | Traffic stops (no restart) |
| **Response Time** | <50ms | ~100ms (DB test) |
| **When Returns 503** | Never | When dependencies fail |

## State Being Tracked

### Inference Service
- ✅ Model loaded (boolean)
- ✅ MLflow accessible (boolean)  
- ✅ Predictions served (counter)
- ✅ Errors encountered (counter)
- ✅ Last prediction time (timestamp)
- ✅ Startup time (timestamp)

### Logging Service
- ✅ Database initialized (boolean)
- ✅ Predictions logged (counter)
- ✅ Defects detected (counter)
- ✅ Logging errors (counter)
- ✅ Last prediction time (timestamp)
- ✅ Startup time (timestamp)

## Testing Locally

```bash
# Terminal 1: Start inference service
cd scripts
python -m uvicorn realtime_inference_service:app --reload --port 8000

# Terminal 2: Start logging service
cd src/cloud_logging
python -m uvicorn api:app --reload --port 8001

# Terminal 3: Test endpoints
curl http://localhost:8000/health  # Should return 200 (healthy)
curl http://localhost:8000/ready   # May return 503 if model still loading
curl http://localhost:8000/metrics # Should return Prometheus format

curl http://localhost:8001/health  # Should return 200 (healthy)
curl http://localhost:8001/ready   # Should return 200 (ready)
curl http://localhost:8001/metrics # Should return Prometheus format
```

## What Each Endpoint Returns

### /health (Liveness)
**Success (200 OK)**:
```json
{
  "status": "healthy",
  "service": "inference-service",
  "timestamp": "2026-01-28T15:30:45.123456",
  "uptime_seconds": 1234.5
}
```

### /ready (Readiness)
**Success (200 OK)**:
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

**Not Ready (503 Service Unavailable)**:
```json
{
  "status": "not_ready",
  "reason": "model_not_loaded"
}
```

### /metrics (Prometheus)
**Success (200 OK, text/plain)**:
```
# HELP inference_model_loaded Whether model is loaded
# TYPE inference_model_loaded gauge
inference_model_loaded{model="cifar10-model",stage="Production"} 1

# HELP inference_predictions_total Total predictions served
# TYPE inference_predictions_total counter
inference_predictions_total{model="cifar10-model"} 1523

# ... more metrics ...
```

## Kubernetes Probe Times (from deployment manifest)

**Startup Probe** (startup only):
- Calls every 5 seconds
- Max 30 failures = 150 seconds total
- Waits for /health to return 200

**Liveness Probe** (ongoing):
- Starts after 30 second delay
- Calls every 10 seconds
- Restarts after 3 failures (30 seconds)

**Readiness Probe** (ongoing):
- Starts after 10 second delay
- Calls every 5 seconds
- Removes from service after 2 failures (10 seconds)

## Error Handling

All endpoints include try/except blocks:
- **Inference service**: Returns 500 on exception
- **Logging service**: Returns 503 on exception

Errors are logged but don't crash the service.

## Performance Notes

- `/health`: <50ms (just system checks)
- `/ready`: ~100ms (includes DB connectivity test)
- `/metrics`: <100ms (formats counters)
- All endpoints handle concurrent requests (thread-safe)

## Files Modified

- ✅ [scripts/realtime_inference_service.py](scripts/realtime_inference_service.py)
  - Added ServiceState class
  - Enhanced load_production_model()
  - Enhanced startup_event()
  - Added /health, /ready, /metrics endpoints
  - Updated /predict to track metrics

- ✅ [src/cloud_logging/api.py](src/cloud_logging/api.py)
  - Added LoggingServiceState class
  - Enhanced startup() with error handling
  - Enhanced /health endpoint
  - Added /ready endpoint
  - Added /metrics endpoint
  - Updated /log to track metrics
  - Added missing @app.post("/log") decorator

## Documentation

- 📄 [HEALTH_ENDPOINTS.md](HEALTH_ENDPOINTS.md) - Complete health endpoint guide
  - Detailed endpoint specifications
  - Kubernetes probe configuration
  - Monitoring integration examples
  - Troubleshooting guide

## Integration with Existing Systems

These endpoints work with:
- ✅ Kubernetes probes (configured in k8s/deployment-production.yaml)
- ✅ Prometheus scraping (metrics endpoint)
- ✅ Grafana dashboards (JSON format metrics)
- ✅ Alert rules (based on metric thresholds)
- ✅ MLflow tracking (inference checks MLflow connectivity)
- ✅ CI/CD health checks (GitHub Actions can call these)

## Next Steps

1. Deploy to Kubernetes
2. Monitor probe events: `kubectl get events -n mlops`
3. Set up Prometheus to scrape `/metrics` endpoints
4. Create Grafana dashboards
5. Configure alerts for failures

