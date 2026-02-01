"""Visualization utilities for detections and results."""

import logging
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import cv2
import random

logger = logging.getLogger(__name__)

class Visualizer:
    """Handles visualization of detections and results with advanced features.
    
    This class provides high-level visualization methods with class-specific
    color management and batch processing capabilities.
    
    Example:
        >>> visualizer = Visualizer()
        >>> result = visualizer.draw_detections(image, detections)
    """
    
    def __init__(
        self,
        class_colors: Optional[Dict[int, Tuple[int, int, int]]] = None,
        class_names: Optional[Dict[int, str]] = None,
        default_color: Tuple[int, int, int] = (0, 255, 0)
    ):
        """
        Initialize visualizer.
        
        Args:
            class_colors: Dictionary mapping class IDs to BGR colors
            class_names: Dictionary mapping class IDs to names
            default_color: Default color for classes without specific color
        """
        self.class_colors = class_colors or {}
        self.class_names = class_names or {}
        self.default_color = default_color
        logger.info("Visualizer initialized")
    
    def draw_bbox(
        self,
        image: np.ndarray,
        bbox: List[float],
        label: str,
        confidence: float,
        color: Optional[Tuple[int, int, int]] = None,
        thickness: int = 2
    ) -> np.ndarray:
        """
        Draw a single bounding box on image.
        
        Args:
            image: Input image
            bbox: Bounding box [x1, y1, x2, y2]
            label: Class label
            confidence: Detection confidence
            color: BGR color (uses default if None)
            thickness: Line thickness
            
        Returns:
            Image with drawn bounding box
        """
        if color is None:
            color = self.default_color
        
        x1, y1, x2, y2 = map(int, bbox)
        
        # Draw rectangle
        cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)
        
        # Draw label
        label_text = f"{label} {confidence:.2f}"
        (text_width, text_height), _ = cv2.getTextSize(
            label_text,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            2
        )
        
        # Label background
        cv2.rectangle(
            image,
            (x1, y1 - text_height - 10),
            (x1 + text_width + 10, y1),
            color,
            -1
        )
        
        # Label text
        cv2.putText(
            image,
            label_text,
            (x1 + 5, y1 - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )
        
        return image
    
    def draw_detections(
        self,
        image: np.ndarray,
        detections: List,
        thickness: int = 2
    ) -> np.ndarray:
        """
        Draw all detections on image.
        
        Args:
            image: Input image
            detections: List of Detection objects
            thickness: Line thickness
            
        Returns:
            Image with all detections drawn
        """
        result = image.copy()
        
        for detection in detections:
            # Get color for this class
            color = self.class_colors.get(detection.class_id, self.default_color)
            
            # Draw the detection
            result = self.draw_bbox(
                result,
                detection.bbox,
                detection.class_name,
                detection.confidence,
                color,
                thickness
            )
        
        return result
    
    def draw_from_results(
        self,
        image: np.ndarray,
        results: Dict[str, Any],
        class_id_map: Optional[Dict[str, int]] = None
    ) -> np.ndarray:
        """
        Draw detections from results dictionary.
        
        Args:
            image: Input image
            results: Detection results dict with 'boxes', 'classes', 'confidences'
            class_id_map: Optional mapping from class names to IDs
        
        Returns:
            Image with drawn detections
        
        Example:
            >>> results = detect_objects(frame, detector)
            >>> visualized = visualizer.draw_from_results(frame, results)
        """
        boxes = results.get('boxes', [])
        classes = results.get('classes', [])
        confidences = results.get('confidences', [])
        
        if len(boxes) == 0:
            return image
        
        # Get colors
        colors = []
        for cls in classes:
            if class_id_map and cls in class_id_map:
                class_id = class_id_map[cls]
                color = self.class_colors.get(class_id, self.default_color)
            else:
                color = self.default_color
            colors.append(color)
        
        # Use the draw_bounding_boxes function
        return draw_bounding_boxes(
            image,
            boxes,
            classes,
            confidences,
            colors
        )
    
    def create_grid(
        self,
        images: List[np.ndarray],
        grid_size: Optional[Tuple[int, int]] = None,
        border_size: int = 2,
        border_color: Tuple[int, int, int] = (255, 255, 255)
    ) -> np.ndarray:
        """
        Create a grid of images.
        
        Args:
            images: List of images (all must be same size)
            grid_size: Optional (rows, cols). Auto-calculated if None
            border_size: Border width between images
            border_color: Border color (BGR)
            
        Returns:
            Grid image
        """
        if len(images) == 0:
            return np.zeros((640, 640, 3), dtype=np.uint8)
        
        # Calculate grid size if not provided
        if grid_size is None:
            num_images = len(images)
            cols = int(np.ceil(np.sqrt(num_images)))
            rows = int(np.ceil(num_images / cols))
            grid_size = (rows, cols)
        
        rows, cols = grid_size
        
        # Get image dimensions
        h, w = images[0].shape[:2]
        
        # Create grid with borders
        grid_h = rows * h + (rows - 1) * border_size
        grid_w = cols * w + (cols - 1) * border_size
        
        if len(images[0].shape) == 3:
            grid = np.full((grid_h, grid_w, 3), border_color, dtype=np.uint8)
        else:
            grid = np.full((grid_h, grid_w), border_color[0], dtype=np.uint8)
        
        # Place images in grid
        for idx, img in enumerate(images):
            if idx >= rows * cols:
                break
            
            row = idx // cols
            col = idx % cols
            
            y = row * (h + border_size)
            x = col * (w + border_size)
            
            grid[y:y+h, x:x+w] = img
        
        return grid


def draw_bounding_boxes(
    image: np.ndarray,
    boxes: List[List[float]],
    labels: List[str],
    confidences: List[float],
    colors: Optional[List[Tuple[int, int, int]]] = None,
    thickness: int = 2,
    font_scale: float = 0.5,
    font_thickness: int = 2,
    show_confidence: bool = True,
    alpha: float = 0.8
) -> np.ndarray:
    """
    Draw multiple bounding boxes on an image.
    
    Args:
        image: Input image (BGR format)
        boxes: List of bounding boxes [[x1, y1, x2, y2], ...]
        labels: List of class labels
        confidences: List of confidence scores
        colors: Optional list of BGR colors for each box
        thickness: Line thickness
        font_scale: Font size scale
        font_thickness: Font thickness
        show_confidence: Whether to show confidence in label
        alpha: Transparency for label background
        
    Returns:
        Image with drawn bounding boxes
        
    Example:
        >>> boxes = [[100, 100, 200, 200], [300, 300, 400, 400]]
        >>> labels = ['person', 'car']
        >>> confidences = [0.95, 0.87]
        >>> result = draw_bounding_boxes(image, boxes, labels, confidences)
    """
    result = image.copy()
    
    if colors is None:
        colors = [(0, 255, 0)] * len(boxes)
    
    for i, (box, label, conf, color) in enumerate(zip(boxes, labels, confidences, colors)):
        x1, y1, x2, y2 = map(int, box)
        
        # Draw bounding box
        cv2.rectangle(result, (x1, y1), (x2, y2), color, thickness)
        
        # Create label text
        if show_confidence:
            label_text = f"{label} {conf:.2f}"
        else:
            label_text = label
        
        # Get text size for background rectangle
        (text_width, text_height), baseline = cv2.getTextSize(
            label_text,
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            font_thickness
        )
        
        # Draw filled rectangle for label background
        label_y = y1 - text_height - 10 if y1 - text_height - 10 > 0 else y1 + text_height + 10
        
        if alpha < 1.0:
            # Semi-transparent background
            overlay = result.copy()
            cv2.rectangle(
                overlay,
                (x1, label_y - text_height - 5),
                (x1 + text_width + 10, label_y + 5),
                color,
                -1
            )
            cv2.addWeighted(overlay, alpha, result, 1 - alpha, 0, result)
        else:
            # Solid background
            cv2.rectangle(
                result,
                (x1, label_y - text_height - 5),
                (x1 + text_width + 10, label_y + 5),
                color,
                -1
            )
        
        # Draw label text
        cv2.putText(
            result,
            label_text,
            (x1 + 5, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (255, 255, 255),  # White text
            font_thickness,
            cv2.LINE_AA
        )
    
    return result


def draw_detection_info(
    image: np.ndarray,
    info_text: List[str],
    position: Tuple[int, int] = (10, 30),
    font_scale: float = 0.7,
    color: Tuple[int, int, int] = (0, 255, 0),
    background: bool = True,
    background_alpha: float = 0.6
) -> np.ndarray:
    """
    Draw information text on image (e.g., FPS, object counts).
    
    Args:
        image: Input image
        info_text: List of text lines to draw
        position: Starting (x, y) position
        font_scale: Font size scale
        color: Text color (BGR)
        background: Whether to draw background rectangle
        background_alpha: Background transparency
    
    Returns:
        Image with drawn text
    
    Example:
        >>> info = ['FPS: 30.5', 'Objects: 5', 'Device: GPU']
        >>> result = draw_detection_info(image, info)
    """
    result = image.copy()
    x, y = position
    line_height = int(35 * font_scale)
    
    if background:
        # Calculate background size
        max_width = 0
        for text in info_text:
            (text_width, _), _ = cv2.getTextSize(
                text,
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                2
            )
            max_width = max(max_width, text_width)
        
        # Draw semi-transparent background
        overlay = result.copy()
        cv2.rectangle(
            overlay,
            (x - 5, y - 25),
            (x + max_width + 10, y + line_height * len(info_text) + 5),
            (0, 0, 0),
            -1
        )
        cv2.addWeighted(overlay, background_alpha, result, 1 - background_alpha, 0, result)
    
    # Draw text lines
    for i, text in enumerate(info_text):
        y_pos = y + i * line_height
        cv2.putText(
            result,
            text,
            (x, y_pos),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            color,
            2,
            cv2.LINE_AA
        )
    
    return result


def create_color_palette(num_classes: int, colormap: str = "hsv") -> List[Tuple[int, int, int]]:
    """
    Generate distinct colors for different classes.
    
    Args:
        num_classes: Number of classes
        colormap: Color scheme ('hsv', 'rainbow', 'random')
    
    Returns:
        List of BGR colors
    
    Example:
        >>> colors = create_color_palette(80)  # For COCO classes
    """
    colors = []
    
    if colormap == "hsv":
        for i in range(num_classes):
            hue = int(180 * i / num_classes)
            hsv = np.uint8([[[hue, 255, 255]]])
            bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0][0]
            colors.append(tuple(map(int, bgr)))
    
    elif colormap == "rainbow":
        for i in range(num_classes):
            hue = int(180 * i / num_classes)
            hsv = np.uint8([[[hue, 200, 255]]])
            bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0][0]
            colors.append(tuple(map(int, bgr)))
    
    elif colormap == "random":
        random.seed(42)  # For reproducibility
        for _ in range(num_classes):
            color = (
                random.randint(50, 255),
                random.randint(50, 255),
                random.randint(50, 255)
            )
            colors.append(color)
    
    return colors


