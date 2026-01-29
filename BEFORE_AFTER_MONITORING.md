# Before & After: Adding Monitoring to ML Services

## Problem: Blind Spots

**Before** (basic logging):
```python
@app.post("/predict")
def predict(request):
    print(f"Prediction received for {request.data}")  # ❌ No timestamps, context, or structure
    
    try:
        result = model.predict(request.data)
        print(f"Result: {result}")  # ❌ Can't parse programmatically
        return result
    except Exception as e:
        print(f"Error: {e}")  # ❌ Lost context, no metrics
        raise
```

**Problems**:
- ❌ Can't correlate logs across services
- ❌ No metrics for monitoring
- ❌ No visibility into errors or performance
- ❌ Can't create dashboards
- ❌ No alerting capability

---

## Solution: Structured Logging + Prometheus

**After** (with structured logging & metrics):
```python
from src.monitoring.structured_logging import (
    setup_structured_logging,
    MetricsRegistry,
)

logger = setup_structured_logging('inference-service')
metrics = MetricsRegistry('inference-service')

@app.post("/predict")
def predict(request):
    import time
    start = time.time()
    
    try:
        # ✅ Structured log with context
        logger.info('prediction_received', extra={
            'model': 'cifar10',
            'input_size': len(request.data),
        })
        
        result = model.predict(request.data)
        latency = time.time() - start
        
        # ✅ Log success with metrics
        logger.info('prediction_successful', extra={
            'model': 'cifar10',
            'latency_seconds': latency,
            'confidence': result['confidence'],
        })
        
        # ✅ Record Prometheus metrics
        metrics.predictions_total.labels(
            model='cifar10',
            status='success'
        ).inc()
        metrics.prediction_latency.labels(model='cifar10').observe(latency)
        
        return result
    
    except Exception as e:
        latency = time.time() - start
        
        # ✅ Log errors with full context
        logger.error('prediction_failed', extra={
            'model': 'cifar10',
            'error_type': type(e).__name__,
            'latency_seconds': latency,
        })
        
        # ✅ Record error metrics
        metrics.prediction_errors.labels(
            model='cifar10',
            error_type=type(e).__name__
        ).inc()
        
        raise
```

**Benefits**:
- ✅ Structured logs for log aggregation
- ✅ Metrics for monitoring and alerting
- ✅ Full context for debugging
- ✅ Dashboard visualization
- ✅ Automatic error tracking

---

## Log Output Comparison

### Before (Unstructured)
```
Prediction received for [0.1, 0.2, ...]
Result: {'class': 3, 'confidence': 0.95}
```

**Problems**:
- No timestamps
- No service name
- Can't parse programmatically
- Hard to grep/search
- No correlation IDs

---

### After (Structured JSON)
```json
{
  "timestamp": "2026-01-28T15:30:45.123456",
  "level": "INFO",
  "name": "inference-service",
  "message": "prediction_received",
  "model": "cifar10",
  "input_size": 3072,
  "service": "inference"
}
```

```json
{
  "timestamp": "2026-01-28T15:30:45.125123",
  "level": "INFO",
  "name": "inference-service",
  "message": "prediction_successful",
  "model": "cifar10",
  "latency_seconds": 0.0015,
  "confidence": 0.95,
  "service": "inference"
}
```

**Benefits**:
- ✅ Parseable JSON
- ✅ Timestamps for correlation
- ✅ Context fields for filtering
- ✅ Can be indexed and searched
- ✅ Works with log aggregation tools

---

## Monitoring Capability Comparison

### Before: Manual Monitoring
```
# Have to SSH into server and check logs manually
ssh server
tail -f /var/log/app.log | grep "Result:"

# Count errors manually
grep "Error:" /var/log/app.log | wc -l
```

**Limitations**:
- ❌ Manual, error-prone
- ❌ Not real-time
- ❌ Can't aggregate across services
- ❌ No alerts
- ❌ No historical trends

---

### After: Automated Monitoring with Prometheus

**Metric Collection** (automatic):
```
# Prometheus automatically scrapes /metrics every 15s
curl http://service:8000/metrics

# Output:
# HELP predictions_total Total predictions served
# TYPE predictions_total counter
predictions_total{model="cifar10",status="success"} 1523
predictions_total{model="cifar10",status="error"} 12

# HELP prediction_latency_seconds Prediction latency in seconds
# TYPE prediction_latency_seconds histogram
prediction_latency_seconds_bucket{model="cifar10",le="0.1"} 1400
prediction_latency_seconds_bucket{model="cifar10",le="0.25"} 1510
prediction_latency_seconds_sum{model="cifar10"} 145.23
prediction_latency_seconds_count{model="cifar10"} 1523
```

