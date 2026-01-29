# Structured Logging & Prometheus Metrics - Complete Guide

A comprehensive guide to adding production-grade monitoring to Python ML microservices.

---

## 📚 Documentation Overview

### Quick Start (15 minutes)
**→ [QUICK_START_MONITORING.md](QUICK_START_MONITORING.md)**
- Get metrics exposing in 5 minutes
- Add to your endpoints in 10 minutes
- View metrics immediately
- **Best for**: Just want it working

### Learning Guide (1 hour)
**→ [LOGGING_AND_METRICS_GUIDE.md](LOGGING_AND_METRICS_GUIDE.md)**
- How structured logging works
- Available metrics
- Integration patterns
- Common pitfalls
- **Best for**: Understanding the concepts

### Before/After Comparison
**→ [BEFORE_AFTER_MONITORING.md](BEFORE_AFTER_MONITORING.md)**
- Why monitoring matters
- Real-world impact
- Migration path
- Cost/benefit analysis
- **Best for**: Convincing stakeholders

### Complete Production Stack
**→ [COMPLETE_MONITORING_SETUP.md](COMPLETE_MONITORING_SETUP.md)**
- Docker Compose setup
- Prometheus configuration
- Grafana dashboards
- Alert rules
- Kubernetes integration
- **Best for**: Enterprise deployments

### Practical Example Code
**→ [examples/inference_service_with_logging.py](examples/inference_service_with_logging.py)**
- Complete working example
- Shows all patterns
- Ready to copy/paste
- **Best for**: Implementation reference

### Core Library
**→ [src/monitoring/structured_logging.py](src/monitoring/structured_logging.py)**
- All utilities pre-built
- Production-ready code
- Fully documented
- **Best for**: Integration

---

## 🎯 What You'll Learn

### Structured Logging
Transform logs from:
```
Prediction received for [0.1, 0.2, ...]
Result: {'class': 3, 'confidence': 0.95}
```

To:
```json
{
  "timestamp": "2026-01-28T15:30:45.123456",
  "message": "prediction_successful",
  "model": "cifar10",
  "latency_seconds": 0.125,
  "confidence": 0.95,
  "service": "inference"
}
```

✅ Parseable by log aggregation tools
✅ Searchable and filterable
✅ Context-rich for debugging
✅ Works with all log platforms (ELK, Loki, Datadog, etc.)

### Prometheus Metrics
Expose metrics that services scrape:
```
# HELP predictions_total Total predictions served
# TYPE predictions_total counter
predictions_total{model="cifar10",status="success"} 1523

# HELP prediction_latency_seconds Prediction latency
# TYPE prediction_latency_seconds histogram
prediction_latency_seconds_bucket{le="0.1"} 1400
prediction_latency_seconds_sum 145.23
prediction_latency_seconds_count 1523
```

✅ Industry standard format
✅ Works with Prometheus, Grafana, Datadog, etc.
✅ Histogram buckets for percentile analysis
✅ Auto-scraping every 15 seconds

---

## 🚀 Quick Overview

### 3-Liner Setup
```python
from src.monitoring.structured_logging import (
    setup_structured_logging,
    MetricsRegistry,
)

logger = setup_structured_logging('my-service')
metrics = MetricsRegistry('my-service')
```

### Metrics Endpoint
```python
@app.get('/metrics')
def metrics():
    from prometheus_client import generate_latest
    return generate_latest(metrics.registry)
```

### In Your Code
```python
import time

start = time.time()
result = model.predict(data)
latency = time.time() - start

# Log it
logger.info('prediction_successful', extra={
    'latency_seconds': latency,
    'confidence': result['confidence'],
})

# Metric it
metrics.predictions_total.labels(status='success').inc()
metrics.prediction_latency.labels(model='cifar10').observe(latency)
```

---

## 📊 Monitoring Levels

### Level 1: Structured Logging (15 min)
```python
logger.info('event', extra={'field': 'value'})
```
- Logs as JSON to stdout
- Works with Docker/Kubernetes
- No external dependencies
- ~5 minutes to implement

### Level 2: Local Metrics (30 min)
```python
@app.get('/metrics')
def metrics():
    return generate_latest(metrics.registry)
```
- Expose Prometheus metrics
- View with curl or browser
- No infrastructure needed
- ~10 minutes to implement

