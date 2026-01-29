# Multi-stage Dockerfile for Real-Time Computer Vision App with GPU Support

# Stage 1: Builder
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04 as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for OpenCV and Python development
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-dev \
    python3.10-venv \
    python3-pip \
    build-essential \
    cmake \
    git \
    # OpenCV dependencies
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libhdf5-dev \
    libharfbuzz0b \
    libwebp7 \
    libjasper1 \
    libjpeg-turbo8 \
    libpng16-16 \
    libatlas-base-dev \
    libjasper-dev \
    libtiff5 \
    libwebp6 \
    # Additional utilities
    wget \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install build tools
RUN pip install --upgrade pip setuptools wheel

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# Set metadata
LABEL maintainer="Computer Vision Team"
LABEL description="Real-time computer vision application with PyTorch and OpenCV"
LABEL version="1.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app:$PYTHONPATH"

# Install runtime dependencies only (smaller image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    # OpenCV runtime dependencies
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libhdf5-103 \
    libharfbuzz0b \
    libwebp7 \
    libjasper1 \
    libjpeg-turbo8 \
    libpng16-16 \
    libatlas3-base \
    libtiff5 \
    libwebp6 \
    # Additional utilities
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create non-root user for security
RUN useradd -m -u 1000 visionuser

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=visionuser:visionuser . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /app/output /app/logs && \
    chown -R visionuser:visionuser /app

# Switch to non-root user
USER visionuser

# Health check (simple Python import check)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "import cv2, torch, yaml; print('Health check passed')" || exit 1

# Expose port for potential web interface (if implemented)
EXPOSE 8000 5000

# Default command - run the real-time detection
CMD ["python", "run_realtime_detection.py"]

# Alternative entry points can be used with:
# docker run <image> python run_realtime_detection.py --help
