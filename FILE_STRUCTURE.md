# Complete File Structure and Purposes

## Root Level Files

### `run_realtime_detection.py` (134 lines) ⭐ REFACTORED
**Purpose:** Clean command-line entry point for the detection pipeline
**Responsibilities:**
- Parse command-line arguments
- Display configuration banner
- Create and run DetectionPipeline
- Error handling

**Key Functions:**
```python
def setup_logging()
def create_parser()
def print_banner(args)
def main()
```

**Usage:**
```bash
python run_realtime_detection.py [--model MODEL] [--conf CONF] [--device DEVICE]
```

### `demo_camera.py`
**Purpose:** Demonstrate camera streaming capabilities
**Examples:** 5 camera input demos

### `demo_preprocessing.py`
**Purpose:** Demonstrate image preprocessing
**Examples:** 7 preprocessing pipeline demos

### `demo_yolo.py`
**Purpose:** Demonstrate YOLO inference
**Examples:** 6 YOLO detection demos

### `demo_visualization.py`
**Purpose:** Demonstrate bounding box visualization
**Examples:** 7 visualization technique demos

### `demo_detection_pipeline.py`
**Purpose:** Demonstrate complete pipeline
**Examples:** 6 end-to-end detection demos

## Documentation Files

### `README.md`
Project overview and getting started guide

### `FPS_MONITORING_GUIDE.md`
Comprehensive FPS monitoring documentation
- FPS Monitor class usage
- Performance interpretation
- Optimization tips
- Troubleshooting guide

### `REFACTORING_SUMMARY.md` ⭐ NEW
Explains the modular refactoring
- New module structure
- Module responsibilities
- Design benefits
- File changes summary

### `MODULES_QUICK_REFERENCE.md` ⭐ NEW
Quick reference for using refactored modules
- Import statements
- Method signatures
- Usage examples
- Integration patterns

### `ARCHITECTURE.md` ⭐ NEW
System architecture documentation
- Component diagrams
- Data flow
- Class hierarchy
- Module dependencies
- Execution flow
- Design principles

## Source Code Structure

### `src/video_streaming/`

#### `camera.py`
**Class:** `Camera`
**Purpose:** Handle video input from webcam/file
**Key Methods:**
- `__init__(source, fps)`
- `stream()` - Generator yielding frames
- `read()` - Read single frame
- `release()` - Release camera
- `get_properties()` - Get camera info

#### `__init__.py`
Exports: `Camera`

### `src/preprocessing/`

#### `image_processor.py`
**Class:** `ImageProcessor`
**Purpose:** Preprocess images for inference
**Key Methods:**
- `resize()` - Resize with aspect ratio
- `normalize_pixels()` - Normalize pixel values
- `convert_color()` - BGR to RGB conversion
- `process()` - Main pipeline (returns original + processed)
- `batch_process()` - Process multiple frames
- `process_stream()` - Process stream generator

#### `transforms.py`
**Classes:** Modular transformation classes
- `Transform` - Base class
- `ResizeTransform`
- `NormalizeTransform`
- `BGRToRGBTransform`
- `ToFloatTransform`
- `GrayscaleTransform`
- `GaussianBlurTransform`
- `BrightnessContrastTransform`
- `HistogramEqualizationTransform`

#### `__init__.py`
Exports: `ImageProcessor` and transform classes

### `src/yolo_inference/`

#### `detector.py`
**Class:** `YOLODetector`
**Purpose:** YOLO object detection with GPU/CPU support
**Key Methods:**
- `load_model()` - Load YOLOv5 or YOLOv8
- `detect()` - Run inference on frame
- `warmup()` - Warm up model
- `get_device_info()` - Get GPU/CPU info

#### `model_loader.py`
**Class:** `ModelLoader`
**Purpose:** Manage model loading and caching
**Key Methods:**
- `load_model()` - Load model with caching
- `unload_model()` - Release model memory
- `list_models()` - List available models
- `change_device()` - Switch GPU/CPU

