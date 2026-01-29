"""
Example 3: Integration with real-time detection pipeline
Demonstrates logging predictions from the detection pipeline.
"""

import cv2
import numpy as np
from datetime import datetime
from pathlib import Path

from src.logging_service import VisionLogger, LoggingServiceConfig
from src.video_streaming import CameraStream
from src.preprocessing import ImageProcessor
from src.yolo_inference import YOLODetector
from src.utils import draw_bounding_boxes


def main():
    """Run pipeline integration example."""
    
    # Setup logging service
    config = LoggingServiceConfig(
        model_version="yolov8n_v1.0",
        model_name="yolov8n",
    )
    
    logger = VisionLogger(config)
    
    print("=== Real-Time Detection Pipeline with Logging ===\n")
    
    # Initialize pipeline components
    print("Initializing components...")
    camera = CameraStream(source=0, fps=30)
    preprocessor = ImageProcessor(target_size=(640, 480))
    detector = YOLODetector(model_name="yolov8n", device="cpu")
    
    print("✓ Components initialized\n")
    
    # Process a few frames
    frame_count = 0
    max_frames = 5
    
    try:
        for original_frame in camera:
            if frame_count >= max_frames:
                break
            
            # Preprocess
            preprocessed, _ = preprocessor.process(original_frame)
            
            # Detect
            detections = detector.detect(preprocessed)
            
            # Extract information
            has_detections = len(detections) > 0
            confidence = max([d['confidence'] for d in detections]) if has_detections else 0.0
            
            # Draw detections on original frame
            annotated_frame = draw_bounding_boxes(
                original_frame,
                detections,
                draw_confidence=True
            )
            
            # Create bounding box metadata
            bboxes = [
                {
                    "x": d['bbox'][0],
                    "y": d['bbox'][1],
                    "width": d['bbox'][2],
                    "height": d['bbox'][3],
                    "confidence": d['confidence'],
                    "class": d['class_name']
                }
                for d in detections
            ]
            
            # Log prediction
            image_id = f"pipeline_frame_{frame_count:04d}"
            
            pred_id = logger.log_prediction(
                image=annotated_frame,
                image_id=image_id,
                confidence=confidence,
                defect_detected=has_detections,
                defect_type=detections[0]['class_name'] if has_detections else None,
                bounding_boxes=bboxes if bboxes else None,
                inference_time_ms=detector.last_inference_time,
                processing_notes=f"Detected {len(detections)} objects"
            )
            
            print(f"Frame {frame_count}: "
                  f"Objects={len(detections)}, "
                  f"Confidence={confidence:.3f}, "
                  f"Log ID={pred_id}")
            
            frame_count += 1
    
    except Exception as e:
        print(f"Error during processing: {e}")
    
    finally:
        camera.release()
    
    print(f"\n✓ Processed {frame_count} frames\n")
    
    # Display statistics
    stats = logger.get_statistics()
    print("Statistics:")
    print(f"  Total Predictions: {stats['total_predictions']}")
    print(f"  Objects Detected: {stats['defects_found']}")
    print(f"  Empty Frames: {stats['no_defects']}")
    print(f"  Detection Rate: {stats['defect_rate']:.1f}%")
    print(f"  Average Confidence: {stats['average_confidence']:.3f}")
    print(f"  Storage: {stats['storage']['total_images']} images, "
          f"{stats['storage']['total_size_mb']:.1f} MB\n")
    
    logger.cleanup()
    print("✓ Pipeline integration example completed")


if __name__ == "__main__":
    main()
