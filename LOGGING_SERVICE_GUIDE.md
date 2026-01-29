# ML Vision Logging Service

## Overview

A comprehensive logging service for ML vision systems that coordinates:
- **Image Storage**: Saves prediction images to disk with organized directory structure
- **Database Logging**: Stores prediction metadata in SQL database
- **Metadata Tracking**: Records image ID, timestamp, model version, confidence, and defect information
- **Query & Analytics**: Retrieve predictions, generate statistics, and export data

## Features

### 📸 Image Storage
- Organized by date (YYYY/MM/DD)
- Organized by result (defects/no_defects)
- Configurable JPEG quality
- Automatic cleanup of old images
- Storage statistics and monitoring

### 🗄️ Database
- SQLAlchemy ORM models
- Support for SQLite, PostgreSQL, MySQL
- Automatic schema migration
- Indexed queries for performance
- Connection pooling

### 📊 Metadata Tracking
- Image ID and path
- Prediction timestamp
- Model version and name
- Confidence score
- Defect detection status
- Defect type classification
- Bounding boxes (JSON)
- Inference time
- Processing notes

### 🔍 Query Capabilities
- Get prediction by ID
- Query by date range
- Filter by defect status
- Filter by defect type
- Filter by model version
- Generate statistics
- Export to JSON

## Installation

### Database Driver (Choose One)

```bash
# SQLite (default, no additional install needed)
# Already included in Python

# PostgreSQL
pip install psycopg2-binary

# MySQL
pip install mysqlclient
```

### Logging Service Dependencies
```bash
pip install sqlalchemy opencv-python numpy
```

## Quick Start

### Basic Usage

```python
from src.logging_service import VisionLogger, LoggingServiceConfig

# Create configuration
config = LoggingServiceConfig(
    model_version="yolov8m_v1.0",
    model_name="yolov8m",
)

# Initialize logger
logger = VisionLogger(config)

# Log a prediction
pred_id = logger.log_prediction(
    image=frame,                    # OpenCV image
    image_id="sample_001",          # Unique ID
    confidence=0.95,                # 0.0-1.0
    defect_detected=True,
    defect_type="crack",
    bounding_boxes=[...],           # Optional
    inference_time_ms=42.5,
    processing_notes="Small crack detected"
)

# Retrieve prediction
prediction = logger.get_prediction(pred_id)

# Get statistics
stats = logger.get_statistics()

# Cleanup
logger.cleanup()
```

### With Context Manager

```python
with VisionLogger(config) as logger:
    logger.log_prediction(...)
    predictions = logger.get_defect_predictions()
```

## Configuration

### LoggingServiceConfig

```python
from src.logging_service import LoggingServiceConfig

config = LoggingServiceConfig(
    # Database configuration
    database__url="sqlite:///./vision_logs.db",
    database__echo=False,
    database__pool_size=10,
    database__max_overflow=20,
    database__auto_migrate=True,
    
    # Storage configuration
    storage__base_path="./prediction_images",
    storage__organize_by_date=True,
    storage__organize_by_result=True,
    storage__image_quality=95,
    storage__max_image_age_days=90,
    
    # Logging configuration
    logging__log_level="INFO",
    logging__log_file="./logs/vision_logger.log",
    
    # Model information
    model_version="yolov8m_v1.0",
    model_name="yolov8m",
)
```

### Load from JSON File

```python
config = LoggingServiceConfig.from_json_file("config.json")
config.save_to_json("output_config.json")
```

### JSON Configuration File

```json
{
  "database": {
    "url": "sqlite:///./vision_logs.db",
    "echo": false,
    "auto_migrate": true
  },
  "storage": {
    "base_path": "./prediction_images",
    "organize_by_date": true,
    "organize_by_result": true,
    "image_quality": 95
  },
  "logging": {
    "log_level": "INFO",
    "log_file": "./logs/vision_logger.log"
  },
  "model_version": "yolov8m_v1.0",
  "model_name": "yolov8m"
}
```

