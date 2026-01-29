# FPS Monitoring Guide

## Overview

The real-time detection pipeline includes comprehensive FPS monitoring and visualization tools for performance analysis.

## FPS Monitor Class

The `FPSMonitor` class tracks performance metrics across configurable time windows.

### Basic Usage

```python
from run_realtime_detection import FPSMonitor

monitor = FPSMonitor(window_size=30)

# Update with frame timing
frame_time = 0.033  # seconds
inference_time = 0.025  # seconds
monitor.update(frame_time, inference_time)

# Get metrics
print(f"Current FPS: {monitor.fps:.1f}")
print(f"Average FPS: {monitor.overall_fps:.1f}")
print(f"Min FPS: {monitor.min_fps:.1f}")
print(f"Max FPS: {monitor.max_fps:.1f}")
print(f"Inference FPS: {monitor.avg_inference_fps:.1f}")
```

### Key Metrics

| Metric | Description | Unit |
|--------|-------------|------|
| `fps` | Current FPS (rolling average) | frames/sec |
| `overall_fps` | Overall FPS since start | frames/sec |
| `min_fps` | Minimum FPS in window | frames/sec |
| `max_fps` | Maximum FPS in window | frames/sec |
| `avg_inference_fps` | FPS if only doing inference | frames/sec |
| `avg_frame_time` | Average time per frame | milliseconds |
| `avg_inference_time` | Average inference time | milliseconds |
| `total_frames` | Total frames processed | count |
| `total_time_elapsed` | Elapsed time | seconds |

### Get Full Summary

```python
stats = monitor.get_summary()
# Returns dict with all metrics
```

## Pipeline FPS Display

The main detection pipeline shows FPS information in multiple ways:

### 1. Main FPS Counter (Always Visible)

Large FPS number in top-left corner of video frame.

```
30.5 FPS
```

### 2. FPS Graph (Toggle with 'G')

Shows FPS history over last 30 frames in top-right corner:
- **Green line**: Good performance (>25 FPS)
- **Orange line**: Medium performance (15-25 FPS)
- **Red line**: Low performance (<15 FPS)

### 3. Detailed Statistics (Toggle with 'D')

Shows extended metrics below main FPS:
```
Avg: 29.5 | Min: 28.1 | Max: 30.2
Frame: 32.5ms | Inf: 26.3ms
```

### 4. Info Panel (Toggle with 'I')

Shows detection and system information:
```
Objects: 5
Model: yolov8n
Device: GPU
Status: RUNNING
```

## Keyboard Controls

| Key | Action | Description |
|-----|--------|-------------|
| `Q` | Quit | Stop detection and exit |
| `P` | Pause | Pause frame processing |
| `C` | Confidence | Toggle confidence score display |
| `F` | FPS | Toggle main FPS counter |
| `I` | Info | Toggle info panel |
| `G` | Graph | Toggle FPS history graph |
| `D` | Detail | Toggle detailed statistics |
| `S` | Save | Save current frame to output/ |

## Performance Interpretation

### FPS Guidelines

- **>30 FPS**: Excellent real-time performance
- **25-30 FPS**: Good real-time performance
- **15-25 FPS**: Acceptable for many applications
- **<15 FPS**: May feel sluggish in interactive scenarios

### Identifying Bottlenecks

Use the timing metrics to identify where time is spent:

```
Frame time: 40ms
Inference time: 35ms
I/O overhead: 5ms
```

- **High inference time**: Model is slow, try smaller model or GPU
- **High I/O overhead**: Camera read or preprocessing is slow
- **Uneven FPS**: Inconsistent performance, check system load

### Frame Time Breakdown

```
Total Frame Time = Preprocessing + Inference + Visualization + I/O
```

For example:
```
Total: 40ms
- Preprocess: 3ms (resize, normalize)
- Inference: 32ms (YOLO detection)
- Visualization: 2ms (draw boxes)
- I/O: 3ms (camera read, display)
```

