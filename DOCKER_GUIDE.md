# Docker Production Setup Guide

## Services

### 1. **MLflow Server** (`Dockerfile.mlflow`)
- Tracking and model registry
- SQLite backend + local artifact storage
- Port: 5000
- Volumes: `/data/mlruns`, `/data/db`

### 2. **Camera Stream** (`Dockerfile.camera`)
- Video capture and streaming
- CPU-based (no GPU needed)
- Depends on MLflow

### 3. **Preprocessing** (`Dockerfile.preprocessing`)
- Image normalization, resizing, transforms
- CPU-based
- Depends on MLflow

### 4. **YOLO Inference** (`Dockerfile.yolo`)
- Object detection
- **GPU-required** (PyTorch CUDA)
- Port: 8000 (inference API)
- Volumes: model cache

### 5. **Logging Service** (`Dockerfile.logging`)
- Image storage, metadata logging
- SQLAlchemy + SQLite (can upgrade to PostgreSQL)
- Port: 8001
- Volumes: prediction images, database

## Quick Start

### Prerequisites
- Docker 20.10+
- Docker Compose 1.29+
- NVIDIA Docker runtime (for GPU services): `nvidia-docker`

### Build all services
```bash
docker-compose build
```

### Start all services
```bash
docker-compose up -d
```

### Check service health
```bash
docker-compose ps
```

### View logs
```bash
docker-compose logs -f mlflow
docker-compose logs -f yolo
docker-compose logs -f logging
```

### Stop all services
```bash
docker-compose down
```

## Environment Variables

### Camera Service
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR (default: INFO)
- `CAMERA_ID`: Camera device index (default: 0)

### YOLO Service
- `LOG_LEVEL`: Logging level
- `CUDA_VISIBLE_DEVICES`: GPU IDs (e.g., "0" or "0,1")
- `MODEL_PATH`: Path to YOLO weights (default: yolov8n.pt)

### Logging Service
- `DATABASE_URL`: SQLite or PostgreSQL URL
- `LOG_LEVEL`: Logging level
- `MODEL_VERSION`: Current model version tag
- `MODEL_NAME`: Human-readable model name

### MLflow Server
- `MLFLOW_BACKEND_STORE_URI`: Backend database URI
- `MLFLOW_DEFAULT_ARTIFACT_ROOT`: Artifact storage path

## GPU Setup

### Linux with nvidia-docker
1. Install NVIDIA Docker runtime:
   ```bash
   distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
     sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   sudo apt-get update && sudo apt-get install -y nvidia-docker2
   sudo systemctl restart docker
   ```

2. Update runtime in docker-compose.yml:
   ```yaml
   yolo:
     runtime: nvidia
   ```

3. Verify GPU:
   ```bash
   docker run --rm --runtime=nvidia nvidia/cuda:12.1-runtime-ubuntu22.04 nvidia-smi
   ```

## Production Deployment

### Scale YOLO workers
```yaml
yolo:
  deploy:
    replicas: 2  # Multiple inference workers
```

### Use PostgreSQL for logging
```yaml
logging:
  environment:
    DATABASE_URL: "postgresql://user:pass@postgres:5432/vision_logs"
  depends_on:
    - postgres

postgres:
  image: postgres:15-alpine
  environment:
    POSTGRES_PASSWORD: secret
    POSTGRES_DB: vision_logs
  volumes:
    - postgres-data:/var/lib/postgresql/data
```

### Health checks
All services include healthchecks. Orchestrators (Kubernetes, Swarm) will restart failed containers automatically.

### Resource limits
Add to services in docker-compose.yml:
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
    reservations:
      cpus: '1'
      memory: 2G
```

## Monitoring & Logging

### MLflow UI
Open http://localhost:5000 to view experiments and models.

### Logs
```bash
docker-compose logs -f --tail=100 yolo
```

### Container stats
```bash
docker stats
```

## Troubleshooting

### YOLO container fails to start
- Check CUDA availability: `nvidia-smi` inside container
- Verify model download: `docker exec yolo ls -la /app/models`
- Check GPU allocation: `docker inspect yolo | grep -i gpu`

### MLflow artifacts not persisting
- Ensure `mlflow-data` volume is mounted: `docker volume ls`
- Check permissions: `docker exec mlflow ls -la /data`

### Logging database locked
- Stop other containers: `docker-compose down`
- Remove stale database: `docker volume rm logging-data`
- Restart: `docker-compose up`

### High GPU memory usage
- Reduce batch size in YOLO config
- Use smaller model (`yolov8n` vs `yolov8x`)
- Enable model quantization

## Network

All services communicate via the `vision-network` bridge:
- MLflow: `mlflow:5000`
- YOLO: `yolo:8000`
- Logging: `logging:8001`
- Camera: `camera:*` (internal)
- Preprocessing: `preprocessing:*` (internal)

## Cleanup

### Remove all containers and volumes
```bash
docker-compose down -v
```

### Prune unused images
```bash
docker image prune -a
```

## Security

- All services run as non-root users (UID 1000)
- No privileged containers
- Volumes are named (not host paths)
- Network is isolated (no external exposure except MLflow:5000)

For production, consider:
- Reverse proxy (nginx) in front of MLflow
- Authentication/authorization
- TLS/SSL for inter-service communication
- Secrets management (HashiCorp Vault, AWS Secrets)
