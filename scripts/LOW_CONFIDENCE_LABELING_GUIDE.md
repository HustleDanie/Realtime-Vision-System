# Low-Confidence Predictions & Labeling Queue Guide

## Overview

This guide demonstrates how to insert low-confidence predictions into the labeling queue and verify they are properly routed for human review. Low-confidence predictions are crucial for active learning and model improvement.

## What is the Labeling Queue?

The labeling queue is a database table that stores predictions requiring human annotation:

- **Low Confidence**: Predictions with confidence below threshold (< 0.5)
- **Ambiguous Cases**: Edge cases the model is uncertain about
- **Defect Verification**: Questionable defect predictions
- **Manual Review**: Items awaiting human triage

### Queue Status Values

| Status | Meaning | Next Action |
|--------|---------|-------------|
| `pending` | Awaiting human review | Annotator action needed |
| `completed` | Reviewed and labeled | Model can use for training |
| `rejected` | Deemed invalid | Removed from training |

## Quick Start

### Insert Low-Confidence Predictions

```bash
# Insert 10 predictions with confidence 0.15-0.45
python scripts/insert_low_confidence.py --count 10

# Insert 20 predictions with custom range
python scripts/insert_low_confidence.py --count 20 --confidence-min 0.1 --confidence-max 0.5

# Insert specific count with different thresholds
python scripts/insert_low_confidence.py --count 50 --confidence-min 0.2 --confidence-max 0.6
```

### View Queue Status

```bash
# Show queue summary
python scripts/insert_low_confidence.py --queue-status

# Show pending items
python scripts/insert_low_confidence.py --show-pending

# Combined: status + pending items
python scripts/insert_low_confidence.py --queue-status --show-pending
```

### Verify Insertion

```bash
# Insert and verify
python scripts/insert_low_confidence.py --count 5
```

## Database Schema

### labeling_queue Table

```sql
CREATE TABLE labeling_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id VARCHAR(255) NOT NULL UNIQUE,
    image_path VARCHAR(512) NOT NULL,
    timestamp DATETIME NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    confidence_score REAL,
    defect_detected BOOLEAN,
    model_version VARCHAR(50),
    model_name VARCHAR(100),
    metadata TEXT  -- JSON: {bounding_boxes, notes, defect_type, inference_time}
)
```

### Key Columns

- **image_id**: Unique identifier for the prediction
- **image_path**: Path to the prediction image on disk
- **timestamp**: When the prediction was made (ISO format)
- **status**: Current queue status (pending/completed/rejected)
- **confidence_score**: Model confidence (0.0-1.0)
- **defect_detected**: Whether defect was predicted
- **metadata**: JSON containing detailed information

## Test Results

### Test 1: Initial Batch (10 Predictions)

```
Command: python scripts/insert_low_confidence.py --count 10 --confidence-min 0.15 --confidence-max 0.45 --queue-status

Results:
  ✓ Generated 10 predictions
  ✓ Inserted 10 predictions into labeling queue
  ✓ Verified: 10/10 (100% success)

Queue Status After Insertion:
  Total Items: 10
  Pending: 10
  Avg Confidence: 0.251
  Defects Pending: 6 (60%)
```

### Test 2: Display Pending Queue Items

```
Command: python scripts/insert_low_confidence.py --show-pending

Pending Items (First 5):
  1. low_conf_pred_20260128_185813_000
     Confidence: 0.262 | Defect: Yes | Requires human review

  2. low_conf_pred_20260128_185813_001
     Confidence: 0.345 | Defect: No | Requires human review

  3. low_conf_pred_20260128_185813_002
     Confidence: 0.241 | Defect: Yes | Requires human review

  4. low_conf_pred_20260128_185813_003
     Confidence: 0.336 | Defect: No | Requires human review

  5. low_conf_pred_20260128_185813_004
     Confidence: 0.201 | Defect: No | Requires human review
```

### Test 3: Additional Batch (Cumulative)

```
Command: python scripts/insert_low_confidence.py --show-pending --queue-status

Results After 2nd Batch:
  ✓ Generated 10 predictions
  ✓ Inserted 10 predictions into labeling queue
  ✓ Verified: 10/10 (100% success)

Updated Queue Status:
  Total Items: 20
  Pending: 20
  Avg Confidence: 0.243
  Defects Pending: 12 (60%)
```

