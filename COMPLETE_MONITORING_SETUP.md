# Complete Monitoring Stack Setup

A production-ready monitoring system for ML microservices using Prometheus + Grafana + Structured Logging.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Your ML Services                       │
│  ┌──────────────────────┐      ┌──────────────────────┐ │
│  │ Inference Service    │      │ Logging Service      │ │
│  │ Port 8000            │      │ Port 8001            │ │
│  ├──────────────────────┤      ├──────────────────────┤ │
│  │ GET /metrics         │      │ GET /metrics         │ │
│  │ POST /predict        │      │ POST /log            │ │
│  │ GET /health          │      │ GET /health          │ │
│  └──────────────────────┘      └──────────────────────┘ │
│         ▲                              ▲                 │
│         │ structured logs              │ structured logs │
│         └──────────────┬───────────────┘                │
│                        │                                 │
└─────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
    ┌────────┐      ┌─────────────┐   ┌─────────┐
    │ Metrics│      │ Logs (JSON) │   │Events   │
    │(Counter)      │             │   │         │
    │        │      │             │   │         │
    └────────┘      └─────────────┘   └─────────┘
        ▲                │                ▲
        │                │                │
        │        ┌────────────────┐      │
        │        │ Log Aggregation│      │
        │        │ (Loki/ELK)     │      │
        │        └────────────────┘      │
        │                                │
    ┌───────────────────────────────────┐
    │       Prometheus Server            │
    │  • Scrapes /metrics every 15s     │
    │  • Stores timeseries data         │
    │  • Evaluates alert rules          │
    │  • Exposes query API              │
    └───────────────────────────────────┘
        ▲             │
        │             │
    ┌───┴─────────────┴───┐
    │                     │
    ▼                     ▼
┌─────────────┐    ┌───────────────┐
│   Grafana   │    │ Alert Manager │
│ Dashboards  │    │ (Email/Slack) │
└─────────────┘    └───────────────┘
```

---

## Step-by-Step Setup

### 1. Install Python Dependencies

```bash
pip install prometheus-client python-json-logger fastapi uvicorn
```

### 2. Update Your Services

See `examples/inference_service_with_logging.py` for complete example.

**Minimal changes required**:

```python
from src.monitoring.structured_logging import (
    setup_structured_logging,
    MetricsRegistry,
)
from prometheus_client import generate_latest

# 1. Initialize (3 lines)
logger = setup_structured_logging('my-service')
metrics = MetricsRegistry('my-service')

# 2. Add metrics endpoint (5 lines)
@app.get('/metrics')
def metrics_endpoint():
    return generate_latest(metrics.registry)

# 3. Use in endpoints (add 5-10 lines per endpoint)
@app.post('/predict')
def predict(request):
    start = time.time()
    
    logger.info('prediction_started', extra={'model': 'cifar10'})
    
    try:
        result = model.predict(request.data)
        latency = time.time() - start
        
        metrics.predictions_total.labels(
            model='cifar10',
            status='success'
        ).inc()
        metrics.prediction_latency.labels(model='cifar10').observe(latency)
        
        return result
    except Exception as e:
        metrics.prediction_errors.labels(
            model='cifar10',
            error_type=type(e).__name__
        ).inc()
        raise
```

### 3. Create Docker Compose File

Save as `docker-compose.monitoring.yml`:

```yaml
version: '3.8'

services:
  # Prometheus - Metrics collection and storage
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_storage:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    networks:
      - monitoring

  # Grafana - Visualization and dashboards
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_USERS_ALLOW_SIGN_UP: "false"
    volumes:
      - grafana_storage:/var/lib/grafana
    networks:
      - monitoring
    depends_on:
      - prometheus

  # Loki - Log aggregation (optional)
  loki:
    image: grafana/loki:latest
    container_name: loki
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yml:/etc/loki/local-config.yaml
      - loki_storage:/loki
    command: -config.file=/etc/loki/local-config.yaml
    networks:
      - monitoring

  # Promtail - Log shipper (optional)
  promtail:
    image: grafana/promtail:latest
    container_name: promtail
    volumes:
      - /var/log:/var/log
      - ./promtail-config.yml:/etc/promtail/config.yml
    command: -config.file=/etc/promtail/config.yml
    networks:
      - monitoring
    depends_on:
      - loki

