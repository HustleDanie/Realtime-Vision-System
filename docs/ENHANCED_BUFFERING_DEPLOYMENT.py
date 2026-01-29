"""
Deployment and Configuration Guide for Enhanced Buffering System

This guide explains how to deploy and manage the enhanced async logging client
with local buffering and automatic recovery capabilities.
"""

# ============================================================================
# DEPLOYMENT GUIDE: Enhanced Buffering System
# ============================================================================
#
# The system consists of 3 main components:
#
# 1. LocalBufferManager: SQLite-based persistent buffer
#    - Survives process crashes
#    - FIFO with priority (most recent predictions sent first)
#    - Automatic cleanup of old sent predictions
#    - Space management (warns at 90% capacity)
#
# 2. BufferRecoveryManager: Background recovery loop
#    - Automatically retries buffered predictions when connectivity restored
#    - Batches predictions for efficiency
#    - Tracks recovery status and statistics
#
# 3. EnhancedAsyncLoggingClient: Extended AsyncLoggingClient
#    - Dual buffering (disk + memory for reliability + performance)
#    - Connectivity monitoring (checks cloud API every 30s)
#    - Automatic recovery triggering
#    - Graceful shutdown with buffer preservation
#
# ============================================================================


# SECTION 1: BASIC DEPLOYMENT
# ============================================================================

"""
Step 1: Configure environment variables

Set these in your deployment environment (.env, docker-compose, k8s ConfigMap):

# Cloud logging endpoint
CLOUD_LOGGING_ENDPOINT=http://logging-service:8001/log

# Buffer configuration
BUFFER_DB_PATH=/data/prediction_buffer.db
BUFFER_MAX_SIZE_MB=500
BUFFER_CLEANUP_DAYS=7

# Client configuration
EDGE_DEVICE_ID=factory-camera-01
API_KEY=your-api-key-here

# Batch settings
BATCH_SIZE=32
BATCH_TIMEOUT_SECONDS=10
"""

# Step 2: Initialize and start the client

import asyncio
from src.cloud_logging.enhanced_client import EnhancedAsyncLoggingClient
from src.cloud_logging.buffer_monitor import BufferMonitor


async def deploy_edge_inference():
    """Example: Deploy edge inference with buffering"""
    
    # Initialize client with persistent buffer
    client = EnhancedAsyncLoggingClient(
        api_endpoint="http://logging-service:8001/log",
        edge_device_id="factory-camera-01",
        buffer_db_path="/data/prediction_buffer.db",
        max_buffer_size_mb=500,
        cleanup_after_days=7,
    )
    
    # Start client (initializes buffer, starts monitors)
    await client.start()
    
    # Optional: Start monitoring
    monitor = BufferMonitor(client.buffer_manager, client)
    await monitor.start(interval_seconds=30)
    
    try:
        # ... run your inference loop ...
        pass
    finally:
        # Graceful shutdown
        await monitor.stop()
        await client.shutdown()


# ============================================================================
# SECTION 2: DOCKER DEPLOYMENT
# ============================================================================

"""
Dockerfile snippet for edge inference service with buffering:

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create persistent volume mount point
RUN mkdir -p /data && chmod 777 /data

COPY src/ ./src/
COPY scripts/ ./scripts/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run with buffering enabled
ENV BUFFER_DB_PATH=/data/prediction_buffer.db
ENV BUFFER_MAX_SIZE_MB=500

CMD ["python", "-m", "scripts.run_edge_service"]

---

docker-compose.yml:

services:
  edge-inference:
    build: .
    environment:
      CLOUD_LOGGING_ENDPOINT: http://logging-service:8001/log
      BUFFER_DB_PATH: /data/prediction_buffer.db
      BUFFER_MAX_SIZE_MB: 500
      BUFFER_CLEANUP_DAYS: 7
      EDGE_DEVICE_ID: factory-camera-01
    volumes:
      - edge-buffer:/data  # Persistent volume for buffer
    depends_on:
      - logging-service
    restart: unless-stopped
    
  logging-service:
    build: ./src/cloud_logging
    ports:
      - "8001:8001"
    environment:
      DATABASE_URL: sqlite:////data/predictions.db
    volumes:
      - logging-data:/data
    restart: unless-stopped

volumes:
  edge-buffer:
  logging-data:
"""


