# Debug Logging Guide - Frame Capture, Preprocessing, and YOLO Inference

This guide shows how to enable and use the debug logging for the real-time vision pipeline.

## Overview

Debug logging has been added at three critical stages:

1. **Frame Capture** - Shows when frames are captured from the camera
2. **Preprocessing** - Shows each preprocessing step (resize, normalize, color conversion)
3. **YOLO Inference** - Shows when YOLO processes frames and detection results

## Enabling Debug Logging

### Option 1: Environment Variable (Recommended)

```bash
# Windows PowerShell
$env:PYTHONUNBUFFERED=1
python run_realtime_detection.py --device gpu

# Windows Command Prompt
set PYTHONUNBUFFERED=1
python run_realtime_detection.py --device gpu

# Linux/Mac
export PYTHONUNBUFFERED=1
python run_realtime_detection.py --device gpu
```

### Option 2: Python Code

```python
import logging

# Enable DEBUG logging for all modules
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Or enable just for specific modules
logging.getLogger('src.video_streaming').setLevel(logging.DEBUG)
logging.getLogger('src.preprocessing').setLevel(logging.DEBUG)
logging.getLogger('src.yolo_inference').setLevel(logging.DEBUG)
```

### Option 3: Logging Config File

Edit `config_logging.json`:

```json
{
  "version": 1,
  "disable_existing_loggers": false,
  "formatters": {
    "standard": {
      "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    }
  },
  "handlers": {
    "console": {
      "class": "logging.StreamHandler",
      "level": "DEBUG",
      "formatter": "standard",
      "stream": "ext://sys.stdout"
    }
  },
  "loggers": {
    "src.video_streaming": {
      "level": "DEBUG",
      "handlers": ["console"]
    },
    "src.preprocessing": {
      "level": "DEBUG",
      "handlers": ["console"]
    },
    "src.yolo_inference": {
      "level": "DEBUG",
      "handlers": ["console"]
    }
  },
  "root": {
    "level": "DEBUG",
    "handlers": ["console"]
  }
}
```

## Debug Log Output Examples

### Frame Capture Logs

```
DEBUG - src.video_streaming.camera - Frame captured: #1 | shape=(480, 640, 3) | source=0
DEBUG - src.video_streaming.camera - Frame stored in buffer | FPS: 30.0
DEBUG - src.video_streaming.camera - Frame captured: #2 | shape=(480, 640, 3) | source=0
DEBUG - src.video_streaming.camera - Frame stored in buffer | FPS: 30.1
```

**What it shows:**
- Frame number (sequential counter)
- Image shape (height, width, channels)
- Camera source (0 = default webcam)
- Current FPS being achieved

### Preprocessing Logs

```
DEBUG - src.preprocessing.image_processor - Preprocessing started | input_shape=(480, 640, 3) | dtype=uint8 | target_size=(640, 480)
DEBUG - src.preprocessing.image_processor - Resizing: (640, 480) → (640, 480)
DEBUG - src.preprocessing.image_processor - Resizing | output_shape=(480, 640, 3)
DEBUG - src.preprocessing.image_processor - Converting color space: BGR → RGB
DEBUG - src.preprocessing.image_processor - Color converted | shape=(480, 640, 3)
DEBUG - src.preprocessing.image_processor - Normalizing pixels | type=0-1
DEBUG - src.preprocessing.image_processor - Normalized | dtype=float32
DEBUG - src.preprocessing.image_processor - Preprocessing complete | output_shape=(480, 640, 3) | time=2.34ms
```

**What it shows:**
- Input dimensions and data type
- Each preprocessing step and its effect
- Total preprocessing time in milliseconds
- Output dimensions and final data type

### YOLO Inference Logs

```
DEBUG - src.yolo_inference.detector - YOLO inference started | image_shape=(480, 640, 3) | dtype=uint8 | model=yolov8 | device=cuda:0
DEBUG - src.yolo_inference.detector - Running YOLOv8 forward pass | conf_threshold=0.5 | nms_threshold=0.4
DEBUG - src.yolo_inference.detector - YOLOv8 forward pass complete | raw_results=1
DEBUG - src.yolo_inference.detector - Processing YOLOv8 results | num_boxes=3
DEBUG - src.yolo_inference.detector - YOLOv8 inference complete | detections=3 | time=45.12ms
```

**What it shows:**
- Input image shape and device (GPU/CPU)
- Model type and confidence thresholds
- Number of detections found
- Total inference time in milliseconds

## Complete Pipeline Flow

A complete frame processing cycle would show:

```
1. Frame Capture (0.033s for 30fps):
   Frame captured: #125 | shape=(480, 640, 3)
   Frame stored in buffer | FPS: 30.0

2. Preprocessing (2-5ms):
   Preprocessing started | input_shape=(480, 640, 3)
   Resizing: (640, 480) → (640, 480)
   Converting color space: BGR → RGB
   Normalizing pixels | type=0-1
   Preprocessing complete | time=2.34ms

3. YOLO Inference (20-100ms):
   YOLO inference started | image_shape=(480, 640, 3) | device=cuda:0
   Running YOLOv8 forward pass | conf_threshold=0.5
   Processing YOLOv8 results | num_boxes=5
   YOLOv8 inference complete | detections=5 | time=45.12ms
```