**Grafana Dashboards** (instant visualization):
```
┌─────────────────────────────────────┐
│  Inference Service Dashboard        │
├─────────────────────────────────────┤
│                                      │
│  Predictions/sec  Latency (p95)    │
│        1523/s          145ms        │
│                                      │
│  Error Rate       Model Status      │
│       0.78%           ✓ Ready       │
│                                      │
│  ┌─────────────────────────────┐   │
│  │ Prediction Latency (5m)     │   │
│  │        └─┐  ┌─┐             │   │
│  │         └┴──┘┴──┘           │   │
│  └─────────────────────────────┘   │
│                                      │
│  ┌─────────────────────────────┐   │
│  │ Error Rate Trend (24h)      │   │
│  │ 0.9%   ┌─────────────────┐  │   │
│  │ 0.5%   │  ┌─────┐  ┌──┐  │  │   │
│  │ 0.0%   └──┘     └──┘  └──┘  │   │
│  └─────────────────────────────┘   │
│                                      │
└─────────────────────────────────────┘
```

**Alerts** (automatic notifications):
```yaml
# Example Prometheus alert rule
groups:
  - name: inference_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(prediction_errors_total[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate in inference service"
          
      - alert: SlowPredictions
        expr: histogram_quantile(0.95, prediction_latency_seconds) > 1.0
        for: 5m
        annotations:
          summary: "Predictions slower than 1 second"
          
      - alert: ModelNotLoaded
        expr: model_loaded == 0
        for: 1m
        annotations:
          summary: "Model failed to load"
```

**Benefits**:
- ✅ Real-time monitoring
- ✅ Historical trends
- ✅ Automatic alerts
- ✅ Cross-service visibility
- ✅ Collaborative dashboards

---

## Code Comparison: Minimal Change

### Adding Monitoring to Existing Code

**Before** (~50 lines):
```python
@app.post("/predict")
def predict(request):
    result = model.predict(request.data)
    return result
```

**After** (~70 lines, most is logging/metrics):
```python
@app.post("/predict")
def predict(request):
    import time
    start = time.time()
    
    try:
        logger.info('prediction_received', extra={'model': 'cifar10'})
        
        result = model.predict(request.data)
        latency = time.time() - start
        
        logger.info('prediction_successful', extra={
            'latency_seconds': latency,
            'confidence': result.get('confidence'),
        })
        
        metrics.predictions_total.labels(model='cifar10', status='success').inc()
        metrics.prediction_latency.labels(model='cifar10').observe(latency)
        
        return result
    
    except Exception as e:
        latency = time.time() - start
        logger.error('prediction_failed', extra={'error_type': type(e).__name__})
        metrics.prediction_errors.labels(model='cifar10', error_type=type(e).__name__).inc()
        raise
```

**Change**: Only ~20 additional lines, mostly logging statements

---

## Real-World Impact

### Scenario 1: Slow Predictions

**Before**:
```
Manual investigation:
1. User reports slow predictions
2. SSH into server, check logs manually
3. Look for patterns in error logs
4. No metrics to check (unknown latency)
5. Restart service hoping it helps
Result: Hours to diagnose, guesswork
```

**After**:
```
Automatic alerting:
1. Prometheus alert fires: "SlowPredictions"
2. Click link to Grafana dashboard
3. See: P95 latency jumped from 50ms to 2000ms
4. See: GPU utilization at 95%, CUDA memory at 100%
5. Scale service horizontally or increase resources
Result: Minutes to diagnose with certainty
```

---

### Scenario 2: Model Deployment Problem

**Before**:
```
User queries don't work, no obvious error:
- Check application logs (none)
- Manually test prediction endpoint
- Returns generic "error" message
- Unknown what went wrong
- Rollback without knowing root cause
```

**After**:
```
Prometheus alerts fire immediately:
- model_loaded metric shows 0
- Logs show: "model_load_failed: CUDA out of memory"
- New model uses more GPU memory than old one
- Immediately rollback to previous version
- Fix model optimization before deploying again
```

