# Quick Start: Monitoring Your ML Microservice

Get structured logging + Prometheus metrics up and running in **15 minutes**.

---

## 5-Minute Install

### 1. Install packages
```bash
pip install prometheus-client python-json-logger
```

### 2. Import monitoring utilities
```python
from src.monitoring.structured_logging import (
    setup_structured_logging,
    MetricsRegistry,
)
```

### 3. Initialize in your app
```python
from fastapi import FastAPI
from prometheus_client import generate_latest

app = FastAPI()

# Setup
logger = setup_structured_logging('my-service')
metrics = MetricsRegistry('my-service')

# Add metrics endpoint
@app.get('/metrics')
def metrics():
    return generate_latest(metrics.registry)
```

Done! Your service now exposes metrics.

---

## 10-Minute: Add to Your Endpoints

### Before
```python
@app.post("/predict")
def predict(request):
    result = model.predict(request.data)
    return result
```

### After
```python
import time

@app.post("/predict")
def predict(request):
    start = time.time()
    
    try:
        result = model.predict(request.data)
        latency = time.time() - start
        
        # Log success
        logger.info('prediction_successful', extra={
            'latency_seconds': latency,
            'confidence': result.get('confidence'),
        })
        
        # Record metrics
        metrics.predictions_total.labels(status='success').inc()
        metrics.prediction_latency.labels(model='my-model').observe(latency)
        
        return result
    
    except Exception as e:
        latency = time.time() - start
        
        # Log error
        logger.error('prediction_failed', extra={
            'error_type': type(e).__name__,
            'latency_seconds': latency,
        })
        
        # Record error metric
        metrics.prediction_errors.labels(error_type=type(e).__name__).inc()
        
        raise
```

---

## 15-Minute: View Metrics

### Option 1: Raw Prometheus Format
```bash
curl http://localhost:8000/metrics
```

Output:
```
# HELP predictions_total Total predictions served
# TYPE predictions_total counter
predictions_total{status="success"} 123
predictions_total{status="error"} 2

# HELP prediction_latency_seconds Prediction latency
# TYPE prediction_latency_seconds histogram
prediction_latency_seconds_bucket{le="0.1"} 110
prediction_latency_seconds_bucket{le="0.5"} 119
prediction_latency_seconds_sum 15.234
prediction_latency_seconds_count 123
```

### Option 2: Prometheus Dashboard
```bash
# Install Prometheus
docker run -p 9090:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus

# Visit http://localhost:9090
```

### Option 3: Grafana Dashboard
```bash
# Install Grafana
docker run -p 3000:3000 grafana/grafana

# Visit http://localhost:3000 (admin/admin)
# Add data source: http://prometheus:9090
# Query: rate(predictions_total[1m])
```

---

## Available Metrics (Pre-configured)

### Prediction Metrics
```python
metrics.predictions_total           # Counter: success/error
metrics.prediction_latency          # Histogram: response time
metrics.prediction_confidence       # Histogram: confidence scores
metrics.prediction_errors           # Counter: errors by type
```

### Model Metrics
```python
metrics.model_loaded                # Gauge: is model loaded?
metrics.model_load_time             # Histogram: startup time
```

### HTTP Metrics
```python
metrics.http_requests_total         # Counter: by method/endpoint/status
metrics.http_request_latency        # Histogram: response time
```

### Data Quality
```python
metrics.input_validation_errors     # Counter: bad inputs
```

---

## Useful Queries

### Throughput
```promql
# Predictions per second (last 5 min)
rate(predictions_total[5m])

# Requests per second
rate(http_requests_total[1m])
```

### Latency
```promql
# 95th percentile latency (last 5 min)
histogram_quantile(0.95, rate(prediction_latency_seconds_bucket[5m]))

# Average latency
avg(rate(prediction_latency_seconds_sum[5m]) / 
    rate(prediction_latency_seconds_count[5m]))
```

### Errors
```promql
# Error rate (percentage)
100 * (rate(prediction_errors_total[5m]) / rate(predictions_total[5m]))

# Errors per second
rate(prediction_errors_total[1m])

# Error distribution
sum by (error_type) (rate(prediction_errors_total[5m]))
```

### System Health
```promql
# Model status (1 = loaded, 0 = not loaded)
model_loaded

# Service availability
up{job="my-service"}
```

---

## Structured Log Example

### In code
```python
logger.info('prediction_successful', extra={
    'model': 'cifar10',
    'latency_seconds': 0.125,
    'confidence': 0.95,
    'class': 3,
})
```

### Output (JSON)
```json
{
  "timestamp": "2026-01-28T15:30:45.123456",
  "level": "INFO",
  "name": "my-service",
  "message": "prediction_successful",
  "model": "cifar10",
  "latency_seconds": 0.125,
  "confidence": 0.95,
  "class": 3,
  "service": "my-service"
}
```

### Benefits
- ✅ Parseable by log aggregation (Loki, ELK, Datadog)
- ✅ Timestamped for correlation
- ✅ Structured for filtering/searching
- ✅ Works with container logging

---

## Common Patterns

