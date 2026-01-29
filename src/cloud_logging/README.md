# Async Cloud Logging for Edge Inference

Production-ready Python code for sending prediction results from edge inference services to cloud logging API asynchronously, with batching, retries, and local buffering.

## Architecture

```
┌─────────────────────────────────┐
│   Edge Inference Service        │
│   (YOLO detector)               │
├─────────────────────────────────┤
│  1. Run inference                │
│  2. Send results async           │ ◄──┐
│  3. Return immediately           │    │
└────────────┬──────────────────────┘    │
             │                           │ Non-blocking
             │                           │ (returns immediately)
             ▼                           │
┌─────────────────────────────────┐    │
│  AsyncLoggingClient             │    │
├─────────────────────────────────┤    │
│  - Batch predictions (32x)       │    │
│  - Queue async send              │ ───┘
│  - Retry with backoff            │
│  - Local buffer on failure       │
└────────────┬──────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│  Cloud Logging API               │
│  (FastAPI endpoint)              │
├──────────────────────────────────┤
│  - Receive batch POST            │
│  - Store in database             │
│  - Return 200 OK                 │
└──────────────────────────────────┘
```

## Features

### Edge Client (AsyncLoggingClient)

✅ **Batching** - Groups 32 predictions before sending (configurable)
✅ **Async/Non-Blocking** - Inference returns immediately, logging in background
✅ **Retry Logic** - Exponential backoff (2^n) for failed requests
✅ **Local Buffering** - Persists failed predictions to disk for later retry
✅ **Connection Pooling** - Reuses HTTP connections efficiently
✅ **Graceful Shutdown** - Flushes pending predictions before exit
✅ **Statistics Tracking** - Monitors sent/failed/buffered predictions
✅ **Authentication** - Optional API key support
✅ **Configurable** - All settings via environment variables

### Cloud API (FastAPI)

✅ **Batch Receipt** - Accepts multiple predictions per request
✅ **Database Storage** - SQLite with indexes for fast querying
✅ **Statistics** - Aggregate stats by device and model
✅ **Query Interface** - List predictions with filtering
✅ **Health Check** - /health endpoint for monitoring
✅ **Request Validation** - Pydantic models for data validation

## Installation

```bash
# Install dependencies
pip install aiohttp fastapi uvicorn pydantic

# Or from requirements
pip install -r requirements.txt
```

## Quick Start

### 1. Start Cloud Logging API

```bash
# Terminal 1: Start the cloud API
python -m src.cloud_logging.api

# Expected output:
# INFO:     Uvicorn running on http://0.0.0.0:8001
# INFO:     Application startup complete
```

### 2. Run Edge Inference with Cloud Logging

```bash
# Terminal 2: Run edge inference
python examples/edge_inference_with_cloud_logging.py

# Expected output:
# INFO - EdgeInferenceWithCloudLogging started
# INFO - Processed sample_images/frame_001.jpg: 2 detections, inference: 45.23ms
# INFO - Processed sample_images/frame_002.jpg: 0 detections, inference: 43.12ms
# INFO - Cloud logging stats: {'sent': 2, 'failed': 0, 'retried': 0, 'buffered': 0}
```

### 3. Query Results

```bash
# Get statistics
curl http://localhost:8001/stats | jq

# Get recent predictions
curl "http://localhost:8001/predictions?limit=10" | jq

# Filter by edge device
curl "http://localhost:8001/predictions?edge_device_id=factory-camera-01" | jq
```

## Usage Examples

### Basic Usage

```python
import asyncio
from src.cloud_logging.async_client import AsyncLoggingClient, PredictionResult

async def main():
    async with AsyncLoggingClient(
        api_endpoint="http://logging-service:8001/log",
        edge_device_id="factory-camera-01",
    ) as client:
        
        # Create a prediction
        prediction = PredictionResult(
            image_id="img_001",
            timestamp=time.time(),
            model_version="v1.0",
            model_name="yolov8",
            inference_time_ms=45.2,
            detections=[
                {
                    "class": "defect",
                    "confidence": 0.95,
                    "bbox": [100, 100, 200, 200],
                }
            ],
            defect_detected=True,
            confidence_scores=[0.95],
        )
        
        # Send asynchronously (non-blocking)
        await client.log_prediction(prediction)
        
        # Do other work while prediction is being sent...
        
        # Shutdown flushes pending predictions
        await client.shutdown()

asyncio.run(main())
```