#### `utils.py`
**Functions:**
- `detect_objects()` - Main detection with multiple return formats
- `detect_and_filter()` - Detection with NMS
- `get_detections_by_class()` - Filter by class
- `batch_detect()` - Process batch of frames
- `stream_detect()` - Process frame stream
- `compute_iou()` - Calculate IoU
- `filter_overlapping_boxes()` - NMS
- `get_detection_summary()` - Statistics

#### `__init__.py`
Exports: `YOLODetector`, `ModelLoader`, utility functions

### `src/utils/`

#### `fps_monitor.py` ⭐ NEW
**Class:** `FPSMonitor`
**Purpose:** Track FPS and performance metrics
**Key Properties:**
- `fps` - Current FPS
- `overall_fps` - Overall FPS since start
- `min_fps`, `max_fps` - Min/max FPS
- `avg_frame_time`, `avg_inference_time` - Timing metrics
- `total_frames`, `total_time_elapsed` - Counters

**Key Methods:**
- `update()` - Update with frame timing
- `get_summary()` - Get all metrics as dict

#### `fps_renderer.py` ⭐ NEW
**Class:** `FPSRenderer`
**Purpose:** Render FPS information on frames
**Key Properties:**
- `show_main` - Show main FPS counter
- `show_graph` - Show FPS history graph
- `show_detailed` - Show detailed statistics

**Key Methods:**
- `render_main_fps()` - Render large FPS number
- `render_detailed_stats()` - Render min/max/avg
- `render_fps_graph()` - Render history graph
- `render_all()` - Render all overlays

#### `realtime_pipeline.py` ⭐ NEW
**Class:** `DetectionPipeline`
**Purpose:** Orchestrate complete detection pipeline
**Key Methods:**
- `setup()` - Initialize all components
- `process_frame()` - Run detection on frame
- `draw_frame()` - Draw detections
- `add_overlays()` - Add FPS and info panels
- `handle_keyboard_input()` - Process user input
- `run()` - Main execution loop
- `cleanup()` - Release resources

**Key Attributes:**
- `camera` - Video input
- `preprocessor` - Image processor
- `detector` - YOLO detector
- `fps_monitor` - Performance tracker
- `fps_renderer` - FPS visualizer

#### `visualization.py`
**Functions:**
- `draw_bounding_boxes()` - Draw boxes with labels
- `draw_detection_info()` - Draw text overlays
- `create_color_palette()` - Generate distinct colors

**Class:** `Visualizer`
**Methods:**
- `draw_bbox()` - Draw single box
- `draw_detections()` - Draw multiple boxes
- `draw_from_results()` - Draw from detection dict
- `create_grid()` - Create image grid

#### `logger.py`
**Function:** `setup_logger()`
Purpose: Configure application logging

#### `config_loader.py`
**Class:** `ConfigLoader`
**Purpose:** Load configuration from YAML
**Methods:**
- `load()` - Load config file
- `get()` - Get config value
- `set()` - Set config value

#### `__init__.py` ⭐ UPDATED
**Exports:**
- `FPSMonitor`
- `FPSRenderer`
- `DetectionPipeline`
- `Visualizer`
- `draw_bounding_boxes`
- `draw_detection_info`
- `create_color_palette`
- `setup_logger`
- `ConfigLoader`

## Configuration Files

### `setup.py`
Package installation configuration

### `requirements.txt`
Python dependencies:
- opencv-python
- torch
- ultralytics
- numpy
- pyyaml

## Output Directories

### `output/detections/`
Saved detection frames (auto-created)

### `logs/`
Application logs

### `models/`
Downloaded YOLO models

### `data/`
Input video/image data

## Summary Statistics

| Category | Count | Modules |
|----------|-------|---------|
| **Core Modules** | 3 | src/video_streaming, src/preprocessing, src/yolo_inference |
| **Utility Modules** | 2 | src/utils (9 files) |
| **Demo Scripts** | 5 | demo_*.py |
| **Documentation** | 4 | FPS_MONITORING_GUIDE.md, REFACTORING_SUMMARY.md, MODULES_QUICK_REFERENCE.md, ARCHITECTURE.md |
| **Total Python Files** | 30+ | All source code |
| **Lines of Code** | ~3,000+ | Including documentation strings |