### Level 3: Prometheus (1 hour)
```bash
docker run -p 9090:9090 -v prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus
```
- Automatic metric scraping
- Time-series database
- PromQL queries
- ~15 minutes to setup

### Level 4: Grafana (1.5 hours)
```bash
docker run -p 3000:3000 grafana/grafana
```
- Visual dashboards
- Real-time graphs
- Alerting
- ~30 minutes to setup

### Level 5: Log Aggregation (2 hours)
```bash
docker-compose -f docker-compose.monitoring.yml up
```
- Centralized logs
- Full ELK/Loki stack
- Log searching
- ~30 minutes to setup

---

## 💡 Real-World Example

### The Problem
You deploy a new model. Performance degrades. You don't know why.

**Without monitoring**:
- Manual log analysis: 1-2 hours
- Deploy in dark: hope it works
- Post-mortem analysis: days later
- Pattern recognition: nearly impossible

**With this setup**:
- Prometheus alert: instant
- Grafana graph: shows exact issue
- Check logs in Loki: root cause in 5 min
- Rollback or fix: immediate

---

## 🎯 Use Cases

### 1. Model Performance Monitoring
```promql
# Model degradation
histogram_quantile(0.95, rate(prediction_latency_seconds_bucket[5m]))

# Confidence distribution
avg(prediction_confidence) by (model)

# Error rate
rate(prediction_errors_total[5m]) / rate(predictions_total[5m])
```

### 2. Data Quality Tracking
```promql
# Invalid inputs
rate(input_validation_errors_total[1m])

# Defect detection rate
rate(logging_defects_total[1m]) / rate(logging_predictions_total[1m])
```

### 3. Service Health
```promql
# Model availability
model_loaded

# Database status
logging_db_initialized

# HTTP errors
rate(http_requests_total{status=~"5.."}[5m])
```

### 4. Capacity Planning
```promql
# Throughput trend
rate(predictions_total[1h]) offset 24h

# Peak hour predictions
max_over_time(rate(predictions_total[5m])[1d:5m])
```

---

## 📈 Metrics Available

### Pre-configured Metrics

**Prediction Metrics**:
- `predictions_total` - Total predictions (success/error)
- `prediction_latency_seconds` - Response time histogram
- `prediction_confidence` - Confidence score distribution
- `prediction_errors_total` - Error count by type

**Model Metrics**:
- `model_loaded` - Model availability gauge
- `model_load_time_seconds` - Startup time histogram

**HTTP Metrics**:
- `http_requests_total` - Request count by method/status
- `http_request_latency_seconds` - Request latency

**Data Quality**:
- `input_validation_errors_total` - Invalid inputs
- `service_info` - Service metadata

---

## 🔧 Implementation Path

### Day 1: Basic Monitoring (1 hour)
1. Install dependencies: 5 min
2. Add structured logging: 10 min
3. Add metrics endpoint: 10 min
4. Instrument key endpoints: 20 min
5. Test locally: 10 min

**Result**: JSON logs + metrics endpoint

### Day 2-3: Local Analysis (2 hours)
1. Add Prometheus: 15 min
2. Create initial dashboard: 30 min
3. Set up log viewer: 15 min
4. Define key queries: 30 min
5. Train team: 30 min

**Result**: Dashboard visibility, query capability

### Day 4-7: Production Readiness (4 hours)
1. Containerize stack: 30 min
2. Configure alerts: 1 hour
3. Set up notifications: 30 min
4. Create runbooks: 1 hour
5. Load test: 1 hour

**Result**: Enterprise-ready monitoring

---

## 🎓 Learning Resources

### Concepts
- Structured Logging: JSON format for machine parsing
- Prometheus: Pull-based metrics collection
- Histogram: Distribution of values (latency, size, etc.)
- Gauge: Single number that can go up/down
- Counter: Number that only increases
- Labels: Dimensions for filtering metrics
- PromQL: Query language for Prometheus

### Tools
- `prometheus_client`: Python library
- `python-json-logger`: JSON logging
- `fastapi`: Web framework
- `prometheus`: Metrics server
- `grafana`: Visualization
- `loki`: Log aggregation

### Integrations
- Kubernetes: ServiceMonitor for scraping
- Docker: Automatic stdout logging
- Datadog: Built-in prometheus scraper
- New Relic: Prometheus integration
- AWS CloudWatch: Custom metrics

---

## ✅ Success Criteria

After implementing monitoring, you should be able to:

