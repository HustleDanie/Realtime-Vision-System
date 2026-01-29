"""Tests for utils module."""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import setup_logger, ConfigLoader, Visualizer


class TestLogger:
    """Test cases for logging utilities."""
    
    def test_setup_logger(self):
        """Test logger setup."""
        logger = setup_logger("test_logger")
        assert logger.name == "test_logger"
        assert len(logger.handlers) > 0


class TestConfigLoader:
    """Test cases for ConfigLoader class."""
    
    def test_config_loader_init(self):
        """Test config loader initialization."""
        loader = ConfigLoader(config_dir="configs")
        assert loader.config_dir.name == "configs"
        assert len(loader.configs) == 0


class TestVisualizer:
    """Test cases for Visualizer class."""
    
    def test_visualizer_init(self):
        """Test visualizer initialization."""
        viz = Visualizer()
        assert isinstance(viz.class_colors, dict)