# ============================================================================
# SECTION 3: KUBERNETES DEPLOYMENT
# ============================================================================

"""
Kubernetes StatefulSet for edge inference with buffering:

apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: edge-inference
spec:
  serviceName: edge-inference
  replicas: 1
  selector:
    matchLabels:
      app: edge-inference
  template:
    metadata:
      labels:
        app: edge-inference
    spec:
      containers:
      - name: inference
        image: registry.example.com/edge-inference:latest
        ports:
        - containerPort: 8000
        env:
        - name: CLOUD_LOGGING_ENDPOINT
          value: http://logging-service:8001/log
        - name: BUFFER_DB_PATH
          value: /data/prediction_buffer.db
        - name: BUFFER_MAX_SIZE_MB
          value: "500"
        - name: EDGE_DEVICE_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        volumeMounts:
        - name: buffer-storage
          mountPath: /data
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
  volumeClaimTemplates:
  - metadata:
      name: buffer-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 1Gi  # 1GB for buffer storage
"""


# ============================================================================
# SECTION 4: CONFIGURATION REFERENCE
# ============================================================================

"""
LocalBufferManager Configuration:

db_path: str
    - Path to SQLite database
    - Should be on persistent storage
    - Default: /data/prediction_buffer.db

max_size_mb: int
    - Maximum buffer size in megabytes
    - Warnings trigger at 90% capacity
    - Default: 500 MB

cleanup_after_days: int
    - Delete sent predictions older than N days
    - Reduces database size over time
    - Default: 7 days

---

EnhancedAsyncLoggingClient Configuration:

api_endpoint: str
    - Cloud logging API endpoint
    - Example: http://logging-service:8001/log

edge_device_id: str
    - Unique identifier for this edge device
    - Used for tracking and monitoring

buffer_db_path: str
    - Path to persistent buffer database

max_buffer_size_mb: int
    - Maximum buffer size in MB

cleanup_after_days: int
    - Cleanup age in days

batch_size: int
    - Number of predictions per batch
    - Default: 32

batch_timeout_seconds: int
    - Maximum time to wait before sending batch
    - Default: 10 seconds

api_key: str (optional)
    - API authentication key
"""


# ============================================================================
# SECTION 5: MONITORING AND DEBUGGING
# ============================================================================

"""
BufferMonitor provides operational visibility:

from src.cloud_logging.buffer_monitor import BufferMonitor

monitor = BufferMonitor(buffer_manager, client)
await monitor.start(interval_seconds=30)  # Check every 30 seconds

# Get status
status = await monitor.get_full_status()
# Returns: {
#   'timestamp': '2025-01-28T10:30:45.123456',
#   'buffer_stats': {
#     'pending': 45,
#     'sent': 1250,
#     'failed': 3,
#     'total_buffered': 1298,
#     'size_mb': 12.5,
#     'capacity_mb': 500,
#     'capacity_percent': 2.5
#   },
#   'client_stats': {
#     'sent_batches': 42,
#     'failed_batches': 2,
#     'is_connected': False,
#     'last_connectivity_check': '2025-01-28T10:30:30.123456'
#   }
# }

# Print formatted status
await monitor.print_status()

# Export statistics to JSON
from src.cloud_logging.buffer_monitor import export_buffer_statistics
await export_buffer_statistics('/data/prediction_buffer.db', '/tmp/buffer_stats.json')

# Reset failed predictions for retry
from src.cloud_logging.buffer_monitor import reset_failed_predictions
await reset_failed_predictions('/data/prediction_buffer.db')

# Repair buffer database (integrity check + VACUUM)
from src.cloud_logging.buffer_monitor import repair_buffer_database
await repair_buffer_database('/data/prediction_buffer.db')
"""


# ============================================================================
# SECTION 6: PRODUCTION CHECKLIST
# ============================================================================

