"""
Example 1: Basic prediction logging
Demonstrates simple usage of VisionLogger to log predictions.
"""

import cv2
import numpy as np
from pathlib import Path
from datetime import datetime

from src.logging_service import VisionLogger, LoggingServiceConfig


def create_sample_image() -> np.ndarray:
    """Create a sample image for demonstration."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.rectangle(img, (100, 100), (300, 300), (0, 255, 0), 2)
    cv2.putText(img, "Sample Prediction", (150, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    return img


def main():
    """Run basic logging example."""
    
    # Initialize logging service
    config = LoggingServiceConfig(
        model_version="yolov8m_v1.0",
        model_name="yolov8m",
    )
    
    logger = VisionLogger(config)
    
    print("=== Basic Prediction Logging Example ===\n")
    
    # Create sample image
    image = create_sample_image()
    
    # Log a defect prediction
    defect_pred_id = logger.log_prediction(
        image=image,
        image_id="test_defect_001",
        confidence=0.95,
        defect_detected=True,
        defect_type="crack",
        inference_time_ms=42.5,
        processing_notes="Detected small crack in upper region"
    )
    print(f"✓ Logged defect prediction with ID: {defect_pred_id}\n")
    
    # Log a no-defect prediction
    no_defect_pred_id = logger.log_prediction(
        image=image,
        image_id="test_no_defect_001",
        confidence=0.98,
        defect_detected=False,
        inference_time_ms=40.2,
        processing_notes="No defects detected"
    )
    print(f"✓ Logged no-defect prediction with ID: {no_defect_pred_id}\n")
    
    # Retrieve predictions
    pred1 = logger.get_prediction(defect_pred_id)
    print(f"Retrieved defect prediction:\n{pred1}\n")
    
    pred2 = logger.get_prediction(no_defect_pred_id)
    print(f"Retrieved no-defect prediction:\n{pred2}\n")
    
    # Get statistics
    stats = logger.get_statistics()
    print(f"Predictions Statistics:")
    print(f"  Total: {stats['total_predictions']}")
    print(f"  Defects: {stats['defects_found']}")
    print(f"  No Defects: {stats['no_defects']}")
    print(f"  Defect Rate: {stats['defect_rate']:.1f}%")
    print(f"  Avg Confidence: {stats['average_confidence']:.3f}\n")
    
    # Cleanup
    logger.cleanup()
    print("✓ Cleanup completed")


if __name__ == "__main__":
    main()
