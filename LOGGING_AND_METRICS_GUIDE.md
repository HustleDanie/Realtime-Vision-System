# Structured Logging and Prometheus Metrics Guide

## Quick Start

### 1. Install Dependencies

```bash
pip install prometheus-client python-json-logger fastapi
```

### 2. Basic Setup (3 lines of code)

```python
from src.monitoring.structured_logging import (
    setup_structured_logging,
    MetricsRegistry
)

# Initialize
logger = setup_structured_logging('my-service')
metrics = MetricsRegistry('my-service')
```

### 3. Add to Your FastAPI App

```python
from fastapi import FastAPI
from prometheus_client import generate_latest

app = FastAPI()

# Add metrics endpoint
@app.get('/metrics')
def metrics_endpoint():
    return generate_latest(metrics.registry)
```

That's it! Your service now exposes Prometheus metrics.

---

## Structured Logging Examples

### Basic Logging

```python
# Instead of print() statements, use structured logs:
logger.info('prediction_started', extra={
    'model': 'cifar10',
    'timestamp': datetime.utcnow().isoformat(),
})
```

**Output** (JSON format):
```json
{
  "timestamp": "2026-01-28T15:30:45.123456",
  "level": "INFO",
  "name": "inference-service",
  "message": "prediction_started",
  "model": "cifar10",
  "service": "inference"
}
```

### Logging with Context

```python
from src.monitoring.structured_logging import LogContext

with LogContext(logger, 'model_loading', model='cifar10', version='v2'):
    # Your code here
    model = load_model()
    # Automatically logs: start, end, duration, success/failure
```

**Output**:
```json
{"message": "model_loading_started", "model": "cifar10", "version": "v2", ...}
{"message": "model_loading_completed", "latency_seconds": 2.345, "status": "success", ...}
```

### Data Quality Logging

```python
log_error = log_data_quality(logger, metrics)

# Log validation error
if tensor.shape != expected_shape:
    log_error('cifar10', 'invalid_shape', {
        'expected': expected_shape,
        'got': tuple(tensor.shape)
    })
```

**Output**:
```json
{
  "message": "data_validation_error",
  "model": "cifar10",
  "error_type": "invalid_shape",
  "details": "{\"expected\": (1, 3, 32, 32), \"got\": (1, 64, 64)}"
}
```

---

## Prometheus Metrics Examples

### Available Metrics

#### 1. Prediction Metrics

```python
# Counter: Total predictions
metrics.predictions_total.labels(model='cifar10', status='success').inc()

# Histogram: Prediction latency
metrics.prediction_latency.labels(model='cifar10').observe(0.125)

# Histogram: Confidence scores
metrics.prediction_confidence.labels(model='cifar10').observe(0.95)
```

#### 2. Error Metrics

```python
# Counter: Prediction errors
metrics.prediction_errors.labels(
    model='cifar10',
    error_type='cuda_oom'
).inc()

# Counter: Input validation errors
metrics.input_validation_errors.labels(
    model='cifar10',
    error_reason='invalid_shape'
).inc()
```

#### 3. Model Metrics

```python
# Gauge: Whether model is loaded
metrics.model_loaded.labels(model='cifar10').set(1)  # 1 = loaded, 0 = not loaded

# Histogram: Model load time
metrics.model_load_time.labels(model='cifar10').observe(2.345)
```

#### 4. HTTP Metrics

```python
# Counter: Total HTTP requests
metrics.http_requests_total.labels(
    method='POST',
    endpoint='/predict',
    status=200
).inc()

# Histogram: Request latency
metrics.http_request_latency.labels(
    method='POST',
    endpoint='/predict'
).observe(0.125)
```

---

## Integration Examples

### Example 1: Inference Service