### Integration with YOLO Detector

```python
import asyncio
from src.cloud_logging.edge_integration import EdgeInferenceWithCloudLogging

async def main():
    service = EdgeInferenceWithCloudLogging(
        yolo_model_path="yolov8n.pt",
        cloud_api_endpoint="http://logging-service:8001/log",
        edge_device_id="factory-camera-01",
    )
    
    await service.start()
    
    try:
        # Process image and automatically log to cloud
        result = await service.process_image_async("defect_image.jpg")
        print(result)
        # Output:
        # {
        #     "image_id": "defect_image",
        #     "detections": [...],
        #     "defect_detected": True,
        #     "inference_time_ms": 45.23,
        #     "logged_to_cloud": True
        # }
    finally:
        await service.shutdown()

asyncio.run(main())
```

### With Configuration from Environment

```bash
# Set environment variables
export CLOUD_LOGGING_ENDPOINT="http://logging-service:8001/log"
export BATCH_SIZE=32
export BATCH_TIMEOUT_SECONDS=10
export EDGE_DEVICE_ID="factory-camera-01"
export BUFFER_FILE="/tmp/prediction_buffer.jsonl"
```

```python
from src.cloud_logging.config import get_config
from src.cloud_logging.edge_integration import EdgeInferenceWithCloudLogging

config = get_config()

service = EdgeInferenceWithCloudLogging(
    cloud_api_endpoint=config.api_endpoint,
    batch_size=config.batch_size,
    batch_timeout_seconds=config.batch_timeout_seconds,
    edge_device_id=config.edge_device_id,
    buffer_file=config.buffer_file,
)

# Use service...
```

## Configuration

All settings can be configured via environment variables:

```bash
# Cloud API
CLOUD_LOGGING_ENDPOINT=http://logging-service:8001/log
CLOUD_LOGGING_API_KEY=optional-api-key
CLOUD_LOGGING_ENABLED=true

# Batching
BATCH_SIZE=32                      # Predictions per batch
BATCH_TIMEOUT_SECONDS=10           # Max wait before sending

# Retry
MAX_RETRIES=3                      # Retry attempts
RETRY_BACKOFF_MULTIPLIER=2.0       # Exponential backoff factor
TIMEOUT_SECONDS=30                 # Request timeout

# Local buffering
BUFFER_FILE=/app/data/buffer.jsonl # Persist failed predictions

# Edge device
EDGE_DEVICE_ID=edge-device-01      # Device identifier
```

## Performance

### Batching Impact

```
Without batching (send per prediction):
- Network overhead: High (1 HTTP request per prediction)
- Latency per prediction: ~100-300ms
- CPU usage: High

With batching (32 predictions per batch):
- Network overhead: Low (1 HTTP request per 32 predictions)
- Latency per prediction: <1ms (async, non-blocking)
- CPU usage: Very low
- Throughput: ~32 predictions per batch timeout
```

### Inference Returns Immediately

```python
# Inference completes in ~45ms
# Cloud logging happens in background

start = time.time()
result = await service.process_image_async("image.jpg")
elapsed = time.time() - start

print(f"Inference + return: {elapsed*1000:.2f}ms")
# Output: Inference + return: 1.23ms (not blocked by logging)
```

## Deployment

### Docker

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache -r requirements.txt

COPY . .

ENV CLOUD_LOGGING_ENDPOINT=http://logging-service:8001/log
ENV BATCH_SIZE=32
ENV EDGE_DEVICE_ID=edge-device-01

