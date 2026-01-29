# Docker Deployment Guide for Real-Time Vision System

## Overview

This guide explains how to build, run, and deploy the real-time computer vision application using Docker with GPU support.

## Prerequisites

- **Docker** 20.10+
- **NVIDIA Docker** (for GPU support)
  ```bash
  # Install NVIDIA Docker on Linux
  distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
  curl -s -L https://nvidia.github.io/nvidia-docker/gpg-key.pub | sudo apt-key add -
  curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
    sudo tee /etc/apt/sources.list.d/nvidia-docker.list
  sudo apt-get update && sudo apt-get install -y nvidia-docker2
  sudo systemctl restart docker
  ```

- **GPU with CUDA 12.1 support**
- **At least 8GB VRAM** for YOLOv8 inference

## Quick Start

### Option 1: Using Docker Compose (Recommended)

```bash
# Build the image
docker-compose build

# Run the container with GPU support
docker-compose up -d vision-app

# View logs
docker-compose logs -f vision-app

# Stop the container
docker-compose down
```

### Option 2: Using Docker CLI

```bash
# Build the image
docker build -t realtime-vision:latest .

# Run with GPU
docker run --gpus all -it --rm \
  -v $(pwd)/data:/app/data:ro \
  -v $(pwd)/output:/app/output:rw \
  -v $(pwd)/logs:/app/logs:rw \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  --device /dev/video0:/dev/video0 \
  realtime-vision:latest

# Run with specific model and confidence
docker run --gpus all -it --rm \
  -v $(pwd)/data:/app/data:ro \
  -v $(pwd)/output:/app/output:rw \
  realtime-vision:latest \
  python run_realtime_detection.py --model yolov8m.pt --conf 0.4
```

## Building the Docker Image

### Standard Production Build

```bash
docker build -t realtime-vision:latest .
```

This creates a multi-stage build that:
- Downloads CUDA 12.1 runtime (base layer)
- Installs all system dependencies
- Installs Python packages from requirements.txt
- Creates a lean production image (~3-4GB)

### Development Build

```bash
docker build -f Dockerfile.dev -t realtime-vision:dev .
```

This includes:
- Development tools (pytest, black, flake8, mypy)
- Jupyter Lab
- TensorBoard
- Debugging utilities
- Full source code access

### Build with Custom Arguments

```bash
docker build --build-arg PYTHON_VERSION=3.10 \
  -t realtime-vision:custom .
```

## Running the Container

### Display Real-time Video (X11 Forwarding on Linux)

```bash
docker run --gpus all -it --rm \
  --env DISPLAY=$DISPLAY \
  --volume /tmp/.X11-unix:/tmp/.X11-unix:rw \
  --device /dev/video0:/dev/video0 \
  -v $(pwd)/output:/app/output:rw \
  realtime-vision:latest
```

### Run Headless (No Display)

```bash
docker run --gpus all -it --rm \
  -v /dev/video0:/dev/video0 \
  -v $(pwd)/output:/app/output:rw \
  realtime-vision:latest
```

Save output to file:
```bash
docker run --gpus all -it --rm \
  -v /dev/video0:/dev/video0 \
  -v $(pwd)/output:/app/output:rw \
  realtime-vision:latest \
  python run_realtime_detection.py > output/detection_results.log 2>&1
```

### Run with Custom Configuration

```bash
docker run --gpus all -it --rm \
  -v $(pwd)/data:/app/data:ro \
  -v $(pwd)/output:/app/output:rw \
  -v $(pwd)/logs:/app/logs:rw \
  -e YOLO_MODEL=yolov8m.pt \
  -e CONFIDENCE_THRESHOLD=0.5 \
  -e DEVICE=gpu \
  realtime-vision:latest \
  python run_realtime_detection.py \
    --model $YOLO_MODEL \
    --conf $CONFIDENCE_THRESHOLD \
    --device $DEVICE
```

## Volume Mounting

The container uses the following volume structure:

```
/app/
  ├── data/          → Input images/videos (read-only)
  ├── output/        → Detection results and saved frames
  ├── logs/          → Application logs
  ├── models/        → Pre-downloaded models (optional)
  └── [source code]
```

Mount volumes in docker-compose.yml:

```yaml
volumes:
  - ./data:/app/data:ro              # Input (read-only)
  - ./output:/app/output:rw          # Output (read-write)
  - ./logs:/app/logs:rw              # Logs (read-write)
  - ./models:/app/models:ro          # Models (read-only)
```

## GPU Configuration

### Using Specific GPU

```bash
# Use GPU 0 only
docker run --gpus '"device=0"' -it realtime-vision:latest

# Use multiple GPUs
docker run --gpus all -it realtime-vision:latest
```

In docker-compose.yml:

```yaml
environment:
  - CUDA_VISIBLE_DEVICES=0    # Single GPU
  - CUDA_VISIBLE_DEVICES=0,1  # Multiple GPUs
```

### Check GPU Inside Container

```bash
docker run --gpus all realtime-vision:latest nvidia-smi
```

