"""Image transformation classes for preprocessing."""

import logging
from abc import ABC, abstractmethod
from typing import Tuple, Optional
import numpy as np
import cv2

logger = logging.getLogger(__name__)


class Transform(ABC):
    """Base class for image transformations."""
    
    @abstractmethod
    def apply(self, image: np.ndarray) -> np.ndarray:
        """
        Apply transformation to image.
        
        Args:
            image: Input image
            
        Returns:
            Transformed image
        """
        pass


class ResizeTransform(Transform):
    """Resize image to target dimensions."""
    
    def __init__(
        self,
        target_size: Tuple[int, int],
        interpolation: int = cv2.INTER_LINEAR,
        keep_aspect_ratio: bool = False
    ):
        """
        Initialize resize transform.
        
        Args:
            target_size: Target size (width, height)
            interpolation: OpenCV interpolation method
            keep_aspect_ratio: Maintain aspect ratio with padding
        """
        self.target_size = target_size
        self.interpolation = interpolation
        self.keep_aspect_ratio = keep_aspect_ratio
    
    def apply(self, image: np.ndarray) -> np.ndarray:
        """Resize image to target size."""
        if self.keep_aspect_ratio:
            return self._resize_with_padding(image)
        return cv2.resize(image, self.target_size, interpolation=self.interpolation)
    
    def _resize_with_padding(self, image: np.ndarray) -> np.ndarray:
        """Resize with aspect ratio preservation and padding."""
        h, w = image.shape[:2]
        target_w, target_h = self.target_size
        
        scale = min(target_w / w, target_h / h)
        new_w, new_h = int(w * scale), int(h * scale)
        
        resized = cv2.resize(image, (new_w, new_h), interpolation=self.interpolation)
        
        # Create padded image
        if len(image.shape) == 3:
            padded = np.zeros((target_h, target_w, image.shape[2]), dtype=image.dtype)
        else:
            padded = np.zeros((target_h, target_w), dtype=image.dtype)
        
        # Center the image
        y_offset = (target_h - new_h) // 2
        x_offset = (target_w - new_w) // 2
        padded[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
        
        return padded


class NormalizeTransform(Transform):
    """Normalize image pixel values."""
    
    def __init__(
        self,
        mean: list = [0.485, 0.456, 0.406],
        std: list = [0.229, 0.224, 0.225],
        scale_to_unit: bool = True
    ):
        """
        Initialize normalization transform.
        
        Args:
            mean: Mean values for normalization (ImageNet default)
            std: Standard deviation values for normalization
            scale_to_unit: Scale image to [0, 1] before normalization
        """
        self.mean = np.array(mean, dtype=np.float32)
        self.std = np.array(std, dtype=np.float32)
        self.scale_to_unit = scale_to_unit
    
    def apply(self, image: np.ndarray) -> np.ndarray:
        """Normalize image."""
        image = image.astype(np.float32)
        
        # Scale to [0, 1] if needed
        if self.scale_to_unit and image.max() > 1.0:
            image = image / 255.0
        
        # Apply normalization
        return (image - self.mean) / self.std


class BGRToRGBTransform(Transform):
    """Convert BGR (OpenCV) to RGB format."""
    
    def apply(self, image: np.ndarray) -> np.ndarray:
        """Convert BGR to RGB."""
        if len(image.shape) == 3 and image.shape[2] == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return image


class ToFloatTransform(Transform):
    """Convert image to float32 and scale to [0, 1]."""
    
    def __init__(self, scale: float = 255.0):
        """
        Initialize float conversion transform.
        
        Args:
            scale: Value to divide by (typically 255 for uint8)
        """
        self.scale = scale
    
    def apply(self, image: np.ndarray) -> np.ndarray:
        """Convert to float and scale."""
        return image.astype(np.float32) / self.scale


class GrayscaleTransform(Transform):
    """Convert image to grayscale."""
    
    def apply(self, image: np.ndarray) -> np.ndarray:
        """Convert to grayscale."""
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image


class GaussianBlurTransform(Transform):
    """Apply Gaussian blur to image."""
    
    def __init__(self, kernel_size: Tuple[int, int] = (5, 5), sigma: float = 0):
        """
        Initialize Gaussian blur transform.
        
        Args:
            kernel_size: Blur kernel size (must be odd)
            sigma: Standard deviation (0 = auto-calculate)
        """
        self.kernel_size = kernel_size
        self.sigma = sigma
    
    def apply(self, image: np.ndarray) -> np.ndarray:
        """Apply Gaussian blur."""
        return cv2.GaussianBlur(image, self.kernel_size, self.sigma)


class BrightnessContrastTransform(Transform):
    """Adjust brightness and contrast."""
    
    def __init__(self, alpha: float = 1.0, beta: float = 0.0):
        """
        Initialize brightness/contrast transform.
        
        Args:
            alpha: Contrast control (1.0 = no change)
            beta: Brightness control (0 = no change)
        """
        self.alpha = alpha
        self.beta = beta
    
    def apply(self, image: np.ndarray) -> np.ndarray:
        """Adjust brightness and contrast."""
        return cv2.convertScaleAbs(image, alpha=self.alpha, beta=self.beta)


class HistogramEqualizationTransform(Transform):
    """Apply histogram equalization for contrast enhancement."""
    
    def apply(self, image: np.ndarray) -> np.ndarray:
        """Apply histogram equalization."""
        if len(image.shape) == 2:
            # Grayscale
            return cv2.equalizeHist(image)
        else:
            # Color - convert to YUV, equalize Y channel
            yuv = cv2.cvtColor(image, cv2.COLOR_BGR2YUV)
            yuv[:, :, 0] = cv2.equalizeHist(yuv[:, :, 0])
            return cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)
