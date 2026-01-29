"""Image preprocessing and manipulation utilities for real-time CV."""

import logging
from typing import Any, List, Optional, Tuple, Dict, Union
import numpy as np
import cv2

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Main image processing class for real-time preprocessing pipeline.
    
    Features:
    - Resizing with aspect ratio preservation
    - Pixel normalization (0-1 or ImageNet)
    - BGR to RGB conversion
    - Returns both original and processed frames
    - Batch processing support
    
    Example:
        >>> processor = ImageProcessor(
        ...     target_size=(640, 640),
        ...     normalize=True,
        ...     bgr_to_rgb=True
        ... )
        >>> original, processed = processor.process(frame, return_original=True)
    """
    
    def __init__(
        self,
        target_size: Tuple[int, int] = (640, 640),
        normalize: bool = True,
        normalization_type: str = "imagenet",
        bgr_to_rgb: bool = True,
        keep_aspect_ratio: bool = False,
        interpolation: int = cv2.INTER_LINEAR
    ):
        """
        Initialize image processor.
        
        Args:
            target_size: Target image size (width, height)
            normalize: Whether to normalize pixel values
            normalization_type: Type of normalization:
                - "0-1": Scale to [0, 1]
                - "imagenet": ImageNet mean/std normalization
                - "minus1-1": Scale to [-1, 1]
            bgr_to_rgb: Convert BGR (OpenCV) to RGB
            keep_aspect_ratio: Preserve aspect ratio when resizing
            interpolation: OpenCV interpolation method
        """
        self.target_size = target_size
        self.normalize = normalize
        self.normalization_type = normalization_type
        self.bgr_to_rgb = bgr_to_rgb
        self.keep_aspect_ratio = keep_aspect_ratio
        self.interpolation = interpolation
        
        # ImageNet normalization parameters
        self.imagenet_mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        self.imagenet_std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        
        self.transforms = []
        
        logger.info(
            f"ImageProcessor initialized: size={target_size}, "
            f"normalize={normalize}, bgr_to_rgb={bgr_to_rgb}"
        )
    
    def add_transform(self, transform):
        """Add a custom transformation to the pipeline."""
        self.transforms.append(transform)
        logger.debug(f"Added transform: {transform.__class__.__name__}")
    
    def resize(self, image: np.ndarray) -> np.ndarray:
        """
        Resize image to target size.
        
        Args:
            image: Input image
            
        Returns:
            Resized image
        """
        if self.keep_aspect_ratio:
            return self._resize_with_aspect_ratio(image)
        else:
            return cv2.resize(image, self.target_size, interpolation=self.interpolation)
    
    def _resize_with_aspect_ratio(self, image: np.ndarray) -> np.ndarray:
        """
        Resize image while maintaining aspect ratio with padding.
        
        Args:
            image: Input image
            
        Returns:
            Resized and padded image
        """
        h, w = image.shape[:2]
        target_w, target_h = self.target_size
        
        # Calculate scaling factor
        scale = min(target_w / w, target_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        # Resize image
        resized = cv2.resize(image, (new_w, new_h), interpolation=self.interpolation)
        
        # Create padded image
        if len(image.shape) == 3:
            padded = np.zeros((target_h, target_w, image.shape[2]), dtype=image.dtype)
        else:
            padded = np.zeros((target_h, target_w), dtype=image.dtype)
        
        # Calculate padding offsets (center the image)
        y_offset = (target_h - new_h) // 2
        x_offset = (target_w - new_w) // 2
        
        # Place resized image in center
        padded[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
        
        return padded
    
    def normalize_pixels(self, image: np.ndarray) -> np.ndarray:
        """
        Normalize pixel values.
        
        Args:
            image: Input image (uint8 or float)
            
        Returns:
            Normalized image (float32)
        """
        # Convert to float32 if needed
        if image.dtype == np.uint8:
            image = image.astype(np.float32) / 255.0
        
        if self.normalization_type == "0-1":
            # Already normalized to [0, 1]
            return image
        
        elif self.normalization_type == "imagenet":
            # ImageNet normalization
            return (image - self.imagenet_mean) / self.imagenet_std
        
        elif self.normalization_type == "minus1-1":
            # Scale to [-1, 1]
            return (image * 2.0) - 1.0
        
        else:
            logger.warning(f"Unknown normalization type: {self.normalization_type}")
            return image
    
    def convert_color(self, image: np.ndarray) -> np.ndarray:
        """
        Convert BGR to RGB if needed.
        
        Args:
            image: Input image in BGR format
            
        Returns:
            Image in RGB format
        """
        if self.bgr_to_rgb and len(image.shape) == 3 and image.shape[2] == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return image
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        Apply full preprocessing pipeline (legacy method).
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Preprocessed image
        """
        return self.process(image, return_original=False)
    
    def process(
        self,
        image: np.ndarray,
        return_original: bool = False
    ) -> Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]:
        """
        Process image with full pipeline.
        
        Args:
            image: Input image (BGR format from OpenCV)
            return_original: If True, return (original, processed) tuple
            
        Returns:
            Processed image, or tuple of (original, processed) if return_original=True
        """
        import time as timing
        preprocess_start = timing.time()
        logger.debug(f"Preprocessing started | input_shape={image.shape} | dtype={image.dtype} | target_size={self.target_size}")
        
        original = image.copy() if return_original else None
        processed = image.copy()
        
        # 1. Resize
        if processed.shape[:2][::-1] != self.target_size:
            logger.debug(f"Resizing: {processed.shape[:2][::-1]} → {self.target_size}")
            processed = self.resize(processed)
            logger.debug(f"Resized | output_shape={processed.shape}")
        
        # 2. Convert BGR to RGB
        if self.bgr_to_rgb:
            logger.debug(f"Converting color space: BGR → RGB")
            processed = self.convert_color(processed)
            logger.debug(f"Color converted | shape={processed.shape}")
        
        # 3. Normalize pixel values
        if self.normalize:
            logger.debug(f"Normalizing pixels | type={self.normalization_type}")
            processed = self.normalize_pixels(processed)
            logger.debug(f"Normalized | dtype={processed.dtype}")
        
        # 4. Apply custom transforms
        for i, transform in enumerate(self.transforms):
            logger.debug(f"Applying transform {i}: {transform.__class__.__name__}")
            processed = transform.apply(processed)
            logger.debug(f"Transform applied | shape={processed.shape}")
        
        preprocess_time = (timing.time() - preprocess_start) * 1000  # Convert to ms
        logger.debug(f"Preprocessing complete | output_shape={processed.shape} | time={preprocess_time:.2f}ms")
        
        if return_original:
            return original, processed
        return processed
    
    def process_stream(
        self,
        frames,
        return_originals: bool = True
    ):
        """
        Process a stream of frames (generator).
        
        Args:
            frames: Generator or iterable yielding frames
            return_originals: Whether to yield original frames
            
        Yields:
            (original, processed) tuple if return_originals=True, else processed only
        """
        for frame in frames:
            if return_originals:
                yield self.process(frame, return_original=True)
            else:
                yield self.process(frame, return_original=False)
    
    def batch_process(
        self,
        images: List[np.ndarray],
        return_originals: bool = False
    ) -> Union[List[np.ndarray], Tuple[List[np.ndarray], List[np.ndarray]]]:
        """
        Process a batch of images.
        
        Args:
            images: List of input images
            return_originals: If True, return (originals, processed) tuple
            
        Returns:
            List of processed images, or tuple of (originals, processed) lists
        """
        if return_originals:
            originals = []
            processed = []
            for img in images:
                orig, proc = self.process(img, return_original=True)
                originals.append(orig)
                processed.append(proc)
            return originals, processed
        else:
            return [self.process(img, return_original=False) for img in images]
    
    def batch_preprocess(self, images: List[np.ndarray]) -> List[np.ndarray]:
        """Legacy method for batch preprocessing."""
        return self.batch_process(images, return_originals=False)
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get processor configuration information.
        
        Returns:
            Dictionary with processor settings
        """
        return {
            'target_size': self.target_size,
            'normalize': self.normalize,
            'normalization_type': self.normalization_type,
            'bgr_to_rgb': self.bgr_to_rgb,
            'keep_aspect_ratio': self.keep_aspect_ratio,
            'num_transforms': len(self.transforms)
        }