```python
from fastapi import FastAPI
from prometheus_client import generate_latest
from src.monitoring.structured_logging import (
    setup_structured_logging,
    MetricsRegistry,
    LogContext,
)

app = FastAPI()
logger = setup_structured_logging('inference-service')
metrics = MetricsRegistry('inference-service')

@app.on_event("startup")
async def startup():
    with LogContext(logger, 'model_loading', model='cifar10'):
        # Load model
        global model
        model = load_model()
        metrics.model_loaded.labels(model='cifar10').set(1)

@app.post("/predict")
def predict(request):
    import time
    start = time.time()
    
    try:
        # Make prediction
        result = model.predict(request.data)
        latency = time.time() - start
        
        # Log success
        logger.info('prediction_successful', extra={
            'model': 'cifar10',
            'latency_seconds': latency,
            'confidence': result['confidence'],
        })
        
        # Record metrics
        metrics.predictions_total.labels(
            model='cifar10',
            status='success'
        ).inc()
        metrics.prediction_latency.labels(model='cifar10').observe(latency)
        
        return result
    
    except Exception as e:
        latency = time.time() - start
        
        logger.error('prediction_failed', extra={
            'model': 'cifar10',
            'error_type': type(e).__name__,
            'latency_seconds': latency,
        })
        
        metrics.prediction_errors.labels(
            model='cifar10',
            error_type=type(e).__name__
        ).inc()
        
        raise

@app.get("/metrics")
def metrics():
    return generate_latest(metrics.registry)
```

### Example 2: Logging Service

```python
from fastapi import FastAPI
from src.monitoring.structured_logging import (
    setup_structured_logging,
    MetricsRegistry,
    LogContext,
)

app = FastAPI()
logger = setup_structured_logging('logging-service')
metrics = MetricsRegistry('logging-service')

@app.post("/log")
def log_predictions(batch):
    with LogContext(logger, 'storing_predictions', batch_size=len(batch)):
        try:
            # Store predictions
            for pred in batch:
                store_prediction(pred)
                metrics.predictions_total.labels(
                    model=pred['model'],
                    status='success'
                ).inc()
                
                if pred.get('defect_detected'):
                    metrics.defect_count.inc()
        
        except Exception as e:
            logger.error('storage_failed', extra={
                'error_type': type(e).__name__,
                'batch_size': len(batch),
            })
            metrics.prediction_errors.labels(
                model='unknown',
                error_type='storage'
            ).inc()
            raise

@app.get("/metrics")
def metrics():
    from prometheus_client import generate_latest
    return generate_latest(metrics.registry)
```

---

## Prometheus Configuration

### Scrape Configuration

Add to your `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  scrape_timeout: 10s

scrape_configs:
  - job_name: 'inference-service'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
  
  - job_name: 'logging-service'
    static_configs:
      - targets: ['localhost:8001']
    metrics_path: '/metrics'
```

### Start Prometheus

```bash
# Docker
docker run -p 9090:9090 -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus

# Or locally
prometheus --config.file=prometheus.yml
```

Then open http://localhost:9090

---

## Grafana Queries

### Model Performance

```promql
# Prediction latency (95th percentile)
histogram_quantile(0.95, rate(prediction_latency_seconds_bucket[5m]))

# Predictions per second
rate(predictions_total[1m])

# Error rate
rate(prediction_errors_total[1m]) / rate(predictions_total[1m])

# Average confidence
avg(prediction_confidence_bucket) by (model)

# Model load status
model_loaded
```

### Throughput

```promql
# Total predictions logged
logging_predictions_total

# Defect detection rate
rate(logging_defects_total[5m]) / rate(logging_predictions_total[5m])

# Defects per minute
rate(logging_defects_total[1m])
```

### System Health

```promql
# Service uptime
time() - process_start_time_seconds

# Request latency
histogram_quantile(0.99, rate(http_request_latency_seconds_bucket[5m]))

# HTTP error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
```

---

## Log Aggregation (ELK, Loki, etc.)

### With Loki (Docker Compose)

```yaml
services:
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
  
  promtail:
    image: grafana/promtail:latest
    volumes:
      - /var/log:/var/log
    command: -config.file=/etc/promtail/config.yml
```

### JSON Logging Output

Because we use `python-json-logger`, logs are automatically JSON:

```json
{
  "timestamp": "2026-01-28T15:30:45.123456",
  "level": "INFO",
  "name": "inference-service",
  "message": "prediction_successful",
  "model": "cifar10",
  "latency_seconds": 0.125,
  "confidence": 0.95,
  "service": "inference"
}
```

These can be parsed and indexed by log aggregation tools.

---

## Common Metrics to Track