---

### Scenario 3: Detecting Data Quality Issues

**Before**:
```
Predictions become less accurate over time:
- No visibility into input distribution
- No validation error tracking
- Manual analysis of input data needed
- Unknown when problem started
```

**After**:
```
Validation metrics show:
- input_validation_errors increasing at 10pm
- Logs show: "invalid_shape" errors from client X
- Contact client: their camera resolution changed
- Update input pipeline to handle both resolutions
- Problem resolved with data
```

---

## Setup Effort Comparison

### Before: DIY Monitoring
```
Time investment:
- Set up ELK stack: 4-8 hours
- Configure elasticsearch: 2-4 hours
- Create log parsing rules: 2-4 hours
- Modify application code: 4-6 hours
- Create dashboards: 2-4 hours
- Set up alerting: 2-4 hours
Total: 16-30 hours

Ongoing maintenance:
- Monitor disk usage (ELK grows fast)
- Update parsing rules for new log formats
- Troubleshoot parsing failures
- Manage Kibana access control
```

### After: Using Prometheus + Structured Logging
```
Time investment:
- Install prometheus_client: 5 minutes
- Add 3 lines to create logger/metrics: 5 minutes
- Add monitoring to key endpoints: 30 minutes
- Start Prometheus container: 2 minutes
- Create Grafana dashboard: 15 minutes
Total: ~1 hour

Ongoing maintenance:
- Prometheus storage: ~1GB per month (minimal)
- Grafana: fully managed, no parsing needed
- Metrics are self-documenting (no parsing rules)
- Low disk usage, low CPU overhead
```

---

## Performance Impact

### Overhead Measurement

**Structured Logging**:
- JSON serialization: ~1-2ms per log statement
- Network I/O: negligible (local)
- Impact on latency: <1% for most applications

**Prometheus Metrics**:
- In-memory counter operations: ~1 microsecond
- Generating `/metrics` response: ~10ms
- Impact on latency: negligible (<0.1%)

**Recommendation**: Enable structured logging and metrics in production—the benefit far outweighs the negligible performance cost.

---

## Migration Path

### Step 1: Add Structured Logging (takes 30 minutes)
```python
from src.monitoring.structured_logging import setup_structured_logging

logger = setup_structured_logging('my-service')

# Replace existing logging
# OLD: print("Started prediction")
# NEW:
logger.info('prediction_started', extra={'model': 'cifar10'})
```

### Step 2: Add Prometheus Metrics (takes 20 minutes)
```python
from src.monitoring.structured_logging import MetricsRegistry

metrics = MetricsRegistry('my-service')

# Replace endpoint to expose metrics
# OLD: (no /metrics endpoint)
# NEW:
@app.get('/metrics')
def metrics_endpoint():
    from prometheus_client import generate_latest
    return generate_latest(metrics.registry)
```

### Step 3: Instrument Key Endpoints (takes 30 minutes per endpoint)
```python
# Wrap critical operations with metric recording
start = time.time()
result = expensive_operation()
latency = time.time() - start

metrics.operation_latency.labels(operation='expensive').observe(latency)
```

### Step 4: Set Up Prometheus (takes 15 minutes)
```bash
# Create prometheus.yml
# Start Prometheus container
# Add scrape targets
```

### Step 5: Create Grafana Dashboards (takes 30 minutes)
```
# Open Grafana
# Add Prometheus data source
# Create dashboard with key metrics
# Set up alerts
```

---

## Checklist: Before → After

| Capability | Before | After |
|-----------|--------|-------|
| Structured Logs | ❌ | ✅ |
| Log Aggregation | ❌ | ✅ |
| Real-time Metrics | ❌ | ✅ |
| Dashboards | ❌ | ✅ |
| Alerts | ❌ | ✅ |
| Historical Trends | ❌ | ✅ |
| Cross-service Correlation | ❌ | ✅ |
| Error Tracking | ⚠️ Manual | ✅ Automatic |
| Performance Monitoring | ❌ | ✅ |
| Data Quality Tracking | ❌ | ✅ |
| Latency Analysis | ❌ | ✅ |
| Uptime/Availability | Manual | ✅ Automatic |

---

## Key Takeaway

**Before**: Manual investigation, reactive problem-solving
**After**: Automatic detection, proactive problem prevention

The 1-hour setup investment pays for itself in the first incident.
