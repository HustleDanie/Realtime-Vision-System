"""
Prediction router for running defect detection inference on uploaded images.
"""
import os
import uuid
import base64
from io import BytesIO
from datetime import datetime
from typing import Optional, List

import numpy as np
from PIL import Image
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.monitoring_api.db import get_db
from src.monitoring_api import crud


router = APIRouter(prefix="/predict", tags=["prediction"])


class PredictionResult(BaseModel):
    image_id: str
    defect_detected: bool
    confidence_score: float
    defect_type: Optional[str] = None
    bounding_boxes: Optional[List[dict]] = None
    inference_time_ms: float
    timestamp: datetime
    annotated_image: Optional[str] = None  # Base64 encoded image with annotations


class PredictionRequest(BaseModel):
    image_base64: str
    filename: Optional[str] = None


# Try to import YOLO detector, fallback to mock if not available
try:
    from src.yolo_inference.detector import YOLODetector
    DETECTOR_AVAILABLE = True
except ImportError:
    DETECTOR_AVAILABLE = False
    print("Warning: YOLO detector not available, using mock predictions")


# Initialize detector (lazy loading)
_detector = None


def get_detector():
    global _detector
    if _detector is None and DETECTOR_AVAILABLE:
        try:
            _detector = YOLODetector()
        except Exception as e:
            print(f"Failed to initialize YOLO detector: {e}")
    return _detector


