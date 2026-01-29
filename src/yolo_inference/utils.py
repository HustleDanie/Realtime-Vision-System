"""
Utility functions for YOLO object detection pipelines.

Provides simple functions to run detection and get results in various formats.
"""

import logging
from typing import List, Dict, Tuple, Any
import numpy as np

logger = logging.getLogger(__name__)


def detect_objects(
    frame: np.ndarray,
    detector,
    return_format: str = "dict"
) -> Dict[str, Any] | Tuple[List, List, List]:
    """
    Run YOLO object detection on a preprocessed frame.
    
    This is a convenience function that takes a frame, runs detection,
    and returns results in a clean format.
    
    Args:
        frame: Preprocessed frame as numpy array (BGR or RGB)
        detector: YOLODetector instance (must be loaded)
        return_format: Format of return value:
            - "dict": Return dictionary with 'boxes', 'classes', 'confidences'
            - "tuple": Return tuple of (boxes, classes, confidences)
            - "detections": Return list of Detection objects
    
    Returns:
        Detection results in specified format:
        
        dict format:
            {
                'boxes': [[x1, y1, x2, y2], ...],
                'classes': ['person', 'car', ...],
                'confidences': [0.95, 0.87, ...],
                'num_detections': 2
            }
        
        tuple format:
            (boxes, classes, confidences) where:
            - boxes: List of [x1, y1, x2, y2] coordinates
            - classes: List of class names
            - confidences: List of confidence scores
        
        detections format:
            List of Detection objects
    
    Example:
        >>> from src.yolo_inference import YOLODetector
        >>> from src.yolo_inference.utils import detect_objects
        >>> 
        >>> detector = YOLODetector("yolov8n.pt", device="auto")
        >>> detector.load_model()
        >>> 
        >>> # Process frame
        >>> results = detect_objects(frame, detector, return_format="dict")
        >>> print(f"Found {results['num_detections']} objects")
        >>> 
        >>> for bbox, cls, conf in zip(results['boxes'], 
        ...                             results['classes'], 
        ...                             results['confidences']):
        ...     print(f"{cls}: {conf:.2f} at {bbox}")
    """
    # Run detection
    detections = detector.detect(frame)
    
    if return_format == "detections":
        return detections
    
    # Extract data from detections
    boxes = [det.bbox for det in detections]
    classes = [det.class_name for det in detections]
    confidences = [det.confidence for det in detections]
    
    if return_format == "dict":
        return {
            'boxes': boxes,
            'classes': classes,
            'confidences': confidences,
            'num_detections': len(detections)
        }
    elif return_format == "tuple":
        return boxes, classes, confidences
    else:
        raise ValueError(f"Unknown return_format: {return_format}")


def detect_and_filter(
    frame: np.ndarray,
    detector,
    min_confidence: float = 0.5,
    allowed_classes: List[str] = None,
    max_detections: int = None
) -> Dict[str, Any]:
    """
    Run detection with filtering options.
    
    Args:
        frame: Input frame
        detector: YOLODetector instance
        min_confidence: Minimum confidence threshold
        allowed_classes: List of allowed class names (None = all classes)
        max_detections: Maximum number of detections to return (None = all)
    
    Returns:
        Dictionary with filtered detection results
    
    Example:
        >>> # Only detect persons and cars with high confidence
        >>> results = detect_and_filter(
        ...     frame, 
        ...     detector,
        ...     min_confidence=0.7,
        ...     allowed_classes=['person', 'car'],
        ...     max_detections=10
        ... )
    """
    # Run detection
    detections = detector.detect(frame)
    
    # Filter by confidence
    filtered = [d for d in detections if d.confidence >= min_confidence]
    
    # Filter by class
    if allowed_classes is not None:
        filtered = [d for d in filtered if d.class_name in allowed_classes]
    
    # Sort by confidence (highest first)
    filtered.sort(key=lambda x: x.confidence, reverse=True)
    
    # Limit number of detections
    if max_detections is not None:
        filtered = filtered[:max_detections]
    
    # Convert to dict format
    return {
        'boxes': [d.bbox for d in filtered],
        'classes': [d.class_name for d in filtered],
        'confidences': [d.confidence for d in filtered],
        'class_ids': [d.class_id for d in filtered],
        'num_detections': len(filtered)
    }


def get_detections_by_class(
    frame: np.ndarray,
    detector,
    group_by_class: bool = True
) -> Dict[str, List[Dict]]:
    """
    Run detection and group results by class.
    
    Args:
        frame: Input frame
        detector: YOLODetector instance
        group_by_class: If True, group detections by class name
    
    Returns:
        Dictionary mapping class names to lists of detections
    
    Example:
        >>> results = get_detections_by_class(frame, detector)
        >>> print(f"Found {len(results['person'])} persons")
        >>> print(f"Found {len(results['car'])} cars")
    """
    # Run detection
    detections = detector.detect(frame)
    
    if not group_by_class:
        return {'all': [d.to_dict() for d in detections]}
    
    # Group by class
    grouped = {}
    for det in detections:
        class_name = det.class_name
        if class_name not in grouped:
            grouped[class_name] = []
        
        grouped[class_name].append({
            'bbox': det.bbox,
            'confidence': det.confidence,
            'class_id': det.class_id
        })
    
    return grouped


