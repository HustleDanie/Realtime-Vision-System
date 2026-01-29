# Real-Time Computer Vision System

A production-ready real-time computer vision system with YOLO object detection, video streaming, and preprocessing capabilities.

## Features

- 🎥 Multi-source video streaming (webcam, RTSP, video files)
- 🔍 YOLO-based object detection and tracking
- ⚡ Real-time preprocessing and augmentation
- 🐳 Docker support for containerized deployment
- 📊 Comprehensive logging and monitoring
- 🧪 Full test coverage

## Project Structure

```
realtime-vision-system/
├── src/
│   ├── video_streaming/    # Video capture and streaming
│   ├── preprocessing/       # Image preprocessing and augmentation
│   ├── inference/          # YOLO detection and tracking
│   ├── utils/              # Utility functions
│   └── config/             # Configuration management
├── tests/                  # Unit and integration tests
├── config/                 # Configuration files
├── models/                 # Model weights directory
├── scripts/                # Utility scripts
├── docs/                   # Documentation
└── data/                   # Sample data and outputs
```

## Installation

### Prerequisites

- Python 3.9+
- CUDA (optional, for GPU acceleration)

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd realtime-vision-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Docker Installation

```bash
docker build -t realtime-vision-system .
docker run -it --gpus all realtime-vision-system
```

## Usage

### Basic Example

```python
from src.video_streaming.camera import CameraStream
from src.inference.yolo_detector import YOLODetector
from src.preprocessing.transforms import PreprocessPipeline

# Initialize components
camera = CameraStream(source=0)
detector = YOLODetector(model_path="models/yolov8n.pt")
preprocessor = PreprocessPipeline()

# Process stream
for frame in camera.stream():
    processed = preprocessor.transform(frame)
    detections = detector.detect(processed)
    # Handle detections...
```

## Configuration

Edit `config/config.yaml` to customize:
- Model parameters
- Video sources
- Preprocessing settings
- Logging configuration

## Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

## Performance

- Real-time processing at 30+ FPS (GPU)
- Support for multiple concurrent streams
- Optimized preprocessing pipeline

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct and development process.

## License

This project is licensed under the MIT License - see LICENSE file for details.

## Acknowledgments

- YOLOv8 by Ultralytics
- OpenCV community