networks:
  monitoring:
    driver: bridge

volumes:
  prometheus_storage:
  grafana_storage:
  loki_storage:
```

### 4. Create Prometheus Configuration

Save as `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  scrape_timeout: 10s
  evaluation_interval: 15s

# Alert manager for notifications
alerting:
  alertmanagers:
    - static_configs:
        - targets: []

# Load alert rules
rule_files:
  - 'alert_rules.yml'

scrape_configs:
  # Inference Service
  - job_name: 'inference-service'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
    scrape_timeout: 10s

  # Logging Service
  - job_name: 'logging-service'
    static_configs:
      - targets: ['localhost:8001']
    metrics_path: '/metrics'
    scrape_interval: 15s
    scrape_timeout: 10s

  # Prometheus itself
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

### 5. Create Alert Rules

Save as `alert_rules.yml`:

```yaml
groups:
  - name: inference_service
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          (rate(prediction_errors_total[5m]) / 
           rate(predictions_total[5m])) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate in inference service"
          description: |
            Error rate is {{ $value | humanizePercentage }} 
            (expected < 5%)

      # Model not loaded
      - alert: ModelNotLoaded
        expr: model_loaded == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Model failed to load"
          description: "Model {{ $labels.model }} is not loaded"

      # Slow predictions
      - alert: SlowPredictions
        expr: |
          histogram_quantile(0.95, 
            rate(prediction_latency_seconds_bucket[5m])) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow predictions detected"
          description: |
            P95 latency is {{ $value | humanizeDuration }} 
            (expected < 1s)

  - name: logging_service
    interval: 30s
    rules:
      # Database not accessible
      - alert: DatabaseNotAccessible
        expr: logging_db_initialized == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Logging service database not accessible"

      # High defect detection rate
      - alert: HighDefectRate
        expr: |
          (rate(logging_defects_total[5m]) / 
           rate(logging_predictions_total[5m])) > 0.2
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Unusually high defect detection rate"
          description: |
            Defect rate is {{ $value | humanizePercentage }} 
            (expected < 20%)

  - name: system_health
    interval: 30s
    rules:
      # Service down
      - alert: ServiceDown
        expr: up == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "{{ $labels.job }} is down"

      # High HTTP error rate
      - alert: HighHTTPErrorRate
        expr: |
          (rate(http_requests_total{status=~"5.."}[5m]) / 
           rate(http_requests_total[5m])) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High HTTP error rate (5xx)"
```

### 6. Start the Stack

```bash
# Start all services
docker-compose -f docker-compose.monitoring.yml up -d

# Check logs
docker-compose -f docker-compose.monitoring.yml logs -f prometheus

# Verify services are running
docker-compose -f docker-compose.monitoring.yml ps
```

### 7. Configure Grafana

1. Open http://localhost:3000
2. Login with admin/admin
3. Add data source:
   - Type: Prometheus
   - URL: http://prometheus:9090
   - Save & Test
4. Import dashboard:
   - Click "Dashboards" → "Import"
   - Use ID 3662 (Prometheus) or 1860 (Node Exporter)
   - Or create custom dashboard (see examples below)

---

## Creating Dashboards

### Example 1: Inference Service Dashboard

**JSON Model** (Import into Grafana):

```json
{
  "dashboard": {
    "title": "Inference Service",
    "panels": [
      {
        "title": "Predictions/sec",
        "targets": [
          {
            "expr": "rate(predictions_total[1m])"
          }
        ]
      },
      {
        "title": "Latency P95",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(prediction_latency_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "(rate(prediction_errors_total[5m]) / rate(predictions_total[5m]))"
          }
        ]
      },
      {
        "title": "Model Status",
        "targets": [
          {
            "expr": "model_loaded"
          }
        ]
      }
    ]
  }
}
```

### Example 2: Useful PromQL Queries

