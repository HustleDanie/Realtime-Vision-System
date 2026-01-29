# Refactored Modules - Quick Reference

## Module Imports

### Import Everything
```python
from src.utils import (
    FPSMonitor,
    FPSRenderer,
    DetectionPipeline,
    Visualizer,
    draw_bounding_boxes,
    draw_detection_info,
    create_color_palette,
    setup_logger,
    ConfigLoader
)
```

### Import Individually
```python
from src.utils.fps_monitor import FPSMonitor
from src.utils.fps_renderer import FPSRenderer
from src.utils.realtime_pipeline import DetectionPipeline
```

## FPSMonitor - Performance Tracking

### Basic Usage
```python
from src.utils import FPSMonitor

# Create monitor
monitor = FPSMonitor(window_size=30)

# Update with timing data
for frame_time, inference_time in frame_timings:
    monitor.update(frame_time, inference_time)

# Get metrics
stats = monitor.get_summary()
print(f"Current FPS: {stats['fps']:.1f}")
print(f"Average FPS: {stats['avg_fps']:.1f}")
print(f"Min/Max FPS: {stats['min_fps']:.1f} / {stats['max_fps']:.1f}")
print(f"Avg inference time: {stats['inference_time_ms']:.1f}ms")
```

### Properties
```python
monitor.fps                    # Current FPS (rolling average)
monitor.overall_fps            # Overall FPS since start
monitor.min_fps                # Minimum FPS in window
monitor.max_fps                # Maximum FPS in window
monitor.avg_inference_fps      # FPS if only doing inference
monitor.avg_frame_time         # Average frame time (ms)
monitor.avg_inference_time     # Average inference time (ms)
monitor.total_frames           # Total frames processed
monitor.total_time_elapsed     # Total elapsed time (seconds)
monitor.get_summary()          # Dictionary with all metrics
```

## FPSRenderer - FPS Visualization

### Basic Usage
```python
from src.utils import FPSRenderer

# Create renderer
renderer = FPSRenderer()

# Configure what to show
renderer.show_main = True           # Large FPS number
renderer.show_graph = True          # FPS history graph
renderer.show_detailed = True       # Min/max/avg stats

# Render FPS overlays
frame = renderer.render_main_fps(frame, fps=30.5)
frame = renderer.render_detailed_stats(frame, stats)
frame = renderer.render_fps_graph(frame, frame_times)

# Or render all at once
frame = renderer.render_all(frame, fps=30.5, stats=stats, frame_times=list(monitor.frame_times))
```

### Methods
```python
renderer.render_main_fps(frame, fps)              # Main FPS counter
renderer.render_detailed_stats(frame, stats)      # Min/max/avg display
renderer.render_fps_graph(frame, frame_times)     # History graph
renderer.render_all(frame, fps, stats, frame_times)  # All overlays
```

## DetectionPipeline - Main Orchestrator

### Basic Usage
```python
from src.utils import DetectionPipeline

# Create pipeline
pipeline = DetectionPipeline(
    model_path="yolov8n.pt",
    confidence_threshold=0.5,
    device="auto"
)

# Setup components
if pipeline.setup():
    # Run the pipeline
    pipeline.run()
```

### Command-Line Interface
```bash
# Basic usage
python run_realtime_detection.py

# With arguments
python run_realtime_detection.py --model yolov8m.pt --conf 0.4 --device gpu
```

### Keyboard Controls (During Execution)
```
q - Quit
p - Pause/Resume
f - Toggle FPS counter
g - Toggle FPS graph
d - Toggle detailed statistics
s - Save frame
```

### Pipeline Components
```python
pipeline.camera              # Video input
pipeline.preprocessor       # Image preprocessing
pipeline.detector           # YOLO model
pipeline.fps_monitor        # Performance tracking
pipeline.fps_renderer       # FPS visualization
pipeline.paused             # Pause state
pipeline.frame_count        # Frames processed
```

### Key Methods
```python
pipeline.setup()            # Initialize all components
pipeline.process_frame(frame)       # Run detection on frame
pipeline.draw_frame(frame, results) # Draw detections
pipeline.add_overlays(frame, results) # Add FPS, info panels
pipeline.run()              # Main execution loop
pipeline.cleanup()          # Clean up resources
```

## Integration Example

