# Architecture Overview

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                   CLI Entry Point                               │
│              run_realtime_detection.py                          │
│         • Argument parsing                                      │
│         • Configuration banner                                  │
│         • Pipeline instantiation                                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Pipeline Orchestration                         │
│            src/utils/realtime_pipeline.py                       │
│              DetectionPipeline class                            │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Manages component lifecycle and coordination             │  │
│  │ • setup() - Initialize all components                   │  │
│  │ • process_frame() - Run detection                       │  │
│  │ • draw_frame() - Visualize results                      │  │
│  │ • add_overlays() - Add FPS and info                     │  │
│  │ • run() - Main loop                                     │  │
│  │ • cleanup() - Release resources                         │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────┬─────────────────┬──────────────────────┬───────────────┘
         │                 │                      │
         ▼                 ▼                      ▼
    ┌─────────┐      ┌──────────────┐      ┌──────────────┐
    │ FPSMon. │      │ FPSRenderer  │      │ Components   │
    │ (Track) │      │ (Visualize)  │      │              │
    └─────────┘      └──────────────┘      └──────────────┘
                                            │    │    │    │
                         ┌──────────────────┼────┼────┼────┘
                         │                  │    │    │
                         ▼                  ▼    ▼    ▼
                    ┌────────────┐      ┌──────────────────────┐
                    │ Visualizer │      │ Detection Components │
                    │            │      │                      │
                    │ • Boxes    │      │ • Camera             │
                    │ • Info     │      │ • Preprocessor       │
                    │ • Colors   │      │ • YOLODetector       │
                    └────────────┘      │ • Class colors       │
                                        └──────────────────────┘
```

## Data Flow Diagram

```
┌────────────────┐
│  Input Frame   │
└────────┬───────┘
         │
         ▼
┌────────────────────────┐
│ ImageProcessor         │ src/preprocessing/
│ • Resize               │
│ • Normalize            │
│ • Convert BGR→RGB      │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│ YOLODetector           │ src/yolo_inference/
│ • Load model           │
│ • GPU/CPU inference    │
│ • Return boxes         │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│ draw_bounding_boxes()  │ src/utils/visualization.py
│ • Draw boxes           │
│ • Add labels           │
│ • Add confidence       │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│ FPSRenderer            │ src/utils/fps_renderer.py
│ • Main FPS counter     │
│ • History graph        │
│ • Detailed stats       │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│ Output Frame (Display) │
└────────────────────────┘
```

## Component Interaction Diagram

```
DetectionPipeline
├── Uses: FPSMonitor
│   └─ Tracks: frame_time, inference_time
│   └─ Provides: fps, avg_fps, min_fps, max_fps
│
├── Uses: FPSRenderer
│   ├─ Input: fps value, stats dict, frame_times list
│   └─ Output: annotated frame
│
├── Uses: Camera (src/video_streaming/)
│   ├─ Input: None (gets from source)
│   └─ Output: Stream of video frames
│
├── Uses: ImageProcessor (src/preprocessing/)
│   ├─ Input: Raw frame
│   └─ Output: Preprocessed frame
│
├── Uses: YOLODetector (src/yolo_inference/)
│   ├─ Input: Preprocessed frame
│   └─ Output: Detection results (boxes, classes, scores)
│
└── Uses: Visualization (src/utils/visualization.py)
    ├─ Input: Frame, boxes, labels, confidences
    └─ Output: Annotated frame with boxes and labels
```

## Class Hierarchy

```
┌─────────────────────────────────────┐
│         DetectionPipeline           │
├─────────────────────────────────────┤
│ - camera: Camera                    │
│ - preprocessor: ImageProcessor      │
│ - detector: YOLODetector            │
│ - fps_monitor: FPSMonitor           │
│ - fps_renderer: FPSRenderer         │
│ - paused: bool                      │
│ - frame_count: int                  │
├─────────────────────────────────────┤
│ + setup()                           │
│ + process_frame(frame)              │
│ + draw_frame(frame, results)        │
│ + add_overlays(frame, results)      │
│ + handle_keyboard_input(key)        │
│ + run()                             │
│ + cleanup()                         │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│        FPSMonitor                   │
├─────────────────────────────────────┤
│ - window_size: int                  │
│ - frame_times: deque                │
│ - inference_times: deque            │
│ - total_frames: int                 │
│ - start_time: float                 │
├─────────────────────────────────────┤
│ + update(frame_time, inf_time)      │
│ + get_summary() -> dict             │
│ + fps (property)                    │
│ + overall_fps (property)            │
│ + min_fps (property)                │
│ + max_fps (property)                │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│        FPSRenderer                  │
├─────────────────────────────────────┤
│ - show_main: bool                   │
│ - show_detailed: bool               │
│ - show_graph: bool                  │
├─────────────────────────────────────┤
│ + render_main_fps(frame, fps)       │
│ + render_detailed_stats(frame, stats)│
│ + render_fps_graph(frame, times)    │
│ + render_all(frame, fps, stats, times)│
└─────────────────────────────────────┘
```

## Module Dependencies

```
run_realtime_detection.py
    │
    └─► src.utils.DetectionPipeline
        │
        ├─► src.utils.FPSMonitor
        │
        ├─► src.utils.FPSRenderer
        │
        ├─► src.video_streaming.Camera
        │
        ├─► src.preprocessing.ImageProcessor
        │
        ├─► src.yolo_inference.YOLODetector
        │
        └─► src.utils.visualization
            ├─► draw_bounding_boxes()
            ├─► draw_detection_info()
            └─► create_color_palette()