1. **See in Real-Time**
   - ✅ Current prediction throughput
   - ✅ Current error rate
   - ✅ Current latency (p50, p95, p99)
   - ✅ Model availability

2. **Analyze Trends**
   - ✅ Prediction volume over time
   - ✅ Latency trends
   - ✅ Error rate trends
   - ✅ Model performance degradation

3. **Debug Issues**
   - ✅ Search logs by service/model/error
   - ✅ Find correlation between metrics
   - ✅ Identify unusual patterns
   - ✅ Trace requests through system

4. **Automate Responses**
   - ✅ Alert on high error rate
   - ✅ Alert on slow predictions
   - ✅ Alert on model unavailable
   - ✅ Automatic incident creation

---

## 📋 Checklist

- [ ] Install dependencies
- [ ] Create monitoring module
- [ ] Add logger to services
- [ ] Add metrics registry to services
- [ ] Add /metrics endpoint
- [ ] Instrument prediction endpoint
- [ ] Log startup/shutdown events
- [ ] Log errors with context
- [ ] Test metrics locally
- [ ] Set up Prometheus
- [ ] Create Grafana dashboard
- [ ] Define alert rules
- [ ] Configure notifications
- [ ] Document runbooks
- [ ] Train team

---

## 🎯 Next Steps

### Immediate (Today)
1. Read [QUICK_START_MONITORING.md](QUICK_START_MONITORING.md)
2. Add 3-liner setup to your service
3. Instrument one endpoint
4. Verify `/metrics` endpoint works

### Short Term (This Week)
1. Instrument all endpoints
2. Set up Prometheus locally
3. Create basic dashboard
4. Document key metrics

### Medium Term (This Month)
1. Deploy to production
2. Set up alerts
3. Configure log aggregation
4. Train team on dashboards

---

## 📞 Support

### Common Questions

**Q: Does this add latency?**
A: Negligible (<1ms per request). Measuring itself is cheap.

**Q: What about cardinality explosion?**
A: Use fixed labels only (model, endpoint, status). Never user input or timestamps.

**Q: Can I use this with Kubernetes?**
A: Yes, perfect fit. ServiceMonitor handles scraping automatically.

**Q: What about existing logging?**
A: Keep it. Structured logging works alongside print() and logging module.

**Q: How much storage do metrics need?**
A: ~1GB per month for moderate volume. Very efficient.

**Q: Can I add more metrics later?**
A: Yes, add whenever you need. No migration needed.

### Getting Help

1. **Quick answers**: See [QUICK_START_MONITORING.md](QUICK_START_MONITORING.md)
2. **How-to guides**: See [LOGGING_AND_METRICS_GUIDE.md](LOGGING_AND_METRICS_GUIDE.md)
3. **Setup help**: See [COMPLETE_MONITORING_SETUP.md](COMPLETE_MONITORING_SETUP.md)
4. **Code examples**: See [examples/inference_service_with_logging.py](examples/inference_service_with_logging.py)
5. **Reference**: See [src/monitoring/structured_logging.py](src/monitoring/structured_logging.py)

---

## 🎉 Summary

**Structured logging + Prometheus metrics** enables:

✅ **Visibility**: See what's happening in your service
✅ **Debugging**: Find root causes quickly
✅ **Trending**: Detect degradation early
✅ **Alerting**: Know about problems immediately
✅ **Scaling**: Understand when you need more capacity
✅ **Learning**: Data-driven decisions

**Effort**: ~15 minutes to get started
**Value**: Invaluable for production systems
**Best Practices**: All included

---

## 📖 Full Documentation List

1. **[QUICK_START_MONITORING.md](QUICK_START_MONITORING.md)** - Get running in 15 min
2. **[LOGGING_AND_METRICS_GUIDE.md](LOGGING_AND_METRICS_GUIDE.md)** - Complete learning guide
3. **[BEFORE_AFTER_MONITORING.md](BEFORE_AFTER_MONITORING.md)** - Why monitoring matters
4. **[COMPLETE_MONITORING_SETUP.md](COMPLETE_MONITORING_SETUP.md)** - Production stack
5. **[examples/inference_service_with_logging.py](examples/inference_service_with_logging.py)** - Working example
6. **[src/monitoring/structured_logging.py](src/monitoring/structured_logging.py)** - Core library

---

**Start with [QUICK_START_MONITORING.md](QUICK_START_MONITORING.md) →**
