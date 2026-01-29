"""YOLO detector implementation for real-time object detection."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import numpy as np
import torch
import cv2

# Try importing ultralytics for YOLOv8
try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False

logger = logging.getLogger(__name__)


class Detection:
    """Class representing a single detection."""
    
    def __init__(
        self,
        bbox: List[float],
        confidence: float,
        class_id: int,
        class_name: str,
        uncertain: bool = False,
    ):
        """
        Initialize detection.
        
        Args:
            bbox: Bounding box [x1, y1, x2, y2]
            confidence: Detection confidence score
            class_id: Class ID
            class_name: Class name
        """
        self.bbox = bbox
        self.confidence = confidence
        self.class_id = class_id
        self.class_name = class_name
        self.uncertain = uncertain
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert detection to dictionary."""
        return {
            'bbox': self.bbox,
            'confidence': self.confidence,
            'class_id': self.class_id,
            'class_name': self.class_name,
            'uncertain': self.uncertain,
        }


class YOLODetector:
    """YOLO-based object detector for real-time inference with GPU/CPU support.
    
    Features:
    - Automatic GPU/CPU device selection
    - Supports YOLOv5 (torch.hub) and YOLOv8 (ultralytics)
    - Real-time inference optimization
    - Configurable confidence and NMS thresholds
    
    Example:
        >>> detector = YOLODetector('yolov8n.pt', device='auto')
        >>> detections = detector.detect(frame)
    """
    
    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.5,
        nms_threshold: float = 0.4,
        device: str = "auto",
        model_type: str = "yolov8",
        half_precision: bool = False,
        uncertain_low: float = 0.4,
        uncertain_high: float = 0.7,
    ):
        """
        Initialize YOLO detector.
        
        Args:
            model_path: Path to YOLO model weights (.pt file)
            confidence_threshold: Minimum confidence for detections (0.0-1.0)
            nms_threshold: Non-maximum suppression threshold (0.0-1.0)
            device: Device to use ('auto', 'cuda', 'cpu', 'cuda:0', etc.)
            model_type: Type of YOLO model ('yolov5', 'yolov8')
            half_precision: Use FP16 for faster inference (requires GPU)
        """
        self.model_path = Path(model_path)
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.model_type = model_type.lower()
        self.half_precision = half_precision
        self.uncertain_low = uncertain_low
        self.uncertain_high = uncertain_high
        
        # Device setup
        self.device = self._setup_device(device)
        
        # Model and metadata
        self.model = None
        self.class_names = []
        self.is_loaded = False
        self.review_queue: List[Detection] = []
        
        logger.info(
            f"YOLODetector initialized: model={model_path}, "
            f"device={self.device}, conf={confidence_threshold}"
        )
    
    def _setup_device(self, device: str) -> torch.device:
        """
    
    def warmup(self, input_size: Tuple[int, int] = (640, 640), iterations: int = 3):
        """
        Warm up the model for faster initial inference.
        
        Args:
            input_size: Input image size (width, height)
            iterations: Number of warmup iterations
        """
        if not self.is_loaded:
            self.load_model()
        
        logger.info(f"Warming up model with {iterations} iterations...")
        
        # Create dummy input
        dummy_input = np.zeros((input_size[1], input_size[0], 3), dtype=np.uint8)
        
        # Run warmup iterations
        for i in range(iterations):
            _ = self.detect(dummy_input)
        
        logger.info("Model warmup complete")
    
    def get_device_info(self) -> Dict[str, Any]:
        """
        Get information about the compute device.
        
        Returns:
            Dictionary with device information
        """
        info = {
            'device': str(self.device),
            'device_type': self.device.type,
            'half_precision': self.half_precision,
        }
        
        if self.device.type == "cuda":
            info.update({
                'gpu_name': torch.cuda.get_device_name(0),
                'gpu_memory_total': f"{torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB",
                'gpu_memory_allocated': f"{torch.cuda.memory_allocated(0) / 1e9:.2f} GB",
                'gpu_memory_cached': f"{torch.cuda.memory_reserved(0) / 1e9:.2f} GB",
                'cuda_version': torch.version.cuda,
            })
        
        return info
    
    def set_confidence_threshold(self, threshold: float):
        """Update confidence threshold."""
        self.confidence_threshold = threshold
        if self.model is not None:
            self.model.conf = threshold
    
    def set_nms_threshold(self, threshold: float):
        """Update NMS threshold."""
        self.nms_threshold = threshold
        if self.model is not None:
            self.model.iou = threshold
    
    def __repr__(self) -> str:
        return (
            f"YOLODetector(model={self.model_path.name}, "
            f"device={self.device}, loaded={self.is_loaded})"
        )
        Setup compute device (GPU/CPU).
        
        Args:
            device: Device specification ('auto', 'cuda', 'cpu')
            
        Returns:
            torch.device object
        """
        if device == "auto":
            # Automatically select best available device
            if torch.cuda.is_available():
                device_obj = torch.device("cuda")
                gpu_name = torch.cuda.get_device_name(0)
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
                logger.info(
                    f"GPU available: {gpu_name} "
                    f"({gpu_memory:.1f} GB)"
                )
            elif torch.backends.mps.is_available():
                device_obj = torch.device("mps")
                logger.info("Using Apple MPS (Metal Performance Shaders)")
            else:
                device_obj = torch.device("cpu")
                logger.info("No GPU available, using CPU")
        else:
            device_obj = torch.device(device)
            logger.info(f"Using specified device: {device}")
        
        return device_obj
    
    def load_model(self):
        """Load YOLO model from disk and prepare for inference."""
        if self.is_loaded:
            logger.warning("Model already loaded")
            return
        
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        
        logger.info(f"Loading {self.model_type} model from {self.model_path}")
        
        try:
            if self.model_type == "yolov8":
                self._load_yolov8()
            elif self.model_type == "yolov5":
                self._load_yolov5()
            else:
                raise ValueError(f"Unsupported model type: {self.model_type}")
            
            self.is_loaded = True
            logger.info(
                f"Model loaded successfully on {self.device} | "
                f"Classes: {len(self.class_names)}"
            )
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def _load_yolov8(self):
        """Load YOLOv8 model using ultralytics."""
        if not ULTRALYTICS_AVAILABLE:
            raise ImportError(
                "ultralytics not installed. Install with: pip install ultralytics"
            )
        
        # Load model
        self.model = YOLO(str(self.model_path))
        
        # Move to device
        self.model.to(self.device)
        
        # Configure model
        self.model.conf = self.confidence_threshold
        self.model.iou = self.nms_threshold
        
        # Enable half precision if requested and on GPU
        if self.half_precision and self.device.type == "cuda":
            self.model.half()
            logger.info("Using FP16 (half precision) for faster inference")
        
        # Get class names
        self.class_names = self.model.names
    
    def _load_yolov5(self):
        """Load YOLOv5 model using torch.hub."""
        # Load model from torch hub or local
        if self.model_path.name.startswith("yolov5"):
            # Load from torch hub
            self.model = torch.hub.load(
                'ultralytics/yolov5',
                str(self.model_path.stem),
                pretrained=True
            )
        else:
            # Load custom model
            self.model = torch.hub.load(
                'ultralytics/yolov5',
                'custom',
                path=str(self.model_path)
            )
        
        # Move to device
        self.model.to(self.device)
        
        # Configure model
        self.model.conf = self.confidence_threshold
        self.model.iou = self.nms_threshold
        
        # Enable half precision if requested
        if self.half_precision and self.device.type == "cuda":
            self.model.half()
            logger.info("Using FP16 (half precision) for faster inference")
        
        # Set to evaluation mode
        self.model.eval()
        
        # Get class names
        self.class_names = self.model.names
    
    def detect(self, image: np.ndarray) -> List[Detection]:
        """
        Perform object detection on image.
        
        Args:
            image: Input image as numpy array (BGR format)
            
        Returns:
            List of Detection objects
        """
        if not self.is_loaded:
            self.load_model()
        
        import time as timing
        inference_start = timing.time()
        logger.debug(f"YOLO inference started | image_shape={image.shape} | dtype={image.dtype} | model={self.model_type} | device={self.device}")
        
        try:
            if self.model_type == "yolov8":
                detections = self._detect_yolov8(image)
                inference_time = (timing.time() - inference_start) * 1000
                logger.debug(f"YOLOv8 inference complete | detections={len(detections)} | time={inference_time:.2f}ms")
                return detections
            elif self.model_type == "yolov5":
                detections = self._detect_yolov5(image)
                inference_time = (timing.time() - inference_start) * 1000
                logger.debug(f"YOLOv5 inference complete | detections={len(detections)} | time={inference_time:.2f}ms")
                return detections
        except Exception as e:
            logger.error(f"Detection failed: {e}")
            return []
    
    def _detect_yolov8(self, image: np.ndarray) -> List[Detection]:
        """Detect using YOLOv8."""
        logger.debug(f"Running YOLOv8 forward pass | conf_threshold={self.confidence_threshold} | nms_threshold={self.nms_threshold}")
        # Run inference
        results = self.model(image, verbose=False)
        logger.debug(f"YOLOv8 forward pass complete | raw_results={len(results)}")
        
        detections = []
        for result in results:
            boxes = result.boxes
            logger.debug(f"Processing YOLOv8 results | num_boxes={len(boxes)}")
            
            for i in range(len(boxes)):
                # Get box coordinates
                bbox = boxes.xyxy[i].cpu().numpy().tolist()
                
                # Get confidence and class
                confidence = float(boxes.conf[i].cpu().numpy())
                class_id = int(boxes.cls[i].cpu().numpy())
                class_name = self.class_names[class_id]
                
                # Create detection object
                uncertain = self.uncertain_low <= confidence <= self.uncertain_high
                detection = Detection(
                    bbox=bbox,
                    confidence=confidence,
                    class_id=class_id,
                    class_name=class_name,
                    uncertain=uncertain,
                )
                if uncertain:
                    self.review_queue.append(detection)
                detections.append(detection)
        
        return detections
    
    def _detect_yolov5(self, image: np.ndarray) -> List[Detection]:
        """Detect using YOLOv5."""
        # Run inference
        results = self.model(image)
        
        # Parse results
        detections = []
        for *bbox, conf, cls in results.xyxy[0].cpu().numpy():
            class_id = int(cls)
            class_name = self.class_names[class_id]
            
            confidence = float(conf)
            uncertain = self.uncertain_low <= confidence <= self.uncertain_high
            detection = Detection(
                bbox=bbox,
                confidence=confidence,
                class_id=class_id,
                class_name=class_name,
                uncertain=uncertain,
            )
            if uncertain:
                self.review_queue.append(detection)
            detections.append(detection)
        
        return detections
    
    def batch_detect(self, images: List[np.ndarray]) -> List[List[Detection]]:
        """
        Perform batch detection on multiple images.
        
        Args:
            images: List of input images
            
        Returns:
            List of detection lists for each image
        """
        return [self.detect(img) for img in images]

    def pop_review_queue(self) -> List[Detection]:
        """Return and clear the queued uncertain detections."""
        queued = list(self.review_queue)
        self.review_queue.clear()
        return queued
