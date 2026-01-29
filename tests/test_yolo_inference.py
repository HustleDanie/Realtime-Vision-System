"""Tests for yolo_inference module."""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from yolo_inference import YOLODetector, ModelLoader
from yolo_inference.detector import Detection


class TestDetection:
    """Test cases for Detection class."""
    
    def test_detection_creation(self):
        """Test detection object creation."""
        det = Detection([10, 20, 100, 200], 0.95, 0, "person")
        assert det.confidence == 0.95
        assert det.class_name == "person"
    
    def test_detection_to_dict(self):
        """Test detection to dictionary conversion."""
        det = Detection([10, 20, 100, 200], 0.95, 0, "person")
        det_dict = det.to_dict()
        assert 'bbox' in det_dict
        assert 'confidence' in det_dict


class TestYOLODetector:
    """Test cases for YOLODetector class."""
    
    def test_detector_initialization(self):
        """Test detector initialization."""
        detector = YOLODetector("model.pt", confidence_threshold=0.6)
        assert detector.confidence_threshold == 0.6
        assert detector.model is None


class TestModelLoader:
    """Test cases for ModelLoader class."""
    
    def test_loader_initialization(self):
        """Test model loader initialization."""
        loader = ModelLoader(models_dir="models")
        assert loader.models_dir.name == "models"
        assert len(loader.loaded_models) == 0