| Metric | Type | Purpose |
|--------|------|---------|
| `predictions_total` | Counter | Total predictions served |
| `prediction_latency_seconds` | Histogram | Prediction response time |
| `prediction_errors_total` | Counter | Prediction failures |
| `prediction_confidence` | Histogram | Model confidence distribution |
| `model_loaded` | Gauge | Model availability |
| `model_load_time_seconds` | Histogram | Startup performance |
| `input_validation_errors_total` | Counter | Data quality issues |
| `http_requests_total` | Counter | API usage |
| `http_request_latency_seconds` | Histogram | API response time |

---

## Best Practices

### 1. Log Levels

```python
logger.debug('...')      # Development details, verbose
logger.info('...')       # Important events (predictions, startups)
logger.warning('...')    # Anomalies (high error rate, slow requests)
logger.error('...')      # Failures (exceptions, failed operations)
```

### 2. Metric Names

- Use `_total` suffix for counters: `predictions_total`
- Use `_seconds` suffix for durations: `latency_seconds`
- Use descriptive names: `prediction_latency` not just `latency`
- Group related metrics: `model_*, prediction_*, http_*`

### 3. Label Strategy

```python
# Good: Meaningful labels
metrics.predictions_total.labels(model='cifar10', status='success').inc()

# Bad: Too many labels or cardinality explosion
metrics.predictions_total.labels(
    model=model_name,
    request_id=uuid,  # Cardinality explosion!
    timestamp=now     # Changes every second!
).inc()
```

### 4. Structured Log Fields

```python
# Good: All fields at top level
logger.info('prediction_successful', extra={
    'model': 'cifar10',
    'latency_seconds': 0.125,
    'confidence': 0.95,
})

# OK: Nested details when needed
logger.info('prediction_successful', extra={
    'model': 'cifar10',
    'metrics': {
        'latency_seconds': 0.125,
        'confidence': 0.95,
    }
})
```

---

## Troubleshooting

### Metrics Not Showing in Prometheus

1. Check Prometheus targets: http://localhost:9090/targets
2. Verify metrics endpoint works: `curl http://localhost:8000/metrics`
3. Check scrape interval: `prometheus_tsdb_metric_chunks_created` metric
4. Verify label consistency: same metric, same label names

### Missing Logs

1. Check logger level: `logger.setLevel(logging.INFO)`
2. Verify handler added: `logger.addHandler(...)`
3. Check formatter: JSON logs require `JsonFormatter`
4. Ensure service is writing to stdout/stderr (Docker logs)

### High Cardinality Metrics

**Problem**: Too many unique label combinations

```python
# BAD: Causes metric explosion
metrics.requests.labels(user_id=user_id, endpoint=endpoint).inc()

# GOOD: Aggregate users, keep labels meaningful
metrics.requests.labels(endpoint=endpoint).inc()
metrics.requests_by_status.labels(
    endpoint=endpoint,
    status=status_code
).inc()
```

---

## Complete Example: Setup Script

```python
from src.monitoring.structured_logging import (
    setup_structured_logging,
    MetricsRegistry,
)
from fastapi import FastAPI
from prometheus_client import generate_latest

def setup_monitoring(app: FastAPI, service_name: str):
    """
    Complete monitoring setup for a FastAPI service.
    
    Usage:
        app = FastAPI()
        logger, metrics = setup_monitoring(app, 'my-service')
    """
    
    # Initialize logging
    logger = setup_structured_logging(
        service_name=service_name,
        log_level='INFO',
        log_format='json'
    )
    
    # Initialize metrics
    metrics = MetricsRegistry(service_name)
    
    # Add metrics endpoint
    @app.get('/metrics')
    def metrics_endpoint():
        logger.debug('metrics_requested', extra={'service': service_name})
        return generate_latest(metrics.registry)
    
    logger.info('monitoring_initialized', extra={
        'service': service_name,
        'logging_format': 'json',
        'metrics_enabled': True,
    })
    
    return logger, metrics
```

---

## Summary

✅ **Structured Logging**: JSON format for log aggregation
✅ **Prometheus Metrics**: Industry-standard metrics exposure
✅ **Automatic Instrumentation**: Decorators and middleware
✅ **Production-Ready**: Error handling, context management
✅ **Easy Integration**: ~10 lines of code to add monitoring

See `examples/inference_service_with_logging.py` for a complete working example.
