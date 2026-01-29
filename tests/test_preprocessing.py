"""Tests for preprocessing module."""

import pytest
import numpy as np
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from preprocessing import ImageProcessor
from preprocessing.transforms import ResizeTransform, NormalizeTransform


class TestImageProcessor:
    """Test cases for ImageProcessor class."""
    
    def test_processor_initialization(self):
        """Test image processor initialization."""
        processor = ImageProcessor(target_size=(640, 640))
        assert processor.target_size == (640, 640)
        assert len(processor.transforms) == 0
    
    def test_add_transform(self):
        """Test adding transforms to processor."""
        processor = ImageProcessor()
        transform = ResizeTransform((640, 640))
        processor.add_transform(transform)
        assert len(processor.transforms) == 1


class TestTransforms:
    """Test cases for transform classes."""
    
    def test_resize_transform(self):
        """Test resize transformation."""
        transform = ResizeTransform((640, 640))
        assert transform.target_size == (640, 640)
    
    def test_normalize_transform(self):
        """Test normalization transformation."""
        transform = NormalizeTransform()
        assert len(transform.mean) == 3
        assert len(transform.std) == 3