## Performance Analysis

Use these logs to analyze performance:

### Bottleneck Detection

```
Preprocessing complete | time=2.34ms     ← Fast
YOLOv8 inference complete | time=45.12ms ← Slow = GPU bound
```

If preprocessing is slow (>10ms), check:
- Target resolution (try smaller for faster processing)
- Number of custom transforms
- CPU usage

If inference is slow (>100ms), check:
- Model size (try smaller model like yolov8n)
- GPU memory availability
- Concurrent processes

### Frame Rate Monitoring

```
Frame stored in buffer | FPS: 30.1
Frame stored in buffer | FPS: 30.2
Frame stored in buffer | FPS: 29.8
Frame stored in buffer | FPS: 30.0
```

Watch for:
- Dropping FPS = GPU overloaded
- Erratic FPS = Other processes stealing resources
- Consistent FPS = Everything working well

## Useful Log Filtering

### Show only frame capture:
```bash
python run_realtime_detection.py 2>&1 | grep "Frame captured"
```

### Show only preprocessing:
```bash
python run_realtime_detection.py 2>&1 | grep "Preprocessing"
```

### Show only YOLO inference:
```bash
python run_realtime_detection.py 2>&1 | grep "YOLO inference"
```

### Show only timing information:
```bash
python run_realtime_detection.py 2>&1 | grep "time="
```

### Redirect to file for analysis:
```bash
python run_realtime_detection.py 2>&1 > debug_logs.txt
```

## Log Fields Reference

| Field | Example | Meaning |
|-------|---------|---------|
| `#N` | `#125` | Frame sequence number |
| `shape=` | `(480, 640, 3)` | Image dimensions (height, width, channels) |
| `dtype=` | `uint8` or `float32` | Data type of pixel values |
| `source=` | `0` | Camera source (0=webcam, filepath, or RTSP URL) |
| `FPS:` | `30.0` | Current frames per second |
| `time=` | `2.34ms` | Processing time in milliseconds |
| `conf_threshold=` | `0.5` | Minimum confidence for detections |
| `nms_threshold=` | `0.4` | Non-maximum suppression threshold |
| `device=` | `cuda:0` | Processing device (GPU or CPU) |
| `detections=` | `5` | Number of objects detected |
| `type=` | `0-1` | Normalization type |

## Troubleshooting

### No debug logs appearing?

1. Check log level is set to DEBUG:
   ```python
   logging.getLogger().setLevel(logging.DEBUG)
   ```

2. Check PYTHONUNBUFFERED is set:
   ```bash
   echo $env:PYTHONUNBUFFERED  # Windows PowerShell
   echo $PYTHONUNBUFFERED      # Linux/Mac
   ```

3. Logs might be buffered. Use unbuffered output:
   ```bash
   python -u run_realtime_detection.py
   ```

### Logs are too verbose?

Set specific modules to DEBUG:
```python
logging.getLogger('src.yolo_inference').setLevel(logging.DEBUG)
logging.getLogger().setLevel(logging.INFO)  # Keep others at INFO
```

### Performance is degraded with logging?

Debug logging has minimal overhead (<1-2%), but if concerned:
- Use INFO level instead of DEBUG
- Redirect logs to file instead of console
- Filter to only the stages you care about

## Integration with Monitoring

These logs integrate with the monitoring system created earlier:

```python
from src.monitoring.structured_logging import setup_structured_logging

logger = setup_structured_logging('vision-pipeline')

# Now logs include timestamps, service name, and structured format:
# 2026-01-28T15:30:45.123456 - vision-pipeline - DEBUG - Frame captured: #125
```

## Next Steps

1. **Enable debug logging** using one of the options above
2. **Run the pipeline** and observe the logs
3. **Identify bottlenecks** (preprocessing or YOLO inference)
4. **Optimize** based on what you find:
   - Large preprocessing time → reduce resolution or transforms
   - Large inference time → use smaller model or GPU
   - Dropping FPS → reduce batch processing or concurrent operations
5. **Monitor production** with DEBUG level in specific scenarios

## Example: Complete Setup with Debug Logging

```bash
# 1. Set environment
$env:PYTHONUNBUFFERED=1

# 2. Run with debug logging
python run_realtime_detection.py \
  --model yolov8n.pt \
  --conf 0.5 \
  --device auto \
  2>&1 | Tee-Object -FilePath debug_run_$(Get-Date -Format 'yyyyMMdd_HHmmss').log
```

This will:
- Enable unbuffered output
- Run detection
- Save logs to `debug_run_20260128_153045.log`
- Also display logs on console

---

**Debug logging is enabled by default in the code. Simply set your log level to DEBUG to see these messages!**