### Specify GPU Memory Allocation

```bash
docker run --gpus all --memory 8g -it realtime-vision:latest
```

## Keyboard Controls (Interactive Mode)

When running with `-it` (interactive terminal):

```
q → Quit application
p → Pause/Resume
f → Toggle FPS display
g → Toggle FPS graph
d → Toggle detailed stats
s → Save current frame
```

## Docker Compose Operations

### Start Service

```bash
docker-compose up -d vision-app
```

### Stop Service

```bash
docker-compose down vision-app
```

### View Logs

```bash
# Real-time logs
docker-compose logs -f vision-app

# Last 100 lines
docker-compose logs --tail 100 vision-app

# Logs with timestamps
docker-compose logs -f --timestamps vision-app
```

### Execute Command in Running Container

```bash
docker-compose exec vision-app python run_realtime_detection.py --help
```

### Rebuild Service

```bash
docker-compose up -d --build vision-app
```

## Development Workflow

### Run Development Container

```bash
docker-compose up -d vision-app-dev
```

### Access Development Tools

```bash
# Interactive bash
docker-compose exec vision-app-dev bash

# Run tests
docker-compose exec vision-app-dev pytest tests/

# Run code formatting
docker-compose exec vision-app-dev black src/

# Start Jupyter Lab
docker-compose exec vision-app-dev jupyter lab --ip=0.0.0.0
# Access at http://localhost:8888

# Start TensorBoard (if using PyTorch logging)
docker-compose exec vision-app-dev tensorboard --logdir=logs/ --host=0.0.0.0
# Access at http://localhost:6006
```

## Image Inspection

### View Image Information

```bash
docker image inspect realtime-vision:latest
docker image history realtime-vision:latest
```

### Check Image Size

```bash
docker images realtime-vision:latest
# Typical sizes:
# - Production: ~3-4GB
# - Development: ~6-7GB
```

## Troubleshooting

### GPU Not Available

```bash
# Check if Docker recognizes GPU
docker run --gpus all nvidia/cuda:12.1.0-runtime-ubuntu22.04 nvidia-smi

# Common issue: NVIDIA Docker not installed
# Solution: Install nvidia-docker following prerequisites above
```

### Permission Denied on Output Files

```bash
# Fix permissions in docker-compose.yml
# Ensure volume is mounted with proper permissions:
volumes:
  - ./output:/app/output:rw

# Or manually fix on host
sudo chown -R $USER:$USER ./output
```

### Out of Memory (OOM)

```bash
# Reduce model size
docker run --gpus all realtime-vision:latest \
  python run_realtime_detection.py --model yolov8n.pt

# Or limit memory usage
docker run --gpus all -m 6g realtime-vision:latest
```

### Display Not Working (X11)

```bash
# Check X11 permissions
xhost +local:

# Verify DISPLAY is set
echo $DISPLAY

# Run with DISPLAY explicitly set
docker run --gpus all \
  -e DISPLAY=:0 \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  realtime-vision:latest
```

### Webcam Not Found

```bash
# List available video devices on host
ls -l /dev/video*

# Mount correct device
docker run --gpus all \
  --device /dev/video0:/dev/video0 \
  realtime-vision:latest
```

## Performance Optimization

### Use Lightweight Models

```bash
# Nano model (fastest)
docker run --gpus all realtime-vision:latest \
  python run_realtime_detection.py --model yolov8n.pt

# Small model (balanced)
docker run --gpus all realtime-vision:latest \
  python run_realtime_detection.py --model yolov8s.pt
```

### Enable GPU Memory Optimization

```bash
docker run --gpus all \
  -e CUDA_LAUNCH_BLOCKING=1 \
  realtime-vision:latest
```

### Resource Limits (docker-compose)

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 8G
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

## Production Deployment

### Push to Registry

```bash
# Tag image
docker tag realtime-vision:latest myregistry/realtime-vision:1.0

# Push to registry (Docker Hub, ECR, GCR, etc.)
docker push myregistry/realtime-vision:1.0
```

### Health Checks

The Dockerfile includes a health check:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "import cv2, torch, yaml; print('Health check passed')" || exit 1
```

Monitor health:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### Auto-restart Policy

```yaml
# In docker-compose.yml
restart: unless-stopped
```

Or with Docker CLI:

```bash
docker run --restart unless-stopped realtime-vision:latest
```

## Cleanup

### Remove Stopped Containers

```bash
docker container prune
```

### Remove Unused Images

```bash
docker image prune
```

### Full Cleanup (Warning: Removes all unused resources)

```bash
docker system prune -a
```

## Additional Resources

- [NVIDIA Docker Documentation](https://github.com/NVIDIA/nvidia-docker)
- [Docker Official Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [CUDA Toolkit Documentation](https://docs.nvidia.com/cuda/)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Docker logs: `docker logs <container_id>`
3. Check application logs: `docker exec <container_id> tail -f /app/logs/app.log`
4. Verify GPU setup: `docker run --gpus all nvidia/cuda:12.1.0-runtime-ubuntu22.04 nvidia-smi`