## Database Configuration

### SQLite (Default)
```python
db_url = "sqlite:///./vision_logs.db"
```

### PostgreSQL
```python
db_url = "postgresql://user:password@localhost:5432/vision_db"
```

### MySQL
```python
db_url = "mysql+mysqldb://user:password@localhost:3306/vision_db"
```

## API Reference

### VisionLogger Class

#### Methods

##### `log_prediction(...) -> int`
Log a complete prediction with image and metadata.

```python
pred_id = logger.log_prediction(
    image: cv2.Mat,                          # OpenCV image
    image_id: str,                           # Unique ID
    confidence: float,                       # 0.0-1.0
    defect_detected: bool,
    timestamp: Optional[datetime] = None,
    defect_type: Optional[str] = None,
    bounding_boxes: Optional[List[Dict]] = None,
    inference_time_ms: Optional[float] = None,
    processing_notes: Optional[str] = None,
) -> int  # Returns prediction ID
```

##### `get_prediction(prediction_id: int) -> Dict`
Retrieve prediction by ID.

```python
prediction = logger.get_prediction(123)
# Returns: {
#   "id": 123,
#   "image_id": "sample_001",
#   "image_path": "2024/01/27/defects/pred_20240127_120000_abc123.jpg",
#   "timestamp": "2024-01-27T12:00:00",
#   "model_version": "yolov8m_v1.0",
#   "model_name": "yolov8m",
#   "confidence_score": 0.95,
#   "defect_detected": true,
#   "defect_type": "crack",
#   "bounding_boxes": "[...]",
#   "inference_time_ms": 42.5,
#   "processing_notes": "..."
# }
```

##### `get_predictions_by_date(start_date, end_date) -> List[Dict]`
Get predictions within date range.

```python
from datetime import datetime, timedelta

start = datetime(2024, 1, 1)
end = datetime(2024, 1, 31)
predictions = logger.get_predictions_by_date(start, end)
```

##### `get_defect_predictions(defect_type=None, limit=100) -> List[Dict]`
Get all defect predictions with optional filtering.

```python
# Get all defects
all_defects = logger.get_defect_predictions()

# Get specific defect type
cracks = logger.get_defect_predictions(defect_type="crack", limit=50)
```

##### `get_predictions_by_model(model_version, limit=100) -> List[Dict]`
Get predictions made by specific model version.

```python
predictions = logger.get_predictions_by_model("yolov8m_v1.0")
```

##### `get_statistics(start_date=None, end_date=None) -> Dict`
Generate statistics about predictions.

```python
stats = logger.get_statistics()
# Returns: {
#   "total_predictions": 1000,
#   "defects_found": 150,
#   "no_defects": 850,
#   "defect_rate": 15.0,
#   "average_confidence": 0.92,
#   "defect_types": {"crack": 100, "dent": 50},
#   "storage": {
#     "total_images": 1000,
#     "defect_images": 150,
#     "no_defect_images": 850,
#     "total_size_mb": 450.5
#   }
# }
```

##### `export_predictions(output_file, defect_only=False, ...) -> int`
Export predictions to JSON file.

```python
count = logger.export_predictions(
    output_file="predictions.json",
    defect_only=True
)
```

##### `health_check() -> Dict[str, bool]`
Check service health.

```python
health = logger.health_check()
# Returns: {"database": true, "storage": true}
```

### ImageStorage Class

#### Methods

##### `save_image(...) -> str`
Save image to disk.

```python
relative_path = storage.save_image(
    image=frame,
    image_id="test_001",
    defect_detected=True,
    quality=95
)
# Returns: "2024/01/27/defects/pred_20240127_120000_abc123.jpg"
```

##### `load_image(relative_path) -> cv2.Mat`
Load image from disk.

```python
image = storage.load_image(relative_path)
```

##### `delete_image(relative_path) -> bool`
Delete image file.