class Visualizer:
    """Handles visualization of detections and results."""
    
    def __init__(self, class_colors: Optional[dict] = None):
        """
        Initialize visualizer.
        
        Args:
            class_colors: Dictionary mapping class IDs to RGB colors
        """
        self.class_colors = class_colors or {}
        logger.info("Visualizer initialized")
    
    def draw_bbox(self, image: np.ndarray, bbox: List[float], 
                  label: str, confidence: float, 
                  color: Tuple[int, int, int] = (0, 255, 0)) -> np.ndarray:
        """
        Draw bounding box on image.
        
        Args:
            image: Input image
            bbox: Bounding box [x1, y1, x2, y2]
            label: Class label
            confidence: Detection confidence
            color: RGB color for bbox
            
        Returns:
            Image with drawn bounding box
        """
        # Placeholder: would use cv2.rectangle and cv2.putText
        logger.debug(f"Drawing bbox for {label} with confidence {confidence:.2f}")
        return image
    
    def draw_detections(self, image: np.ndarray, detections: List) -> np.ndarray:
        """
        Draw all detections on image.
        
        Args:
            image: Input image
            detections: List of Detection objects
            
        Returns:
            Image with all detections drawn
        """
        result = image.copy()
        for detection in detections:
            color = self.class_colors.get(detection.class_id, (0, 255, 0))
            result = self.draw_bbox(
                result, 
                detection.bbox, 
                detection.class_name,
                detection.confidence,
                color
            )
        return result
    
    def create_grid(self, images: List[np.ndarray], 
                    grid_size: Optional[Tuple[int, int]] = None) -> np.ndarray:
        """
        Create a grid of images.
        
        Args:
            images: List of images
            grid_size: Optional (rows, cols) for grid
            
        Returns:
            Grid image
        """
        # Placeholder implementation
        logger.debug(f"Creating grid with {len(images)} images")
        return np.zeros((640, 640, 3), dtype=np.uint8)