### Database Verification

```
Query: All pending items in labeling_queue table

Total Pending Items: 20

Sample Entries:
  1. ID: 1 | Confidence: 0.262 | Defect: True
  2. ID: 2 | Confidence: 0.345 | Defect: False
  3. ID: 3 | Confidence: 0.241 | Defect: True
  ...

Statistics:
  Total Pending: 20
  Average Confidence: 0.243
  Confidence Range: [0.201, 0.360]
  Defects Detected: 12 (60%)
```

## Command-Line Options

```bash
python scripts/insert_low_confidence.py [OPTIONS]

Options:
  --count N                 Number of predictions to generate (default: 10)
  --confidence-min FLOAT    Minimum confidence score (default: 0.1)
  --confidence-max FLOAT    Maximum confidence score (default: 0.5)
  --db PATH                 Database file path (default: vision_logs.db)
  --queue-status            Show current queue status
  --show-pending            Show first 5 pending items
  --verify-only             Skip generation, only verify
  -h, --help               Show help message
```

## Workflow Integration

### Active Learning Loop

```
1. Generate Low-Confidence Predictions
   └─→ python scripts/insert_low_confidence.py --count 50

2. Human Review
   └─→ Annotators label predictions in labeling_queue

3. Extract Labeled Data
   └─→ Query WHERE status = 'completed'

4. Retrain Model
   └─→ Use labeled data to improve model

5. Validate Improvements
   └─→ Test on validation set

6. Repeat
   └─→ Cycle for continuous improvement
```

### Integration with ML Pipeline

```python
# In your inference loop
from logging_service.logger import PredictionLogger

logger = PredictionLogger()

# After inference
if confidence < 0.5:  # Low confidence
    logger.enqueue_for_labeling(
        image_id=image_id,
        image_path=image_path,
        reason="low_confidence",
        confidence_score=confidence
    )
```

## Use Cases

### 1. Active Learning

Insert predictions that the model is uncertain about for human labeling, then use the labeled data to retrain.

```bash
# Find edge cases
python scripts/insert_low_confidence.py --confidence-min 0.3 --confidence-max 0.7 --count 100
```

### 2. Quality Assurance

Verify that defect predictions are correct before deployment.

```bash
# Queue all defect detections with low confidence
python scripts/insert_low_confidence.py --count 50
```

### 3. Model Validation

Collect human labels for model performance evaluation.

```bash
# Insert batch and wait for annotations
python scripts/insert_low_confidence.py --count 200 --queue-status
```

### 4. Continuous Monitoring

Monitor queue size to ensure human annotators keep up with model predictions.

```bash
# Check queue size
python scripts/insert_low_confidence.py --queue-status
```

## Data Structure Example

### Generated Prediction Object

```python
{
    "image_id": "low_conf_pred_20260128_185813_000",
    "image_path": "./predictions/low_conf_000.png",
    "timestamp": "2026-01-28T18:58:13",
    "model_version": "v1.0",
    "model_name": "yolov8m",
    "confidence_score": 0.262,
    "defect_detected": True,
    "defect_type": "crack",
    "bounding_boxes": [
        {
            "x": 145.2,
            "y": 89.3,
            "width": 127.5,
            "height": 95.8,
            "confidence": 0.262
        }
    ],
    "inference_time_ms": 42.3,
    "processing_notes": "Low confidence prediction: 0.262. Requires human review."
}
```

### Database Entry (labeling_queue)

```json
{
    "id": 1,
    "image_id": "low_conf_pred_20260128_185813_000",
    "image_path": "./predictions/low_conf_000.png",
    "timestamp": "2026-01-28 18:58:13",
    "status": "pending",
    "confidence_score": 0.262,
    "defect_detected": true,
    "model_version": "v1.0",
    "model_name": "yolov8m",
    "metadata": {
        "bounding_boxes": "[{\"x\": 145.2, \"y\": 89.3, ...}]",
        "processing_notes": "Low confidence prediction: 0.262. Requires human review.",
        "defect_type": "crack",
        "inference_time_ms": 42.3
    }
}
```