"""
Before deploying to production:

☐ Configure persistent storage volume for buffer
  - Minimum 500MB recommended
  - Use high-reliability storage (not local disk)
  - Enable backups

☐ Set buffer size limits appropriately
  - max_buffer_size_mb: Based on available disk
  - cleanup_after_days: Balance retention vs storage

☐ Enable monitoring
  - Start BufferMonitor
  - Setup alerts for buffer thresholds:
    * Alert if pending > 1000
    * Alert if size > 90% capacity
    * Alert if failed > 100

☐ Configure health checks
  - Liveness probe: /health endpoint
  - Readiness probe: Check both inference and connectivity

☐ Setup logging
  - Enable INFO level for buffer operations
  - Setup centralized log aggregation

☐ Test failure scenarios
  - Simulate network failure (disconnect cloud API)
  - Verify predictions buffer to disk
  - Verify automatic recovery when connectivity restored
  - Test graceful shutdown with buffered predictions

☐ Setup runbooks
  - How to manually trigger recovery
  - How to cleanup old buffer data
  - How to repair corrupted buffer
  - How to export statistics for analysis

☐ Performance validation
  - Latency of log_prediction() (should be <5ms)
  - Throughput (predictions/sec)
  - Memory usage with buffering enabled
  - Disk usage growth rate
"""


# ============================================================================
# SECTION 7: TROUBLESHOOTING
# ============================================================================

"""
Issue: Predictions not reaching cloud API

Diagnosis:
1. Check connectivity status:
   status = await client.get_buffer_status()
   print(f"Connected: {status['is_connected']}")

2. Check buffer stats:
   stats = await client.buffer_manager.get_stats()
   print(f"Pending: {stats['pending']}, Failed: {stats['failed']}")

3. Check recent errors:
   batch = await client.buffer_manager.get_batch(batch_size=1)
   print(f"Last error: {batch[0]['last_error']}")

Solutions:
- Verify cloud API endpoint is reachable
- Check network connectivity from edge device
- Verify API key/authentication
- Check API rate limits

---

Issue: Buffer growing too large

Diagnosis:
1. Get buffer stats:
   stats = await client.buffer_manager.get_stats()
   print(f"Size: {stats['size_mb']}MB, Capacity: {stats['capacity_percent']}%")

2. Check if recovery is running:
   recovery_status = client.recovery_manager.get_recovery_status()
   print(f"Recovering: {recovery_status['is_recovering']}")

Solutions:
- Manually trigger cleanup:
  await client.buffer_manager.cleanup(force=True)
  
- Increase max_buffer_size_mb
- Ensure cloud API is reachable and responsive
- Check for sending failures: reset failed predictions
  
  from src.cloud_logging.buffer_monitor import reset_failed_predictions
  await reset_failed_predictions(buffer_db_path)

---

Issue: Memory usage too high

Diagnosis:
- In-memory batch size may be large
- Check number of pending predictions

Solutions:
- Reduce batch_size (default: 32)
- Increase batch_timeout_seconds to flush more frequently
- Enable buffer cleanup more frequently

---

Issue: Database corrupted or slow

Diagnosis:
1. Run integrity check:
   from src.cloud_logging.buffer_monitor import repair_buffer_database
   await repair_buffer_database(buffer_db_path)

Solutions:
- Repair and VACUUM database:
  from src.cloud_logging.buffer_monitor import repair_buffer_database
  await repair_buffer_database(buffer_db_path)

- Alternatively, recreate buffer:
  rm /data/prediction_buffer.db
  # Client will recreate on next start
"""


# ============================================================================
# SECTION 8: PERFORMANCE TUNING
# ============================================================================

"""
Batch Size Tuning (batch_size parameter):
- Smaller (8-16): Lower latency, more API calls
- Medium (32): Good balance (DEFAULT)
- Larger (64-128): Higher throughput, more memory

Batch Timeout Tuning (batch_timeout_seconds parameter):
- Shorter (3-5s): More responsive, more frequent API calls
- Medium (10s): Good balance (DEFAULT)
- Longer (30s): Higher throughput, less responsive

Buffer Size Tuning (max_buffer_size_mb parameter):
- Small (100-200MB): Limited offline tolerance
- Medium (500MB): Good balance (DEFAULT)
- Large (1GB+): Extended offline tolerance, more storage

Recovery Batch Size (in BufferRecoveryManager):
- Smaller batches: Lower memory spike during recovery
- Larger batches: Faster recovery

Example: High-throughput edge device

client = EnhancedAsyncLoggingClient(
    api_endpoint="http://logging-service:8001/log",
    batch_size=64,  # Larger batch
    batch_timeout_seconds=20,  # Longer timeout
    max_buffer_size_mb=1000,  # More buffer
)

Example: Low-latency edge device

client = EnhancedAsyncLoggingClient(
    api_endpoint="http://logging-service:8001/log",
    batch_size=16,  # Smaller batch
    batch_timeout_seconds=3,  # Shorter timeout
    max_buffer_size_mb=200,  # Less buffer
)

Example: Unreliable network edge device

client = EnhancedAsyncLoggingClient(
    api_endpoint="http://logging-service:8001/log",
    batch_size=32,
    batch_timeout_seconds=10,
    max_buffer_size_mb=2000,  # Extra buffer for offline periods
    cleanup_after_days=30,  # Keep data longer
)
"""


