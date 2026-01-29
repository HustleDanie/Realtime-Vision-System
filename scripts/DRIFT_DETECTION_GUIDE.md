# Data Drift Detection & Simulation Guide

## Overview

This guide demonstrates how to simulate data drift in images and detect it using statistical methods. Drift detection is critical for monitoring machine learning pipelines to ensure model performance doesn't degrade over time.

## What is Data Drift?

Data drift occurs when the distribution of input data changes over time. Common causes in computer vision systems:

1. **Brightness Drift** - Camera exposure changes, lighting variations
2. **Blur Drift** - Focus degradation, vibration, lens issues
3. **Color Drift** - White balance changes, sensor aging
4. **Noise Drift** - Sensor degradation, electronic noise increase

## Quick Start

### Step 1: Simulate Drift

Generate synthetic images with controlled drift patterns:

```bash
# Generate all drift types
python scripts/simulate_drift.py --drift-type all --num-images 10

# Generate specific drift type
python scripts/simulate_drift.py --drift-type brightness --num-images 20

# Custom image size
python scripts/simulate_drift.py --drift-type blur --width 1280 --height 720
```

Output:
- `baseline_images/` - Baseline reference images
- `drifted_images/` - Images with applied drift

### Step 2: Detect Drift

Analyze the drifted images and compare to baseline:

```bash
# Run drift detection
python scripts/detect_drift.py --baseline ./baseline_images --drifted ./drifted_images

# Save results to JSON
python scripts/detect_drift.py --baseline ./baseline_images --drifted ./drifted_images --output results.json

# Verbose output
python scripts/detect_drift.py --baseline ./baseline_images --drifted ./drifted_images --verbose
```

## Test Results

### Test 1: Combined Drift (All Types)

Simulated: 10 baseline + 40 drifted images (brightness, blur, color, noise)

**Results:**
```
Drift Scores:
  Brightness Drift: 5.94 (p=0.0100) *
  Blur Drift: 1537.31 (p=0.2906)
  Histogram Drift: 1.1426 (p=0.0000) *
  
Overall Drift Score: 0.5360 ⚠️ MODERATE DRIFT
```

**Interpretation:**
- **Brightness** significantly changed (p < 0.05)
- **Color distribution** significantly changed (p < 0.05)
- **Blur** increased but not statistically significant
- **Overall**: Moderate drift requiring attention

### Test 2: Brightness Drift Only

Simulated: Progressive 5% brightness increase per image (10 baseline, 8 drifted)

**Results:**
```
Drift Scores:
  Brightness Drift: 9.28 (p=0.0004) *
  Blur Drift: 894.68 (p=0.0005) *
  Histogram Drift: 0.8757 (p=0.0002) *
  
Overall Drift Score: 0.3321 ⚠️ MODERATE DRIFT
```

**Interpretation:**
- **Brightness** highly significant (p=0.0004)
- All metrics show significant changes
- Brightness drift is the primary detector

## Drift Simulation Options

### Brightness Drift

Gradually increases pixel intensity to simulate:
- Camera exposure compensation
- Gradual lighting changes
- Sensor drift

```bash
python scripts/simulate_drift.py --drift-type brightness --num-images 20
```

**Parameters:**
- `drift_rate`: 0.02 (2% increase per image, adjustable in code)
- Output: Progressive brightening visible in saved images

### Blur Drift

Progressively applies Gaussian blur to simulate:
- Focus degradation
- Lens contamination
- Vibration/movement

```bash
python scripts/simulate_drift.py --drift-type blur --num-images 15
```

**Parameters:**
- `max_kernel`: 15 (maximum blur kernel size)
- Kernel progression: 3 → 5 → 7 → 9 → 11 → 13 → 15

### Color Drift

Shifts color channels to simulate:
- White balance changes
- Sensor aging
- Light spectrum changes

```bash
python scripts/simulate_drift.py --drift-type color --num-images 10
```

