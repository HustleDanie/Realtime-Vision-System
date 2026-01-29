"""
Example 2: Advanced logging with bounding boxes
Demonstrates logging predictions with detection metadata.
"""

import cv2
import numpy as np
from datetime import datetime, timedelta

from src.logging_service import VisionLogger, LoggingServiceConfig


def create_image_with_objects() -> np.ndarray:
    """Create image with detected objects."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Draw background
    cv2.rectangle(img, (0, 0), (640, 480), (50, 50, 50), -1)
    
    # Draw detected objects with bounding boxes
    cv2.rectangle(img, (50, 50), (150, 150), (0, 255, 0), 2)
    cv2.putText(img, "Normal (0.98)", (55, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
    
    cv2.rectangle(img, (200, 100), (350, 250), (0, 0, 255), 2)
    cv2.putText(img, "Defect (0.92)", (205, 90), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)
    
    cv2.rectangle(img, (400, 200), (550, 350), (0, 0, 255), 2)
    cv2.putText(img, "Defect (0.87)", (405, 190), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)
    
    return img


def main():
    """Run advanced logging example."""
    
    # Initialize with custom configuration
    config = LoggingServiceConfig(
        model_version="yolov8m_v2.0",
        model_name="yolov8m_defect_detector",
    )
    
    logger = VisionLogger(config)
    
    print("=== Advanced Prediction Logging Example ===\n")
    
    # Create image with multiple detections
    image = create_image_with_objects()
    
    # Define bounding boxes detected in image
    bounding_boxes = [
        {
            "x": 50,
            "y": 50,
            "width": 100,
            "height": 100,
            "confidence": 0.98,
            "class": "normal"
        },
        {
            "x": 200,
            "y": 100,
            "width": 150,
            "height": 150,
            "confidence": 0.92,
            "class": "crack"
        },
        {
            "x": 400,
            "y": 200,
            "width": 150,
            "height": 150,
            "confidence": 0.87,
            "class": "dent"
        }
    ]
    
    # Log with multiple detections
    pred_id = logger.log_prediction(
        image=image,
        image_id="advanced_example_001",
        confidence=0.92,  # Overall confidence
        defect_detected=True,
        defect_type="mixed",  # Multiple defect types
        bounding_boxes=bounding_boxes,
        inference_time_ms=45.3,
        processing_notes="Detected multiple defects: 1 crack, 1 dent"
    )
    print(f"✓ Logged prediction with bounding boxes: {pred_id}\n")
    
    # Retrieve and display prediction details
    prediction = logger.get_prediction(pred_id)
    print("Prediction Details:")
    print(f"  Image ID: {prediction['image_id']}")
    print(f"  Timestamp: {prediction['timestamp']}")
    print(f"  Model: {prediction['model_name']} v{prediction['model_version']}")
    print(f"  Defect Detected: {prediction['defect_detected']}")
    print(f"  Defect Type: {prediction['defect_type']}")
    print(f"  Confidence: {prediction['confidence_score']:.3f}")
    print(f"  Inference Time: {prediction['inference_time_ms']:.1f}ms")
    print(f"  Image Path: {prediction['image_path']}")
    print(f"  Bounding Boxes: {prediction['bounding_boxes']}\n")
    
    # Get all defect predictions
    defect_preds = logger.get_defect_predictions(limit=10)
    print(f"Defect Predictions in Database: {len(defect_preds)}\n")
    
    # Get predictions by model version
    model_preds = logger.get_predictions_by_model("yolov8m_v2.0", limit=10)
    print(f"Predictions by Model yolov8m_v2.0: {len(model_preds)}\n")
    
    # Export predictions
    export_count = logger.export_predictions(
        output_file="./predictions_export.json",
        defect_only=True
    )
    print(f"✓ Exported {export_count} defect predictions to predictions_export.json\n")
    
    # Health check
    health = logger.health_check()
    print(f"Health Check:")
    print(f"  Database: {'✓' if health['database'] else '✗'}")
    print(f"  Storage: {'✓' if health['storage'] else '✗'}\n")
    
    logger.cleanup()
    print("✓ Example completed")


if __name__ == "__main__":
    main()