CMD ["python", "examples/edge_inference_with_cloud_logging.py"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: edge-inference
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: inference
          image: edge-inference:latest
          env:
            - name: CLOUD_LOGGING_ENDPOINT
              value: "http://logging-service:8001/log"
            - name: BATCH_SIZE
              value: "32"
            - name: EDGE_DEVICE_ID
              value: "edge-device-01"
            - name: BUFFER_FILE
              value: "/app/data/buffer.jsonl"
          volumeMounts:
            - name: buffer-storage
              mountPath: /app/data
      volumes:
        - name: buffer-storage
          emptyDir: {}
```

## Monitoring

### Cloud API Statistics

```bash
# Check total predictions and defect rate
curl http://localhost:8001/stats | jq '.defects_detected / .total_predictions'

# Monitor by device
curl http://localhost:8001/stats | jq '.by_edge_device'
```

### Client Statistics

```python
service = EdgeInferenceWithCloudLogging(...)
await service.start()

# ... process images ...

stats = service.get_cloud_logging_stats()
print(stats)
# Output:
# {
#     'sent': 128,
#     'failed': 0,
#     'retried': 2,
#     'buffered': 0,
# }
```

### Buffered Predictions

```bash
# Check buffered predictions (if network failed)
tail -f /app/data/prediction_buffer.jsonl | jq

# Each line is a JSON prediction
# When connection is restored, client retries automatically
```

## Testing

```bash
# Run unit tests
pytest tests/test_async_cloud_logging.py -v

# With coverage
pytest tests/test_async_cloud_logging.py --cov=src.cloud_logging

# Run async tests
pytest tests/test_async_cloud_logging.py -v -m asyncio
```

## Troubleshooting

### Predictions not reaching cloud

```python
# Check local buffer
cat /app/data/prediction_buffer.jsonl | wc -l

# Check client stats
stats = service.get_cloud_logging_stats()
if stats['buffered'] > 0:
    print("Predictions buffered locally, waiting for network recovery")

# Check cloud API logs
docker logs <cloud-logging-container>
```

### High latency for inference

```python
# Check if client is blocking
# Inference should return in <10ms
elapsed = time.time() - start
assert elapsed < 0.010, f"Inference blocked by logging: {elapsed*1000}ms"

# If slow, check:
# - Batch size (increase it)
# - Network latency (reduce timeout)
# - CPU load (reduce model size)
```

### Connection refused

```bash
# Verify cloud API is running
curl http://localhost:8001/health

# Check endpoint in edge service
CLOUD_LOGGING_ENDPOINT=http://logging-service:8001/log

# Verify networking (in Kubernetes)
kubectl exec -it <edge-pod> -- curl http://logging-service:8001/health
```

## Advanced Usage

### Custom Batching Logic

```python
from src.cloud_logging.async_client import AsyncLoggingClient

client = AsyncLoggingClient(
    api_endpoint="...",
    batch_size=64,           # Larger batches
    batch_timeout_seconds=5,  # Flush every 5 seconds
)
```

### Retry Configuration

```python
client = AsyncLoggingClient(
    api_endpoint="...",
    max_retries=5,                    # More retries
    retry_backoff_multiplier=1.5,     # Slower backoff (1.5s, 2.25s, 3.375s)
)
```

### API Key Authentication

```python
client = AsyncLoggingClient(
    api_endpoint="...",
    api_key="your-secret-key",
)
# Client automatically adds: Authorization: Bearer your-secret-key
```

### Local Buffering with Persistence

```python
client = AsyncLoggingClient(
    api_endpoint="...",
    buffer_file="/persistent/storage/predictions.jsonl",
)
# Failed predictions are saved to disk
# Automatically retried when service restarts
```

## Architecture Diagrams

### Request Flow

```
┌─────────────┐
│  Image      │
└──────┬──────┘
       │
       ▼
┌──────────────────────┐
│ YOLO Inference       │
│ (blocking, ~45ms)    │
└──────┬───────────────┘
       │
       ├─► Return results immediately (non-blocking)
       │
       └─► Queue prediction to AsyncLoggingClient
           │
           ├─► Add to batch (in-memory)
           │
           ├─► When batch full OR timeout:
           │   └─► POST to cloud API
           │       ├─► Success: Update stats
           │       ├─► Failure: Retry with backoff
           │       │   └─► Max retries exceeded: Buffer to disk
           │
           └─► Graceful shutdown: Flush all pending
```

### Data Flow

```
Edge Device                           Cloud
┌─────────────────────┐              ┌──────────────────┐
│ Image 1             │              │                  │
│ Image 2             │  Batch 1     │  Cloud API       │
│ Image 3             ├─────────────►│ (32 predictions) │
│ ...                 │   (async)    │                  │
│ Image 32            │              │  SQLite DB       │
└─────────────────────┘              │  [predictions]   │
         │                           │  [statistics]    │
         │ Non-blocking              │                  │
         │ (returns immediately)     └──────────────────┘
         ▼
 Process continues...
```

## License

MIT - See LICENSE file for details