**Parameters:**
- `channel_shift`: (5, 10, 15) for BGR channels
- Constant shift applied to all images

### Noise Drift

Progressively adds Gaussian noise to simulate:
- Sensor thermal noise
- Electronic degradation
- CCD/CMOS aging

```bash
python scripts/simulate_drift.py --drift-type noise --num-images 20
```

**Parameters:**
- `noise_scale`: 0.02 (base noise level)
- Noise increases 2%, 4%, 6%, etc. per image

### Combined Drift

Apply all drift types simultaneously:

```bash
python scripts/simulate_drift.py --drift-type all --num-images 10
```

Generates 40 drifted images total (10 per drift type)

## Drift Detection Methods

### 1. Brightness Analysis

Compares mean pixel intensity between baseline and drifted images.

```
Formula: |mean(drifted) - mean(baseline)|
```

**Statistical Test:** Two-sample t-test
- **Null Hypothesis:** No brightness difference
- **P-value < 0.05:** Significant change detected

**Use Cases:**
- Exposure compensation detection
- Lighting change detection
- Sensor gain adjustment

### 2. Blur Detection

Uses Laplacian variance as blur metric (Brenner gradient).

```
Formula: variance(Laplacian(image))
Higher variance = sharper image
Lower variance = blurrier image
```

**Statistical Test:** Two-sample t-test
- **Null Hypothesis:** No blur change
- **P-value < 0.05:** Focus degradation detected

**Use Cases:**
- Focus degradation detection
- Lens contamination warning
- Vibration/movement detection

### 3. Color Histogram Analysis

Compares pixel value distributions across color channels.

```
Formula: Chi-square distance between histograms
distance = Σ((H1 - H2)² / (H1 + H2))
```

**Statistical Test:** Kolmogorov-Smirnov test
- **Null Hypothesis:** Same color distribution
- **P-value < 0.05:** Color distribution changed

**Use Cases:**
- White balance changes
- Sensor aging detection
- Light spectrum shifts

### 4. Overall Drift Score

Combines all metrics into normalized 0-1 scale:

```
score = (brightness_drift/100 + blur_drift/1000 + histogram_drift/100) / 3
```

**Interpretation:**
- **0.0 - 0.1:** No drift
- **0.1 - 0.3:** Mild drift (monitor)
- **0.3 - 0.7:** Moderate drift (investigate)
- **0.7 - 1.0:** Severe drift (alert)

## Integration with ML Pipeline

### Baseline Establishment

1. Collect images when system is known to be working well
2. Run drift simulation on baseline (should show ~0 drift)
3. Save baseline statistics for comparison

```python
from scripts.detect_drift import DriftDetector

detector = DriftDetector()
results = detector.analyze("./good_images", "./good_images")
baseline_score = results["drift_scores"]["overall_drift_score"]
print(f"Baseline drift: {baseline_score}")  # Should be ~0
```

### Production Monitoring

Continuously compare new data to baseline:

```python
# In your inference loop
detector = DriftDetector()
results = detector.analyze("./baseline", "./recent_predictions")

if results["drift_scores"]["overall_drift_score"] > 0.3:
    # Alert: Moderate drift detected
    log.warning("Data drift detected! Check camera settings.")
    # Optionally retrain model
```

### Drift Response Actions

Based on drift detection score:

| Score | Action |
|-------|--------|
| < 0.1 | Continue normal operation |
| 0.1 - 0.3 | Log warning, increase monitoring frequency |
| 0.3 - 0.7 | Alert operators, trigger model revalidation |
| > 0.7 | Critical alert, disable auto-inference, manual review |

## File Structure

```
scripts/
├── simulate_drift.py           # Drift simulation tool
├── detect_drift.py             # Drift detection tool
└── DRIFT_DETECTION_GUIDE.md    # This file

baseline_images/               # Generated baseline images
├── baseline_000.png
├── baseline_001.png
...

drifted_images/               # Generated drifted images
├── brightness_drift_000.png
├── blur_drift_000.png
├── color_drift_000.png
├── noise_drift_000.png
...

drift_results.json            # Detection results
```