# ============================================================================
# SECTION 9: INTEGRATION WITH KUBERNETES
# ============================================================================

"""
Complete K8s deployment with enhanced buffering:

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: edge-inference-config
data:
  CLOUD_LOGGING_ENDPOINT: http://logging-service:8001/log
  BATCH_SIZE: "32"
  BATCH_TIMEOUT_SECONDS: "10"
  BUFFER_MAX_SIZE_MB: "500"
  BUFFER_CLEANUP_DAYS: "7"
  CONNECTIVITY_CHECK_INTERVAL: "30"
  
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: edge-inference
spec:
  replicas: 1
  selector:
    matchLabels:
      app: edge-inference
  template:
    metadata:
      labels:
        app: edge-inference
    spec:
      containers:
      - name: inference
        image: edge-inference:latest
        imagePullPolicy: Always
        
        ports:
        - containerPort: 8000
          name: http
        
        envFrom:
        - configMapRef:
            name: edge-inference-config
        
        env:
        - name: EDGE_DEVICE_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        
        - name: BUFFER_DB_PATH
          value: /data/prediction_buffer.db
        
        resources:
          requests:
            memory: "256Mi"
            cpu: "500m"
          limits:
            memory: "512Mi"
            cpu: "2000m"
        
        volumeMounts:
        - name: buffer-storage
          mountPath: /data
        
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 15
          periodSeconds: 30
          timeoutSeconds: 5
          failureThreshold: 3
        
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 2
        
        startupProbe:
          httpGet:
            path: /health
            port: 8000
          failureThreshold: 30
          periodSeconds: 1
      
      volumes:
      - name: buffer-storage
        persistentVolumeClaim:
          claimName: edge-buffer-pvc
  
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: edge-buffer-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi

---
apiVersion: v1
kind: Service
metadata:
  name: edge-inference
spec:
  selector:
    app: edge-inference
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
"""


# ============================================================================
# SECTION 10: MIGRATION FROM BASE CLIENT
# ============================================================================

"""
Migrating from AsyncLoggingClient to EnhancedAsyncLoggingClient:

Before (without buffering):
    from src.cloud_logging.async_client import AsyncLoggingClient
    
    client = AsyncLoggingClient(
        api_endpoint="http://logging-service:8001/log"
    )

After (with buffering):
    from src.cloud_logging.enhanced_client import EnhancedAsyncLoggingClient
    
    client = EnhancedAsyncLoggingClient(
        api_endpoint="http://logging-service:8001/log",
        buffer_db_path="/data/prediction_buffer.db",
        max_buffer_size_mb=500,
    )

Key differences:
1. Import statement: enhanced_client instead of async_client
2. All log_prediction() calls automatically buffered to disk
3. Automatic recovery when connectivity restored
4. Can start with existing batched predictions (persistence)
5. Same API: log_prediction(), shutdown(), get_buffer_status()

Migration steps:
1. Create persistent storage volume
2. Update Docker image to mount volume at /data
3. Update environment variables (set BUFFER_DB_PATH)
4. Update Python code: import EnhancedAsyncLoggingClient
5. Deploy and test with network failure simulation
6. Monitor buffer status in production
7. Adjust max_buffer_size_mb based on usage

Rollback:
- Simply revert to AsyncLoggingClient
- Buffered predictions will remain in database (not synced)
- Or manually recover from database before rollback
"""

print(__doc__)