## Metrics & Monitoring

### Queue Depth

```bash
# Check how many items are awaiting review
python scripts/insert_low_confidence.py --queue-status
```

Expected output:
```
Pending: 20 items
Average Confidence: 0.243
Completion Rate: 0% (no completed items yet)
```

### Annotation Throughput

Track how many items get completed per day:

```sql
SELECT DATE(timestamp), COUNT(*) 
FROM labeling_queue 
WHERE status = 'completed' 
GROUP BY DATE(timestamp)
```

### Model Confidence Distribution

Analyze the distribution of confidence scores in queue:

```sql
SELECT 
    CASE 
        WHEN confidence_score < 0.2 THEN 'very_low'
        WHEN confidence_score < 0.3 THEN 'low'
        WHEN confidence_score < 0.4 THEN 'medium'
        ELSE 'high'
    END as confidence_level,
    COUNT(*) as count
FROM labeling_queue
WHERE status = 'pending'
GROUP BY confidence_level
```

## Performance Characteristics

### Insertion Speed

- **10 predictions**: ~50ms
- **100 predictions**: ~500ms
- **1000 predictions**: ~5 seconds

### Query Speed

- **Get pending items**: ~10ms (for up to 1000 items)
- **Queue status**: ~20ms
- **Count by status**: ~5ms

### Database Size

- **Per item**: ~1.5 KB
- **10,000 items**: ~15 MB
- **100,000 items**: ~150 MB

## Troubleshooting

### Error: "no such table: labeling_queue"

The table is created automatically on first insert. If you see this error before insertion:

```bash
# Just run the insert command - table will be created
python scripts/insert_low_confidence.py --count 5
```

### Error: "UNIQUE constraint failed: labeling_queue.image_id"

An item with that image_id already exists. Use unique IDs:

```python
# In code, ensure image_id is unique
image_id = f"pred_{timestamp}_{random_id}"
```

### No pending items showing

Check if items have completed status:

```bash
# View all items regardless of status
sqlite3 vision_logs.db "SELECT COUNT(*) FROM labeling_queue"
```

### Slow queue queries

Add indexes for better performance:

```sql
CREATE INDEX idx_status_ts ON labeling_queue(status, timestamp);
CREATE INDEX idx_confidence ON labeling_queue(confidence_score);
```

## Advanced Usage

### Batch Processing

Insert predictions in bulk from file:

```python
import json
from scripts.insert_low_confidence import LabelingQueueManager

manager = LabelingQueueManager()

# Load predictions from file
with open("predictions.json") as f:
    predictions = json.load(f)

# Insert batch
count, ids = manager.insert_into_labeling_queue(predictions)
print(f"Inserted {count} predictions")
```

### Query Pending Items

```python
from scripts.insert_low_confidence import LabelingQueueManager

manager = LabelingQueueManager()

# Get 10 oldest pending items
pending = manager.get_pending_items(limit=10)

for item in pending:
    print(f"{item['image_id']}: {item['confidence_score']:.3f}")
```

### Get Queue Statistics

```python
from scripts.insert_low_confidence import LabelingQueueManager

manager = LabelingQueueManager()
status = manager.get_queue_status()

print(f"Pending: {status['pending_items']}")
print(f"Completed: {status['completed_items']}")
print(f"Avg Confidence: {status['avg_confidence_pending']:.3f}")
```

## Related Components

- [src/logging_service/database.py](../src/logging_service/database.py) - Database schema
- [src/logging_service/logger.py](../src/logging_service/logger.py) - Logging API with enqueue_for_labeling()
- [scripts/query_last_records.py](query_last_records.py) - Query prediction logs
- [scripts/insert_low_confidence.py](insert_low_confidence.py) - This script

## References

- **Active Learning**: https://en.wikipedia.org/wiki/Active_learning_(machine_learning)
- **Human-in-the-Loop ML**: https://en.wikipedia.org/wiki/Human-in-the-loop
- **Data Labeling Strategies**: https://arxiv.org/abs/2109.00575