## Advanced Usage

### Custom Drift Parameters

Edit `simulate_drift.py` to adjust drift rates:

```python
# Line ~140 - Brightness drift rate
drifted, factors = apply_brightness_drift(baseline_images, drift_rate=0.10)  # 10% per image

# Line ~160 - Blur maximum kernel
drifted, kernels = apply_blur_drift(baseline_images, max_kernel=25)  # Max kernel 25

# Line ~180 - Color channel shifts
drifted, shift = apply_color_drift(baseline_images, channel_shift=(10, 20, 30))

# Line ~200 - Noise scale
drifted, levels = apply_noise_drift(baseline_images, noise_scale=0.05)  # 5% base
```

### Batch Analysis

Compare multiple drift scenarios:

```bash
#!/bin/bash
for drift_type in brightness blur color noise all; do
    echo "Testing $drift_type drift..."
    python scripts/simulate_drift.py --drift-type $drift_type --output ./baseline ./test_$drift_type
    python scripts/detect_drift.py --baseline ./baseline --drifted ./test_$drift_type --output results_$drift_type.json
done
```

### Real Camera Feed Integration

Use drift detection on live camera stream:

```python
import cv2
from scripts.detect_drift import DriftDetector

# Collect baseline frames
baseline = []
cap = cv2.VideoCapture(0)
for i in range(30):
    ret, frame = cap.read()
    baseline.append(frame)

# Later, check for drift
detector = DriftDetector()
recent = [frame for frame in buffer[-30:]]  # Last 30 frames

results = detector.analyze(baseline, recent)
drift_score = results["drift_scores"]["overall_drift_score"]

if drift_score > threshold:
    print("Alert: Camera drift detected!")
```

## Troubleshooting

### OpenCV Import Error

```
Error: OpenCV not available
Solution: pip install opencv-python
```

### Scipy Not Found

```
Error: No module named 'scipy'
Solution: pip install scipy
```

### Image Files Not Loading

- Check file extensions are .png, .jpg, or .npy
- Verify paths are correct
- Use `--verbose` flag for debugging

### No Drift Detected When Expected

Possible causes:
- Drift magnitude too small (adjust parameters in simulate_drift.py)
- Image size too small (try --width 1280 --height 720)
- Number of images too small (need sufficient samples for statistics)

Solution: Increase `--num-images` parameter

### P-value > 0.05 But Drift Visible

This is normal - requires statistical significance, not just visual difference:
- Small sample sizes reduce power
- Try `--num-images 50` or more
- Natural variation can mask small drifts

## Performance Metrics

### Execution Time (10 baseline + 10 drifted images):

| Operation | Time |
|-----------|------|
| Baseline generation | ~100ms |
| Drift application (all types) | ~200ms |
| Feature extraction | ~500ms |
| Drift detection | ~100ms |
| **Total** | **~900ms** |

### Memory Usage:

- Per image: ~1.2 MB (640x480 RGB)
- 20 images: ~24 MB
- Scales linearly with image count

## References

- **Brenner Gradient** (Blur Detection): Brenner, J. F., et al. (1976)
- **Kolmogorov-Smirnov Test**: https://en.wikipedia.org/wiki/Kolmogorov%E2%80%93Smirnov_test
- **Chi-Square Distance**: https://en.wikipedia.org/wiki/Chi-squared_test
- **Data Drift in ML**: https://ml-ops.systems/content/data-drift

## Related Files

- [scripts/simulate_drift.py](simulate_drift.py) - Drift simulation
- [scripts/detect_drift.py](detect_drift.py) - Drift detection
- [scripts/mlflow_experiments_info.py](mlflow_experiments_info.py) - Model experiment tracking
- [scripts/query_last_records.py](query_last_records.py) - Database query tool