def mock_prediction(image: np.ndarray) -> dict:
    """Generate mock prediction for testing when detector is not available."""
    import random
    import time
    
    start_time = time.time()
    
    # Simulate processing time
    time.sleep(0.1 + random.random() * 0.2)
    
    # Random detection result
    defect_detected = random.random() > 0.6
    confidence = random.uniform(0.7, 0.99) if defect_detected else random.uniform(0.85, 0.99)
    
    defect_types = ["scratch", "dent", "crack", "stain", "chip", "discoloration"]
    defect_type = random.choice(defect_types) if defect_detected else None
    
    bounding_boxes = []
    if defect_detected:
        h, w = image.shape[:2]
        # Generate random bounding box
        x1 = random.randint(0, w // 2)
        y1 = random.randint(0, h // 2)
        x2 = random.randint(x1 + 50, min(x1 + 200, w))
        y2 = random.randint(y1 + 50, min(y1 + 200, h))
        bounding_boxes.append({
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "confidence": confidence,
            "label": defect_type
        })
    
    inference_time = (time.time() - start_time) * 1000
    
    return {
        "defect_detected": defect_detected,
        "confidence_score": confidence,
        "defect_type": defect_type,
        "bounding_boxes": bounding_boxes,
        "inference_time_ms": inference_time
    }


def run_inference(image: np.ndarray) -> dict:
    """Run inference using YOLO detector or mock."""
    detector = get_detector()
    
    if detector is not None:
        try:
            detections = detector.detect(image)
            
            defect_detected = len(detections) > 0
            confidence = max([d.get('confidence', 0) for d in detections]) if detections else 0.95
            defect_type = detections[0].get('label') if detections else None
            
            bounding_boxes = []
            for det in detections:
                bounding_boxes.append({
                    "x1": det.get('x1', 0),
                    "y1": det.get('y1', 0),
                    "x2": det.get('x2', 0),
                    "y2": det.get('y2', 0),
                    "confidence": det.get('confidence', 0),
                    "label": det.get('label', 'defect')
                })
            
            return {
                "defect_detected": defect_detected,
                "confidence_score": confidence,
                "defect_type": defect_type,
                "bounding_boxes": bounding_boxes,
                "inference_time_ms": det.get('inference_time_ms', 0) if detections else 0
            }
        except Exception as e:
            print(f"Detector error: {e}, falling back to mock")
    
    return mock_prediction(image)


def draw_annotations(image: np.ndarray, bounding_boxes: List[dict]) -> np.ndarray:
    """Draw bounding boxes on the image."""
    import cv2
    
    annotated = image.copy()
    
    for box in bounding_boxes:
        x1, y1, x2, y2 = int(box['x1']), int(box['y1']), int(box['x2']), int(box['y2'])
        confidence = box.get('confidence', 0)
        label = box.get('label', 'defect')
        
        # Draw rectangle
        color = (0, 0, 255)  # Red for defects
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        
        # Draw label
        label_text = f"{label}: {confidence:.2f}"
        cv2.putText(annotated, label_text, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    return annotated


def image_to_base64(image: np.ndarray) -> str:
    """Convert numpy array to base64 encoded JPEG."""
    import cv2
    
    # Convert BGR to RGB if needed
    if len(image.shape) == 3 and image.shape[2] == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    pil_image = Image.fromarray(image)
    buffer = BytesIO()
    pil_image.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


@router.post("/upload", response_model=PredictionResult)
async def predict_from_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Run defect detection on an uploaded image file.
    
    Accepts: JPEG, PNG, WebP images
    Returns: Prediction results with optional annotated image
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    try:
        # Read and decode image
        contents = await file.read()
        image = Image.open(BytesIO(contents))
        image_np = np.array(image)
        
        # Convert RGBA to RGB if needed
        if len(image_np.shape) == 3 and image_np.shape[2] == 4:
            image_np = image_np[:, :, :3]
        
        # Run inference
        result = run_inference(image_np)
        
        # Generate image ID
        image_id = f"IMG_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        # Draw annotations if defects detected
        annotated_base64 = None
        if result['bounding_boxes']:
            try:
                import cv2
                annotated = draw_annotations(image_np, result['bounding_boxes'])
                annotated_base64 = image_to_base64(annotated)
            except ImportError:
                pass  # cv2 not available
        
        # Save to database
        try:
            import json
            crud.create_inspection_log(
                db=db,
                image_id=image_id,
                image_path=file.filename or "uploaded_image",
                model_version="v1.0",
                model_name="yolo_defect_detector",
                confidence_score=result['confidence_score'],
                defect_detected=result['defect_detected'],
                defect_type=result['defect_type'],
                bounding_boxes=json.dumps(result['bounding_boxes']) if result['bounding_boxes'] else None,
                inference_time_ms=result['inference_time_ms'],
                processing_notes="Uploaded via web interface"
            )
        except Exception as e:
            print(f"Failed to save to database: {e}")
        
        return PredictionResult(
            image_id=image_id,
            defect_detected=result['defect_detected'],
            confidence_score=result['confidence_score'],
            defect_type=result['defect_type'],
            bounding_boxes=result['bounding_boxes'],
            inference_time_ms=result['inference_time_ms'],
            timestamp=datetime.now(),
            annotated_image=annotated_base64
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process image: {str(e)}")


@router.post("/base64", response_model=PredictionResult)
async def predict_from_base64(
    request: PredictionRequest,
    db: Session = Depends(get_db)
):
    """
    Run defect detection on a base64 encoded image.
    
    Useful for camera captures from the frontend.
    """
    try:
        # Decode base64 image
        image_data = request.image_base64
        
        # Remove data URL prefix if present
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes))
        image_np = np.array(image)
        
        # Convert RGBA to RGB if needed
        if len(image_np.shape) == 3 and image_np.shape[2] == 4:
            image_np = image_np[:, :, :3]
        
        # Run inference
        result = run_inference(image_np)
        
        # Generate image ID
        image_id = f"CAM_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        # Draw annotations if defects detected
        annotated_base64 = None
        if result['bounding_boxes']:
            try:
                import cv2
                annotated = draw_annotations(image_np, result['bounding_boxes'])
                annotated_base64 = image_to_base64(annotated)
            except ImportError:
                pass
        
        # Save to database
        try:
            import json
            crud.create_inspection_log(
                db=db,
                image_id=image_id,
                image_path=request.filename or "camera_capture",
                model_version="v1.0",
                model_name="yolo_defect_detector",
                confidence_score=result['confidence_score'],
                defect_detected=result['defect_detected'],
                defect_type=result['defect_type'],
                bounding_boxes=json.dumps(result['bounding_boxes']) if result['bounding_boxes'] else None,
                inference_time_ms=result['inference_time_ms'],
                processing_notes="Captured via camera"
            )
        except Exception as e:
            print(f"Failed to save to database: {e}")
        
        return PredictionResult(
            image_id=image_id,
            defect_detected=result['defect_detected'],
            confidence_score=result['confidence_score'],
            defect_type=result['defect_type'],
            bounding_boxes=result['bounding_boxes'],
            inference_time_ms=result['inference_time_ms'],
            timestamp=datetime.now(),
            annotated_image=annotated_base64
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process image: {str(e)}")


@router.get("/status")
async def get_prediction_status():
    """Check if the prediction service is available."""
    detector = get_detector()
    return {
        "status": "ok",
        "detector_available": detector is not None,
        "mock_mode": detector is None,
        "supported_formats": ["jpeg", "png", "webp"]
    }