```

## Execution Flow

```
1. START
   │
   ▼
2. Parse CLI arguments (run_realtime_detection.py)
   │
   ▼
3. Create DetectionPipeline instance
   │
   ▼
4. pipeline.setup()
   ├─ Initialize Camera
   ├─ Initialize ImageProcessor
   ├─ Initialize YOLODetector
   ├─ Warmup model
   └─ Generate class colors
   │
   ▼
5. pipeline.run()
   └─ LOOP (for each frame):
      ├─ Read frame from camera
      ├─ Process frame through pipeline
      │  ├─ Preprocess (resize, normalize)
      │  └─ Detect objects (YOLO)
      ├─ Update FPS monitor
      ├─ Draw detections
      ├─ Render FPS overlays
      ├─ Render info panel
      ├─ Display frame
      └─ Handle keyboard input
      │
      └─► UNTIL 'q' pressed
      │
   ▼
6. pipeline.cleanup()
   ├─ Release camera
   ├─ Close window
   └─ Print statistics
   │
   ▼
7. Print summary banner
   │
   ▼
8. END
```

## File Organization

```
realtime-vision-system/
│
├── run_realtime_detection.py      ◄─ Clean CLI entry point (134 lines)
│
├── src/
│   ├── video_streaming/
│   │   ├── camera.py              ◄─ Camera/video input
│   │   └── __init__.py
│   │
│   ├── preprocessing/
│   │   ├── image_processor.py      ◄─ Resize, normalize, convert
│   │   ├── transforms.py
│   │   └── __init__.py
│   │
│   ├── yolo_inference/
│   │   ├── detector.py            ◄─ YOLO detection
│   │   ├── model_loader.py
│   │   ├── utils.py
│   │   └── __init__.py
│   │
│   └── utils/
│       ├── fps_monitor.py         ◄─ FPS tracking (NEW)
│       ├── fps_renderer.py        ◄─ FPS visualization (NEW)
│       ├── realtime_pipeline.py   ◄─ Pipeline orchestration (NEW)
│       ├── visualization.py       ◄─ Drawing utilities
│       ├── logger.py
│       ├── config_loader.py
│       └── __init__.py
│
├── demo_*.py                       ◄─ Example scripts
├── FPS_MONITORING_GUIDE.md
├── REFACTORING_SUMMARY.md
├── MODULES_QUICK_REFERENCE.md
└── README.md
```

## Key Design Principles

### 1. Single Responsibility Principle
- `FPSMonitor`: Only tracks performance metrics
- `FPSRenderer`: Only renders FPS visualizations
- `DetectionPipeline`: Orchestrates components
- Each module has one reason to change

### 2. Separation of Concerns
- Data collection (FPSMonitor)
- Data visualization (FPSRenderer)
- Component orchestration (DetectionPipeline)
- CLI interface (run_realtime_detection.py)

### 3. Dependency Injection
- Pipeline passes stats to renderer
- Pipeline manages component initialization
- No global state or tight coupling

### 4. Composition Over Inheritance
- Pipeline uses FPSMonitor, doesn't inherit
- Pipeline uses FPSRenderer, doesn't inherit
- Easy to swap or extend components

### 5. Clean Interface
- Simple public APIs
- Clear method signatures
- Comprehensive docstrings
- Type hints throughout

## Scalability

The modular design allows:
- ✅ Running multiple pipelines concurrently
- ✅ Custom pipeline variants via inheritance
- ✅ Integration into larger systems
- ✅ Component replacement (e.g., different detector)
- ✅ Performance profiling per component
- ✅ Unit testing of individual modules
- ✅ Streaming to multiple outputs