##### `get_storage_stats() -> Dict`
Get storage statistics.

##### `cleanup_old_images(days_old: int) -> int`
Delete images older than specified days.

```python
deleted = storage.cleanup_old_images(days_old=30)
```

### PredictionLog Model

Database schema for prediction records.

```python
class PredictionLog(Base):
    id: int                          # Primary key
    image_id: str                    # Unique image identifier
    image_path: str                  # Path on disk
    timestamp: datetime              # Prediction time
    model_version: str               # Model version
    model_name: str                  # Model name
    confidence_score: float          # 0.0-1.0
    defect_detected: bool            # Boolean flag
    defect_type: Optional[str]       # Defect classification
    bounding_boxes: Optional[str]    # JSON string
    inference_time_ms: Optional[float]
    processing_notes: Optional[str]
```

## Examples

### Example 1: Basic Logging
```bash
python examples/example_logging_basic.py
```

### Example 2: Advanced with Bounding Boxes
```bash
python examples/example_logging_advanced.py
```

### Example 3: Pipeline Integration
```bash
python examples/example_logging_pipeline.py
```

## Directory Structure

```
prediction_images/
├── 2024/
│   ├── 01/
│   │   ├── 27/
│   │   │   ├── defects/
│   │   │   │   ├── pred_20240127_120000_abc123.jpg
│   │   │   │   ├── pred_20240127_120015_def456.jpg
│   │   │   ├── no_defects/
│   │   │   │   ├── pred_20240127_120001_ghi789.jpg
```

## Performance Considerations

### Database
- Indexed on: `image_id`, `timestamp`, `model_version`, `defect_detected`
- Connection pooling for multiple concurrent writes
- Supports batch operations for high-throughput scenarios

### Storage
- Configurable JPEG quality (default 95%)
- Automatic organization reduces filesystem load
- Cleanup mechanisms to manage disk space

### Async Support
- Future support for async database writes
- Batch processing for bulk operations

## Troubleshooting

### Database Connection Errors
```python
# Check connection
health = logger.health_check()
if not health['database']:
    # Verify database URL and credentials
    print(logger.db_connection.db_url)
```

### Image Save Failures
```python
# Ensure storage path is writable
import os
storage_path = "./prediction_images"
if not os.access(storage_path, os.W_OK):
    print("Storage path not writable")
```

### Disk Space Issues
```python
# Cleanup old images
deleted = logger.storage.cleanup_old_images(days_old=30)

# Monitor storage
stats = logger.storage.get_storage_stats()
print(f"Total size: {stats['total_size_mb']:.1f} MB")
```

## Best Practices

1. **Use Context Managers**: Ensures proper cleanup
   ```python
   with VisionLogger(config) as logger:
       logger.log_prediction(...)
   ```

2. **Batch Operations**: Log multiple predictions efficiently
   ```python
   for prediction in predictions:
       logger.log_prediction(...)
   ```

3. **Regular Cleanup**: Manage disk space
   ```python
   logger.storage.cleanup_old_images(days_old=30)
   ```

4. **Monitor Storage**: Check statistics regularly
   ```python
   stats = logger.get_statistics()
   ```

5. **Structured Configuration**: Use JSON files for production
   ```python
   config = LoggingServiceConfig.from_json_file("config.json")
   ```

## Integration with Vision Pipeline

```python
from src.utils import DetectionPipeline
from src.logging_service import VisionLogger

logger = VisionLogger(config)
pipeline = DetectionPipeline()

for frame in pipeline:
    detections = pipeline.detect(frame)
    
    # Log predictions
    logger.log_prediction(
        image=frame,
        image_id=f"frame_{timestamp}",
        confidence=max_confidence,
        defect_detected=len(detections) > 0,
        bounding_boxes=detections
    )
```

## Support

For issues or questions:
1. Check the examples in `examples/`
2. Review the API documentation above
3. Check health status with `logger.health_check()`
4. Review logs at the configured log file path