### Pattern 1: Log with Context
```python
from src.monitoring.structured_logging import LogContext

with LogContext(logger, 'database_query', query_type='insert'):
    # Automatically logs start, end, duration, status
    db.insert(data)
```

### Pattern 2: Validate and Log
```python
from src.monitoring.structured_logging import log_data_quality

log_error = log_data_quality(logger, metrics)

if input_shape != expected_shape:
    log_error('my-model', 'invalid_shape', {
        'expected': expected_shape,
        'got': input_shape
    })
    # Automatically increments validation error metric
```

### Pattern 3: Time Measurements
```python
import time

start = time.time()
result = expensive_operation()
latency = time.time() - start

logger.info('operation_completed', extra={
    'latency_seconds': latency,
    'result_size': len(result),
})

metrics.operation_latency.labels(operation='expensive').observe(latency)
```

---

## Troubleshooting

### "No metrics showing in Prometheus"
```bash
# Check the /metrics endpoint works
curl http://localhost:8000/metrics

# Check Prometheus config points to your service
cat prometheus.yml | grep -A 5 "targets:"

# Check Prometheus targets page
# Go to http://localhost:9090/targets
# Service should be UP (not DOWN)
```

### "Logs not structured (just plain text)"
```python
# Make sure you're using the right logger
logger = setup_structured_logging('my-service')

# Not using print or standard logging
logger.info('...')  # ✓ Correct
print('...')        # ✗ Wrong
logging.info('...')  # ✗ Wrong (not structured)
```

### "Too many metrics / cardinality explosion"
```python
# ✓ Good: Use fixed labels
metrics.predictions.labels(model='cifar10', status='success').inc()

# ✗ Bad: Don't use unbounded labels
metrics.predictions.labels(request_id=request_id).inc()  # Creates millions of series!
metrics.predictions.labels(timestamp=now()).inc()         # Changes every second!
metrics.predictions.labels(user_id=user_id).inc()         # Too many users!
```

---

## Next Steps

### Step 1: Add Monitoring ✓
```python
# You just did this!
```

### Step 2: Deploy
```bash
docker build -t my-service .
docker run -p 8000:8000 my-service
```

### Step 3: Set Up Prometheus (optional)
```bash
# See COMPLETE_MONITORING_SETUP.md for details
docker run -p 9090:9090 prom/prometheus
```

### Step 4: Create Dashboards (optional)
```
# See COMPLETE_MONITORING_SETUP.md for Grafana setup
```

### Step 5: Add Alerts (optional)
```
# See COMPLETE_MONITORING_SETUP.md for alert rules
```

---

## Metrics Quick Reference

| Metric | Type | When to Use |
|--------|------|-------------|
| `predictions_total` | Counter | Track all predictions |
| `prediction_latency` | Histogram | Track response times |
| `prediction_errors` | Counter | Track failure reasons |
| `model_loaded` | Gauge | Track model availability |
| `input_validation_errors` | Counter | Track data quality |
| `http_requests_total` | Counter | Track API usage |
| `http_request_latency` | Histogram | Track API performance |

---

## Complete Minimal Example

```python
from fastapi import FastAPI
from prometheus_client import generate_latest
from src.monitoring.structured_logging import (
    setup_structured_logging,
    MetricsRegistry,
)
import time

app = FastAPI()

# Setup monitoring
logger = setup_structured_logging('demo-service')
metrics = MetricsRegistry('demo-service')

# Expose metrics
@app.get('/metrics')
def metrics_endpoint():
    return generate_latest(metrics.registry)

# Simple endpoint with monitoring
@app.post('/predict')
def predict(request):
    start = time.time()
    
    try:
        # Simulate prediction
        result = {'class': 3, 'confidence': 0.95}
        latency = time.time() - start
        
        # Log
        logger.info('prediction_successful', extra={
            'latency_seconds': latency,
            'confidence': result['confidence'],
        })
        
        # Metrics
        metrics.predictions_total.labels(status='success').inc()
        metrics.prediction_latency.labels(model='demo').observe(latency)
        
        return result
    
    except Exception as e:
        # Log error
        logger.error('prediction_failed', extra={
            'error': str(e),
        })
        
        # Metrics
        metrics.prediction_errors.labels(error_type='unknown').inc()
        raise

if __name__ == '__main__':
    import uvicorn
    logger.info('service_starting', extra={'port': 8000})
    uvicorn.run(app, host='0.0.0.0', port=8000)
```

**Run it**:
```bash
python app.py

# In another terminal:
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d "{}"
curl http://localhost:8000/metrics
```

---

## Key Takeaways

✅ **3 lines** to add basic monitoring
✅ **5-10 lines** per endpoint to instrument
✅ **0 dependencies** on external systems (works standalone)
✅ **100% gain** in observability

Total effort: **15 minutes**
Value: **Invaluable for production**

See [LOGGING_AND_METRICS_GUIDE.md](LOGGING_AND_METRICS_GUIDE.md) for advanced patterns.
See [COMPLETE_MONITORING_SETUP.md](COMPLETE_MONITORING_SETUP.md) for production stack.