### Combine Multiple Modules
```python
from src.utils import (
    FPSMonitor,
    FPSRenderer,
    DetectionPipeline,
)
import cv2

# Create pipeline
pipeline = DetectionPipeline(device="auto")
pipeline.setup()

# Custom FPS monitoring and rendering
custom_monitor = FPSMonitor(window_size=60)
custom_renderer = FPSRenderer()
custom_renderer.show_graph = True
custom_renderer.show_detailed = True

# Process frames
for frame in pipeline.camera.stream():
    start = time.time()
    
    # Detect
    original, results, inf_time = pipeline.process_frame(frame)
    
    # Draw detections
    output = pipeline.draw_frame(original, results)
    
    # Track performance
    frame_time = time.time() - start
    custom_monitor.update(frame_time, inf_time)
    
    # Render custom FPS display
    stats = custom_monitor.get_summary()
    output = custom_renderer.render_all(
        output,
        fps=stats['fps'],
        stats=stats,
        frame_times=list(custom_monitor.frame_times)
    )
    
    # Display
    cv2.imshow('Detection', output)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

pipeline.cleanup()
```

### Custom Pipeline Variant
```python
from src.utils import DetectionPipeline

class CustomPipeline(DetectionPipeline):
    """Custom pipeline with additional features."""
    
    def process_frame(self, frame):
        """Override to add custom preprocessing."""
        # Custom preprocessing
        custom_frame = self.custom_preprocessing(frame)
        
        # Use parent's processing
        return super().process_frame(custom_frame)
    
    def custom_preprocessing(self, frame):
        """Add your custom logic."""
        # ... your code ...
        return frame

# Use custom pipeline
pipeline = CustomPipeline()
pipeline.run()
```

## Performance Monitoring

### Real-Time Monitoring
```python
pipeline = DetectionPipeline()
pipeline.setup()

# Create custom monitor
custom_monitor = FPSMonitor()

for frame in pipeline.camera.stream():
    start = time.time()
    original, results, inf_time = pipeline.process_frame(frame)
    
    # Update monitor
    frame_time = time.time() - start
    custom_monitor.update(frame_time, inf_time)
    
    # Print every 100 frames
    if custom_monitor.total_frames % 100 == 0:
        stats = custom_monitor.get_summary()
        print(f"FPS: {stats['fps']:.1f} | "
              f"Avg: {stats['avg_fps']:.1f} | "
              f"Inference: {stats['inference_time_ms']:.1f}ms")

pipeline.cleanup()
```

### Profiling by Component
```python
import time

# Time individual components
t0 = time.time()
original, processed = pipeline.preprocessor.process(frame)
preprocess_time = time.time() - t0

t0 = time.time()
results = pipeline.detector.detect(original)
inference_time = time.time() - t0

t0 = time.time()
output = pipeline.draw_frame(original, results)
visualization_time = time.time() - t0

print(f"Preprocessing: {preprocess_time*1000:.1f}ms")
print(f"Inference: {inference_time*1000:.1f}ms")
print(f"Visualization: {visualization_time*1000:.1f}ms")
```

## Troubleshooting

### Module Not Found
```python
# Make sure you're importing from src.utils
from src.utils import DetectionPipeline

# NOT from src.utils.realtime_pipeline
# (though this also works, the first way is preferred)
```

### Pipeline Setup Fails
```python
pipeline = DetectionPipeline()
if pipeline.setup():
    pipeline.run()
else:
    print("Setup failed - check logs for details")
    # Check:
    # 1. YOLO model path is correct
    # 2. Camera is connected
    # 3. GPU/CPU device is available
```

### Low FPS Performance
```python
# Use FPS monitoring to identify bottleneck
stats = pipeline.fps_monitor.get_summary()
print(f"FPS: {stats['fps']:.1f}")
print(f"Inference: {stats['inference_time_ms']:.1f}ms")
print(f"Total frame: {stats['frame_time_ms']:.1f}ms")

# If inference time is high: use smaller model or GPU
# If total time >> inference time: I/O bottleneck
```

## Summary

The refactored architecture provides:
- ✅ Clean module separation
- ✅ Easy component reuse
- ✅ Simple integration
- ✅ Performance monitoring
- ✅ Flexible customization
- ✅ Command-line interface
- ✅ Backward compatibility