```promql
# Predictions per second (last 5 minutes)
rate(predictions_total[5m])

# Error rate (percentage)
100 * (rate(prediction_errors_total[5m]) / rate(predictions_total[5m]))

# P99 latency
histogram_quantile(0.99, rate(prediction_latency_seconds_bucket[5m]))

# Predictions by model (stacked)
sum by (model) (rate(predictions_total[5m]))

# Error distribution by error type
sum by (error_type) (rate(prediction_errors_total[5m]))

# Model availability
model_loaded

# Average confidence score
avg(prediction_confidence) by (model)

# Database initialization status
logging_db_initialized

# Defect detection rate
100 * (rate(logging_defects_total[5m]) / rate(logging_predictions_total[5m]))
```

---

## Monitoring Multiple Services

### Kubernetes Deployment

For Kubernetes, use ServiceMonitor:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: inference-service
spec:
  selector:
    matchLabels:
      app: inference
  endpoints:
    - port: metrics
      interval: 15s
```

### Multi-Environment

Use Prometheus Federation:

```yaml
# Central prometheus.yml
scrape_configs:
  - job_name: 'prometheus-prod'
    static_configs:
      - targets: ['prometheus-prod:9090']
  
  - job_name: 'prometheus-staging'
    static_configs:
      - targets: ['prometheus-staging:9090']
```

---

## Best Practices

### Metric Naming
```python
# ✅ Good: Descriptive, follows convention
metrics.predictions_total.labels(...).inc()
metrics.prediction_latency_seconds.labels(...).observe(...)
metrics.model_loaded.labels(...).set(...)

# ❌ Bad: Unclear, no suffix
metrics.total.inc()
metrics.time.observe(...)
metrics.status.set(...)
```

### Label Cardinality
```python
# ✅ Good: Fixed labels, no user input
metrics.predictions_total.labels(model='cifar10', status='success').inc()

# ❌ Bad: Unbounded cardinality
metrics.predictions.labels(request_id=str(uuid.uuid4())).inc()  # Creates millions of series!
```

### Log Levels
```python
logger.debug('...')      # Verbose development info
logger.info('...')       # Important events (predictions, startup)
logger.warning('...')    # Anomalies (slow requests, validation errors)
logger.error('...')      # Failures (exceptions, crashes)
```

---

## Troubleshooting

### Metrics Not Showing

```bash
# 1. Verify metrics endpoint works
curl http://localhost:8000/metrics

# 2. Check Prometheus targets
# Go to http://localhost:9090/targets
# Should see "inference-service" as UP

# 3. Check Prometheus logs
docker logs prometheus

# 4. Verify scrape config
# Should have job_name and targets
grep -A 5 "inference-service" prometheus.yml
```

### High Memory Usage

```bash
# 1. Reduce cardinality of labels
# Remove any metrics with user input, UUIDs, timestamps

# 2. Reduce retention period
# Add to prometheus.yml:
# --storage.tsdb.retention.time=15d

# 3. Use downsampling
# Let Prometheus aggregate older data
```

### Logs Not Appearing in Loki

```bash
# 1. Check Promtail config
docker logs promtail

# 2. Verify service is logging to stdout
# Docker captures stdout automatically

# 3. Check Loki is receiving logs
curl -G -s "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={job="service"}' | jq
```

---

## Quick Reference Commands

```bash
# Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Stop monitoring stack
docker-compose -f docker-compose.monitoring.yml down

# View logs
docker-compose -f docker-compose.monitoring.yml logs -f prometheus

# Check metrics directly
curl http://localhost:8000/metrics

# Query Prometheus
curl 'http://localhost:9090/api/v1/query?query=predictions_total'

# Access UIs
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000
# Loki: (query through Grafana)
```

---

## Summary

✅ **Structured Logging**: JSON format for log aggregation
✅ **Prometheus Metrics**: Industry-standard metrics exposure
✅ **Grafana Dashboards**: Real-time visualization
✅ **Alert Rules**: Automatic notifications
✅ **Log Aggregation**: Optional Loki integration
✅ **Production Ready**: Tested patterns, best practices

Total setup time: ~2 hours for complete stack
Maintenance: Minimal (mostly happens automatically)
Value: Invaluable for production ML services
