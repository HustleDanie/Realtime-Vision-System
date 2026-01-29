# Test Fake Detections - Quick Guide

## Overview

This test script generates 10 fake detection images with bounding boxes and verifies they are properly saved to both the database and image folder.

## What It Tests

1. **Image Generation** - Creates realistic fake detection images with:
   - Random background patterns
   - Grid overlays
   - Colored bounding boxes for defects
   - Text labels

2. **Database Logging** - Verifies:
   - All detections are saved to SQLite database
   - Metadata is correctly stored (confidence, defect type, bounding boxes)
   - Database queries return expected results

3. **Image Storage** - Verifies:
   - Images are saved to disk in organized folders
   - Images are not corrupted and can be read
   - File paths match database records

## Running the Test

### Basic Usage

```bash
# From project root
python tests/test_fake_detections.py
```

### Expected Output

```
======================================================================
FAKE DETECTION TEST SUITE - 10 DETECTIONS
======================================================================

Test Configuration:
  Database: sqlite:///./test_outputs/test_vision_logs.db
  Images: test_outputs/test_prediction_images
  Model: test-yolov8n vtest-v1.0

======================================================================
STEP 1: GENERATING AND LOGGING DETECTIONS
======================================================================
✓ Logged detection #1: id=1, defect=True, boxes=3
✓ Logged detection #2: id=2, defect=True, boxes=2
✓ Logged detection #3: id=3, defect=False, boxes=0
✓ Logged detection #4: id=4, defect=True, boxes=4
✓ Logged detection #5: id=5, defect=True, boxes=1
✓ Logged detection #6: id=6, defect=True, boxes=5
✓ Logged detection #7: id=7, defect=False, boxes=0
✓ Logged detection #8: id=8, defect=True, boxes=2
✓ Logged detection #9: id=9, defect=True, boxes=3
✓ Logged detection #10: id=10, defect=True, boxes=4

======================================================================
VERIFYING DATABASE ENTRIES
======================================================================
✓ Found in DB: id=1, image_id=test_detection_001_..., defect=True
✓ Found in DB: id=2, image_id=test_detection_002_..., defect=True
...
✓ Found in DB: id=10, image_id=test_detection_010_..., defect=True

Database Summary:
  Total entries: 10
  Defects: 8
  No defects: 2

======================================================================
VERIFYING IMAGE FILES
======================================================================
✓ Image exists: test_detection_001_....jpg (shape: (480, 640, 3))
✓ Image exists: test_detection_002_....jpg (shape: (480, 640, 3))
...
✓ Image exists: test_detection_010_....jpg (shape: (480, 640, 3))

Image Directory Summary:
  Base path: test_outputs/test_prediction_images
  Total image files: 10

======================================================================
FINAL TEST REPORT
======================================================================

Generation & Logging:
  Total detections logged: 10
  With defects: 8
  Without defects: 2

Verification:
  Database entries verified: 10/10
  Image files verified: 10/10

======================================================================
✓ ALL TESTS PASSED
======================================================================

✓ Test completed successfully!
```

## Output Locations

After running the test, you'll find:

- **Database**: `test_outputs/test_vision_logs.db`
- **Images**: `test_outputs/test_prediction_images/`
  - Organized by date: `YYYY/MM/DD/`
  - Organized by result: `defects/` or `no_defects/`

## Test Structure

### FakeDetectionGenerator

Generates realistic fake detection images:
- Dimensions: 640x480 pixels
- Random noise patterns
- Grid overlay for industrial look
- Colored bounding boxes
- Text labels for defect types

### DetectionTestSuite

Orchestrates the complete test:
1. Configures test environment
2. Generates fake detections
3. Logs to database and disk
4. Verifies database entries
5. Verifies image files
6. Prints comprehensive report

## Customization

### Change Number of Detections

Edit the `main()` function:

```python
# Generate 20 detections instead of 10
success = test_suite.run_full_test(num_detections=20)
```

### Change Image Dimensions

Edit the `DetectionTestSuite` initialization:

```python
self.generator = FakeDetectionGenerator(width=1280, height=720)
```

### Change Test Output Directory

```python
test_suite = DetectionTestSuite(test_dir="./my_test_dir")
```

### Add Custom Defect Types

Edit the `FakeDetectionGenerator.__init__`:

```python
self.defect_types = [
    "scratch", "dent", "crack", "custom_defect_1", "custom_defect_2"
]
```

## Interpreting Results

### Success Indicators

✓ All tests pass when:
- All detections are logged without errors
- All database entries are found
- All image files exist and are readable
- No errors in the error list

### Common Issues

**Database locked**:
- Close any SQLite browser applications
- Delete `test_outputs/test_vision_logs.db` and retry

**Permission errors**:
- Ensure `test_outputs/` directory is writable
- Run from project root directory

**Import errors**:
- Ensure you're in the project root
- Activate virtual environment if using one

## Integration with Real Pipeline

This test validates the same code path used in production:
- `VisionLogger.log_prediction()` - Same method
- Database schema - Same tables and columns
- Image storage - Same directory structure

## Cleanup

To remove test outputs:

```bash
# PowerShell
Remove-Item -Recurse -Force test_outputs

# Linux/Mac
rm -rf test_outputs/
```

## Viewing Test Images

Open any generated image to see:
- Background noise pattern
- Grid overlay
- Bounding boxes (colored rectangles)
- Defect labels (text above boxes)
- Test image identifier

## Database Inspection

Use SQLite browser or command line:

```bash
# Open database
sqlite3 test_outputs/test_vision_logs.db

# Query all detections
SELECT id, image_id, defect_detected, confidence_score, defect_type 
FROM prediction_logs;

# Count by defect type
SELECT defect_type, COUNT(*) 
FROM prediction_logs 
GROUP BY defect_type;
```

## Exit Codes

- `0` - All tests passed
- `1` - Some tests failed

Useful for CI/CD integration:

```bash
python tests/test_fake_detections.py && echo "Success" || echo "Failed"
```

## Dependencies

Required packages (already in requirements.txt):
- numpy
- opencv-python (cv2)
- sqlalchemy

## Next Steps

After successful test:
1. Inspect generated images in `test_outputs/test_prediction_images/`
2. Query database using SQLite browser
3. Integrate with CI/CD pipeline
4. Add to automated test suite
5. Customize for specific defect types

---

**Quick Test**: Just run `python tests/test_fake_detections.py` and look for `✓ ALL TESTS PASSED` at the end!