## Module Statistics

### Refactored Modules (NEW)

| Module | File | Lines | Purpose |
|--------|------|-------|---------|
| FPSMonitor | fps_monitor.py | ~100 | Track FPS metrics |
| FPSRenderer | fps_renderer.py | ~150 | Render FPS visualization |
| DetectionPipeline | realtime_pipeline.py | ~250 | Orchestrate pipeline |

### Existing Modules

| Module | File | Lines | Purpose |
|--------|------|-------|---------|
| Camera | camera.py | ~200 | Video input |
| ImageProcessor | image_processor.py | ~200 | Image preprocessing |
| YOLODetector | detector.py | ~300 | YOLO inference |
| Visualization | visualization.py | ~300 | Draw results |

### CLI Entry Point

| File | Lines | Purpose |
|------|-------|---------|
| run_realtime_detection.py | 134 | Clean entry point |

## Key Features by Module

### Camera Module
✅ Webcam support
✅ Video file support
✅ FPS control
✅ Auto-reconnect
✅ Frame buffering
✅ Context manager support

### Preprocessing Module
✅ Resizing (with aspect ratio)
✅ Normalization (0-1, ImageNet, -1 to 1)
✅ Color conversion (BGR→RGB)
✅ Batch processing
✅ Stream processing
✅ Multiple transformation types

### YOLO Module
✅ YOLOv5 support
✅ YOLOv8 support
✅ GPU/CPU auto-selection
✅ FP16 support
✅ Model caching
✅ Multiple return formats

### FPS Module (NEW)
✅ Real-time FPS calculation
✅ Min/max/average tracking
✅ Inference-only FPS
✅ Performance graph visualization
✅ Detailed statistics overlay
✅ Color-coded performance indicators

### Visualization Module
✅ Bounding box drawing
✅ Label and confidence display
✅ Semi-transparent backgrounds
✅ Custom colors
✅ Color palette generation
✅ Info panel overlay
✅ Batch operations

## Refactoring Impact

### Before Refactoring
- Single 767-line script
- Mixed concerns (monitoring, rendering, orchestration)
- Difficult to test individual components
- Hard to reuse for custom pipelines

### After Refactoring
- Clean 134-line entry point
- Separated concerns (3 new modules)
- Each module is independently testable
- Easy component reuse and customization
- Better maintainability
- Clearer architecture

## Dependencies Graph

```
run_realtime_detection.py
    │
    └─ src.utils.DetectionPipeline
        ├─ src.utils.FPSMonitor
        ├─ src.utils.FPSRenderer
        ├─ src.video_streaming.Camera
        │   └─ cv2, threading, time
        ├─ src.preprocessing.ImageProcessor
        │   └─ cv2, numpy
        ├─ src.yolo_inference.YOLODetector
        │   ├─ torch
        │   ├─ ultralytics
        │   └─ cv2, numpy
        └─ src.utils.visualization
            ├─ cv2, numpy, random
            └─ src.utils.visualization functions
```

## Getting Started

### Run Main Pipeline
```bash
python run_realtime_detection.py
```

### Run with Arguments
```bash
python run_realtime_detection.py --model yolov8m.pt --conf 0.4 --device gpu
```

### Run Demo Scripts
```bash
python demo_camera.py
python demo_preprocessing.py
python demo_yolo.py
python demo_visualization.py
python demo_detection_pipeline.py
```

### Use as Library
```python
from src.utils import DetectionPipeline

pipeline = DetectionPipeline()
pipeline.run()
```

## File Size Reference

- `run_realtime_detection.py`: 4 KB (clean, minimal)
- `src/utils/realtime_pipeline.py`: 12 KB (pipeline logic)
- `src/utils/fps_monitor.py`: 3 KB (monitoring)
- `src/utils/fps_renderer.py`: 8 KB (rendering)
- Total source code: ~200 KB
- Total with docs: ~250 KB