## Command Line Usage

### Basic Detection

```bash
python run_realtime_detection.py
```

### With Different Model

```bash
python run_realtime_detection.py --model yolov8m.pt
```
- `yolov8n.pt`: Fast, lower accuracy
- `yolov8s.pt`: Balanced
- `yolov8m.pt`: Slower, higher accuracy
- `yolov8l.pt`: Slowest, best accuracy

### With Lower Confidence Threshold

```bash
python run_realtime_detection.py --conf 0.4
```

More detections, but lower quality.

### Force CPU

```bash
python run_realtime_detection.py --device cpu
```

### Use Video File

```bash
python run_realtime_detection.py --video path/to/video.mp4
```

## Performance Tips

### 1. GPU Acceleration

GPU is much faster for inference:

```bash
# Automatic GPU selection
python run_realtime_detection.py --device auto

# Force GPU if available
python run_realtime_detection.py --device gpu
```

**Expected speedup**: 5-10x faster than CPU

### 2. Model Selection

Smaller models are faster:

```bash
# Fast (nano model)
python run_realtime_detection.py --model yolov8n.pt  # ~30 FPS
python run_realtime_detection.py --model yolov8s.pt  # ~25 FPS
python run_realtime_detection.py --model yolov8m.pt  # ~15 FPS
python run_realtime_detection.py --model yolov8l.pt  # ~8 FPS
```

### 3. Input Size

Larger input sizes are slower. YOLOv8 uses 640x640 by default.

### 4. Disable Unnecessary Displays

Reduce GPU overhead:

```
Toggle displays with keyboard:
F - Disable FPS counter
G - Disable FPS graph
D - Disable detailed stats
I - Disable info panel
```

## Statistics Output

When quitting (press Q), detailed statistics are printed:

```
======================================================================
PERFORMANCE STATISTICS
======================================================================
Total frames processed: 1000
Total time elapsed: 33.5s

FPS Metrics:
  Current FPS: 29.5
  Average FPS: 29.8
  Min FPS: 28.1
  Max FPS: 30.2

Timing Metrics:
  Avg frame time: 33.5ms
  Avg inference time: 27.3ms
  Inference FPS: 36.6
======================================================================
```

## Troubleshooting

### FPS Below 30

**Check timing breakdown:**
1. Is inference time high? → Use smaller model or GPU
2. Is I/O time high? → Check camera performance
3. Is visualization slow? → Has GPU issues with drawing

### Inconsistent FPS

**Possible causes:**
1. System load (CPU usage, background processes)
2. GPU thermal throttling
3. Camera buffering
4. Dynamic model optimizations

**Solutions:**
1. Close other applications
2. Ensure proper ventilation
3. Restart camera/application
4. Check GPU temperature

### Graph Shows Red Spikes

**Occasional low FPS is normal** due to:
1. System interrupts
2. Model optimization kicks
3. Garbage collection

**Persistent low FPS** suggests:
1. Model too large for device
2. Input resolution too high
3. Insufficient GPU memory
4. System overheating

## Advanced: Custom Monitoring

You can integrate `FPSMonitor` into your own code:

```python
from run_realtime_detection import FPSMonitor
import cv2

monitor = FPSMonitor()

while True:
    start = time.time()
    
    # Your processing
    frame = camera.read()
    results = detector.detect(frame)
    
    inference_time = time.time() - start
    
    # Update monitor
    frame_time = time.time() - start
    monitor.update(frame_time, inference_time)
    
    # Display
    stats = monitor.get_summary()
    print(f"FPS: {stats['fps']:.1f}")
```

## Summary

The FPS monitoring system provides:

✅ Real-time performance visualization
✅ Detailed timing breakdown
✅ Multiple display options
✅ Performance trend analysis (FPS graph)
✅ Comprehensive statistics on exit

Use these tools to optimize your detection pipeline and ensure smooth real-time performance!