def batch_detect(
    frames: List[np.ndarray],
    detector,
    show_progress: bool = False
) -> List[Dict[str, Any]]:
    """
    Run detection on multiple frames.
    
    Args:
        frames: List of input frames
        detector: YOLODetector instance
        show_progress: Show progress bar (requires tqdm)
    
    Returns:
        List of detection results for each frame
    
    Example:
        >>> frames = [frame1, frame2, frame3]
        >>> results = batch_detect(frames, detector)
        >>> for i, result in enumerate(results):
        ...     print(f"Frame {i}: {result['num_detections']} objects")
    """
    results = []
    
    if show_progress:
        try:
            from tqdm import tqdm
            frames = tqdm(frames, desc="Detecting")
        except ImportError:
            logger.warning("tqdm not installed, progress bar disabled")
    
    for frame in frames:
        result = detect_objects(frame, detector, return_format="dict")
        results.append(result)
    
    return results


def stream_detect(
    frame_generator,
    detector,
    callback=None,
    max_frames: int = None
):
    """
    Run detection on a stream of frames (generator).
    
    Args:
        frame_generator: Generator yielding frames
        detector: YOLODetector instance
        callback: Optional callback function(frame, results)
        max_frames: Maximum number of frames to process
    
    Yields:
        Tuple of (frame, detection_results)
    
    Example:
        >>> from src.video_streaming import Camera
        >>> 
        >>> camera = Camera(source=0)
        >>> 
        >>> for frame, results in stream_detect(camera.stream(), detector):
        ...     print(f"Detected {results['num_detections']} objects")
        ...     if results['num_detections'] > 0:
        ...         print(f"Classes: {results['classes']}")
    """
    frame_count = 0
    
    for frame in frame_generator:
        # Run detection
        results = detect_objects(frame, detector, return_format="dict")
        
        # Call callback if provided
        if callback is not None:
            callback(frame, results)
        
        yield frame, results
        
        # Check frame limit
        frame_count += 1
        if max_frames is not None and frame_count >= max_frames:
            break


def compute_iou(box1: List[float], box2: List[float]) -> float:
    """
    Compute Intersection over Union (IoU) between two bounding boxes.
    
    Args:
        box1: [x1, y1, x2, y2]
        box2: [x1, y1, x2, y2]
    
    Returns:
        IoU score (0.0 - 1.0)
    """
    # Get coordinates
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2
    
    # Calculate intersection area
    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2)
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)
    
    if x2_i < x1_i or y2_i < y1_i:
        return 0.0
    
    intersection = (x2_i - x1_i) * (y2_i - y1_i)
    
    # Calculate union area
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    union = area1 + area2 - intersection
    
    return intersection / union if union > 0 else 0.0


def filter_overlapping_boxes(
    boxes: List[List[float]],
    classes: List[str],
    confidences: List[float],
    iou_threshold: float = 0.5
) -> Tuple[List, List, List]:
    """
    Filter overlapping bounding boxes using NMS-like logic.
    
    Args:
        boxes: List of bounding boxes
        classes: List of class names
        confidences: List of confidence scores
        iou_threshold: IoU threshold for filtering
    
    Returns:
        Filtered (boxes, classes, confidences)
    """
    if len(boxes) == 0:
        return [], [], []
    
    # Sort by confidence (descending)
    indices = sorted(range(len(confidences)), 
                    key=lambda i: confidences[i], 
                    reverse=True)
    
    keep = []
    
    for i in indices:
        # Check if this box overlaps with any kept box
        should_keep = True
        for j in keep:
            if classes[i] == classes[j]:  # Only compare same class
                iou = compute_iou(boxes[i], boxes[j])
                if iou > iou_threshold:
                    should_keep = False
                    break
        
        if should_keep:
            keep.append(i)
    
    # Return filtered results
    filtered_boxes = [boxes[i] for i in keep]
    filtered_classes = [classes[i] for i in keep]
    filtered_confidences = [confidences[i] for i in keep]
    
    return filtered_boxes, filtered_classes, filtered_confidences


def get_detection_summary(results: Dict[str, Any]) -> str:
    """
    Generate a text summary of detection results.
    
    Args:
        results: Detection results dictionary
    
    Returns:
        Formatted summary string
    
    Example:
        >>> results = detect_objects(frame, detector)
        >>> print(get_detection_summary(results))
        Detection Summary:
        - Total: 3 objects
        - person: 2 (conf: 0.95, 0.87)
        - car: 1 (conf: 0.92)
    """
    if results['num_detections'] == 0:
        return "No objects detected"
    
    # Count by class
    class_counts = {}
    class_confidences = {}
    
    for cls, conf in zip(results['classes'], results['confidences']):
        if cls not in class_counts:
            class_counts[cls] = 0
            class_confidences[cls] = []
        class_counts[cls] += 1
        class_confidences[cls].append(conf)
    
    # Build summary
    lines = [f"Detection Summary:"]
    lines.append(f"- Total: {results['num_detections']} objects")
    
    for cls, count in sorted(class_counts.items()):
        confs = class_confidences[cls]
        conf_str = ", ".join([f"{c:.2f}" for c in confs])
        lines.append(f"- {cls}: {count} (conf: {conf_str})")
    
    return "\n".join(lines)
