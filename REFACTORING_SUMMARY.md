# Real-Time Vision System - Refactored Architecture

## Overview

The real-time detection pipeline has been refactored into clean, modular components for better maintainability and code reuse.

## Module Structure

```
src/
├── video_streaming/
│   ├── camera.py           # Camera/Video input handling
│   └── __init__.py
│
├── preprocessing/
│   ├── image_processor.py  # Image resizing, normalization, color conversion
│   ├── transforms.py       # Modular transformation classes
│   └── __init__.py
│
├── yolo_inference/
│   ├── detector.py         # YOLO detection with GPU/CPU support
│   ├── model_loader.py     # Model management and loading
│   ├── utils.py            # Detection utility functions
│   └── __init__.py
│
└── utils/
    ├── visualization.py    # Drawing boxes, labels, info overlays
    ├── fps_monitor.py      # FPS calculation and tracking (NEW)
    ├── fps_renderer.py     # FPS visualization rendering (NEW)
    ├── realtime_pipeline.py # Main pipeline orchestration (NEW)
    ├── logger.py
    ├── config_loader.py
    └── __init__.py
```

## Key Refactoring Changes

### 1. New Module: `FPSMonitor` (`src/utils/fps_monitor.py`)

Dedicated performance monitoring class extracted from main pipeline.

**Features:**
- Tracks FPS with rolling average
- Calculates min/max/overall FPS
- Measures inference vs. total frame time
- Provides detailed statistics summary

**Usage:**
```python
from src.utils import FPSMonitor

monitor = FPSMonitor(window_size=30)
monitor.update(frame_time=0.033, inference_time=0.025)
stats = monitor.get_summary()
print(f"FPS: {stats['fps']:.1f}")
```

### 2. New Module: `FPSRenderer` (`src/utils/fps_renderer.py`)

Handles all FPS visualization on video frames.

**Features:**
- Renders main FPS counter
- Draws FPS history graph with color coding
- Shows detailed statistics overlay
- Separate from monitoring logic

**Usage:**
```python
from src.utils import FPSRenderer

renderer = FPSRenderer()
renderer.show_graph = True
renderer.show_detailed = True

frame = renderer.render_all(
    frame,
    fps=stats['fps'],
    stats=stats,
    frame_times=list(monitor.frame_times)
)
```

### 3. Refactored Module: `DetectionPipeline` (`src/utils/realtime_pipeline.py`)

Main orchestration class that coordinates all components.

**Key Responsibilities:**
- Component initialization (camera, preprocessor, detector)
- Frame processing pipeline
- Detection visualization
- Input handling (keyboard controls)
- State management (pause, display toggles)

**Clean Separation:**
- Delegates FPS monitoring to `FPSMonitor`
- Delegates FPS rendering to `FPSRenderer`
- Uses existing modules for detection, visualization
- Focuses on orchestration and control flow

**Usage:**
```python
from src.utils import DetectionPipeline

pipeline = DetectionPipeline(
    model_path="yolov8n.pt",
    confidence_threshold=0.5,
    device="auto"
)
pipeline.run()
```

### 4. Refactored Script: `run_realtime_detection.py`

Now a clean entry point with minimal logic.

**Responsibilities:**
- Command-line argument parsing
- Configuration banner printing
- Pipeline instantiation and execution
- Error handling

**Code Structure:**
```python
def setup_logging():
    """Configure logging."""

def create_parser():
    """Create argument parser."""

def print_banner(args):
    """Print startup banner."""

def main():
    """Main entry point."""

if __name__ == "__main__":
    sys.exit(main())
```

## Modular Design Benefits

### ✅ Separation of Concerns
- **FPSMonitor**: Pure data tracking
- **FPSRenderer**: Pure visualization
- **DetectionPipeline**: Orchestration and control
- **run_realtime_detection.py**: CLI entry point

### ✅ Reusability
Each module can be used independently:

```python
# Use FPS monitoring in custom code
from src.utils import FPSMonitor
monitor = FPSMonitor()
# ... your custom code ...

# Use FPS rendering with custom pipeline
from src.utils import FPSRenderer
renderer = FPSRenderer()
# ... render FPS on frames ...

# Use DetectionPipeline as library
from src.utils import DetectionPipeline
pipeline = DetectionPipeline(...)
pipeline.run()
```

### ✅ Testability
Each module has clear interfaces:

```python
# Test FPS calculations
def test_fps_monitor():
    monitor = FPSMonitor()
    monitor.update(0.033, 0.025)
    assert monitor.fps > 25

# Test rendering
def test_fps_renderer():
    renderer = FPSRenderer()
    frame = np.zeros((480, 640, 3))
    result = renderer.render_main_fps(frame, 30.0)
    assert result.shape == frame.shape

# Test pipeline setup
def test_detection_pipeline():
    pipeline = DetectionPipeline(device="cpu")
    assert pipeline.setup()
```

### ✅ Maintainability
Easy to modify specific functionality:

```python
# Change FPS calculation logic → modify FPSMonitor
# Change visualization style → modify FPSRenderer
# Add new features → extend DetectionPipeline
# Modify CLI → edit run_realtime_detection.py
```

## Module Dependencies

```
run_realtime_detection.py
    ↓
DetectionPipeline (src/utils/realtime_pipeline.py)
    ↓
    ├── FPSMonitor (src/utils/fps_monitor.py)
    ├── FPSRenderer (src/utils/fps_renderer.py)
    ├── Camera (src/video_streaming/)
    ├── ImageProcessor (src/preprocessing/)
    ├── YOLODetector (src/yolo_inference/)
    └── Visualization (src/utils/visualization.py)
```

## Backward Compatibility

The refactoring maintains full backward compatibility:
- All existing imports still work
- `__init__.py` exports all public classes
- Function signatures unchanged
- Behavior identical to previous implementation

## Usage Examples

### Basic Usage
```bash
python run_realtime_detection.py
```

### With Custom Model
```bash
python run_realtime_detection.py --model yolov8m.pt
```

### Using as Library
```python
from src.utils import DetectionPipeline, FPSMonitor

# Create pipeline
pipeline = DetectionPipeline(device="auto")

# Or use components independently
monitor = FPSMonitor()
# ... your code ...
```

## File Changes Summary

| File | Changes |
|------|---------|
| `run_realtime_detection.py` | Refactored to clean CLI entry point |
| `src/utils/fps_monitor.py` | **NEW** - FPS tracking |
| `src/utils/fps_renderer.py` | **NEW** - FPS visualization |
| `src/utils/realtime_pipeline.py` | **NEW** - Pipeline orchestration |
| `src/utils/__init__.py` | Updated exports |

## Performance Impact

✅ **No performance degradation**
- Same algorithms
- Additional method calls are negligible
- Better memory organization (fewer instance variables)
- Same optimization level

## Next Steps

The modular architecture enables:
1. Unit testing of individual components
2. Integration testing of pipeline
3. Custom pipeline variants
4. Performance profiling by component
5. Easy feature additions without affecting core logic
