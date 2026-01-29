# Debug Logging - Quick Reference Card

## Enable Debug Logging (Choose One)

### PowerShell
```powershell
$env:PYTHONUNBUFFERED=1
python run_realtime_detection.py
```

### Command Prompt
```cmd
set PYTHONUNBUFFERED=1 & python run_realtime_detection.py
```

### Linux/Mac
```bash
export PYTHONUNBUFFERED=1
python run_realtime_detection.py
```

### Python Code
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Debug Log Locations

| Stage | File | Method | What It Shows |
|-------|------|--------|---------------|
| **Capture** | `src/video_streaming/camera.py` | `_update_frame()` | Frame #, shape, FPS |
| **Preprocess** | `src/preprocessing/image_processor.py` | `process()` | Resize, color conversion, normalization, timing |
| **YOLO** | `src/yolo_inference/detector.py` | `detect()` | Image shape, device, detections, time |

---

## Log Output Examples

### Frame Capture
```
Frame captured: #125 | shape=(480, 640, 3) | source=0
Frame stored in buffer | FPS: 30.0
```

### Preprocessing (Complete)
```
Preprocessing started | input_shape=(480, 640, 3) | dtype=uint8 | target_size=(640, 480)
Resizing: (640, 480) → (640, 480)
Resized | output_shape=(480, 640, 3)
Converting color space: BGR → RGB
Color converted | shape=(480, 640, 3)
Normalizing pixels | type=0-1
Normalized | dtype=float32
Preprocessing complete | output_shape=(480, 640, 3) | time=2.34ms
```

### YOLO Inference
```
YOLO inference started | image_shape=(480, 640, 3) | dtype=uint8 | model=yolov8 | device=cuda:0
Running YOLOv8 forward pass | conf_threshold=0.5 | nms_threshold=0.4
YOLOv8 forward pass complete | raw_results=1
Processing YOLOv8 results | num_boxes=5
YOLOv8 inference complete | detections=5 | time=45.12ms
```

---

## Filter Logs

### Show Only Frame Capture
```bash
python run_realtime_detection.py 2>&1 | grep "Frame"
```

### Show Only Preprocessing
```bash
python run_realtime_detection.py 2>&1 | grep "Preprocessing"
```

### Show Only YOLO
```bash
python run_realtime_detection.py 2>&1 | grep "YOLO"
```

### Show Only Timing (All stages)
```bash
python run_realtime_detection.py 2>&1 | grep "time="
```

### Save to File
```bash
python run_realtime_detection.py 2>&1 > debug_logs.txt
```

---

## Performance Analysis

### Benchmark Values (Reference)

| Stage | Time | Notes |
|-------|------|-------|
| Frame Capture | ~33ms | 30fps = 1 frame every 33ms |
| Preprocessing | 2-5ms | Fast, CPU-bound |
| YOLO Inference | 20-100ms | Varies by model size and GPU |
| **Total** | **55-138ms** | 7-18 FPS theoretical (with other overhead) |

### Slow Preprocessing? (>10ms)
- Reduce target resolution (e.g., 640x480 → 416x416)
- Remove custom transforms
- Check CPU usage

### Slow YOLO? (>100ms)
- Use smaller model (yolov8n instead of yolov8m)
- Enable GPU (--device gpu)
- Check GPU memory: `nvidia-smi`

### Dropping FPS?
- Watch for erratic FPS values
- Monitor system resources
- Check for other background processes

---

## Debug Log Fields

| Field | Example | Meaning |
|-------|---------|---------|
| `#N` | `#125` | Frame sequence number |
| `shape=` | `(480, 640, 3)` | H×W×C dimensions |
| `dtype=` | `uint8` | Data type (uint8 or float32) |
| `source=` | `0` | Camera source (0=webcam) |
| `FPS:` | `30.0` | Current frame rate |
| `time=` | `2.34ms` | Processing time |
| `device=` | `cuda:0` | GPU or CPU |
| `detections=` | `5` | Objects found |

---

## Full Documentation

For detailed information, see:
- [DEBUG_LOGGING_GUIDE.md](DEBUG_LOGGING_GUIDE.md) - Complete guide with examples
- [DEBUG_LOGGING_SUMMARY.md](DEBUG_LOGGING_SUMMARY.md) - Implementation details

---

## Common Issues

| Issue | Solution |
|-------|----------|
| No debug logs showing | Set log level to DEBUG: `logging.basicConfig(level=logging.DEBUG)` |
| Logs are buffered | Use unbuffered output: `python -u run_realtime_detection.py` |
| Performance degraded | Debug logs have <1% overhead; use INFO level if concerned |
| Too verbose | Filter by stage using grep patterns above |

---

**Quick Start:** Run `python run_realtime_detection.py` with DEBUG logging enabled to see the complete pipeline trace!
