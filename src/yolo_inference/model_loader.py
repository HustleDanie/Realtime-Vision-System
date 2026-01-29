"""Model loading utilities for YOLO models with GPU/CPU support."""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union
import torch

logger = logging.getLogger(__name__)


class ModelLoader:
    """Handles loading and managing YOLO models with automatic device selection.
    
    Features:
    - Automatic GPU/CPU device detection
    - Model caching and management
    - Support for multiple YOLO versions
    - Device information and monitoring
    
    Example:
        >>> loader = ModelLoader(models_dir="models", device="auto")
        >>> model = loader.load_model("yolov8n.pt", model_type="yolov8")
        >>> print(loader.get_device_info())
    """
    
    def __init__(
        self,
        models_dir: str = "models",
        device: str = "auto",
        cache_models: bool = True
    ):
        """
        Initialize model loader.
        
        Args:
            models_dir: Directory containing model files
            device: Compute device ('auto', 'cuda', 'cpu', 'cuda:0', etc.)
            cache_models: Keep loaded models in memory
        """
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.cache_models = cache_models
        self.loaded_models = {}
        
        # Setup device
        self.device = self._setup_device(device)
        
        logger.info(
            f"ModelLoader initialized: dir={models_dir}, "
            f"device={self.device}, caching={cache_models}"
        )
    
    def _setup_device(self, device: str) -> torch.device:
        """
        Setup compute device with automatic detection.
        
        Args:
            device: Device specification
            
        Returns:
            torch.device object
        """
        if device == "auto":
            if torch.cuda.is_available():
                device_obj = torch.device("cuda")
                logger.info(
                    f"Auto-selected GPU: {torch.cuda.get_device_name(0)} "
                    f"({torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB)"
                )
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                device_obj = torch.device("mps")
                logger.info("Auto-selected Apple MPS device")
            else:
                device_obj = torch.device("cpu")
                logger.info("Auto-selected CPU (no GPU available)")
        else:
            device_obj = torch.device(device)
            logger.info(f"Using specified device: {device}")
        
        return device_obj
    
    def load_model(
        self,
        model_name: str,
        model_type: str = "yolov8",
        force_reload: bool = False,
        **kwargs
    ) -> Any:
        """
        Load a YOLO model by name.
        
        Args:
            model_name: Name of the model file
            model_type: Type of YOLO model ('yolov5', 'yolov8')
            force_reload: Force reload even if cached
            **kwargs: Additional arguments for model loading
            
        Returns:
            Loaded model object
        """
        # Check cache
        if not force_reload and model_name in self.loaded_models:
            logger.info(f"Using cached model: {model_name}")
            return self.loaded_models[model_name]
        
        model_path = self.models_dir / model_name
        
        if not model_path.exists():
            logger.error(f"Model file not found: {model_path}")
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        logger.info(f"Loading {model_type} model from {model_path}")
        
        try:
            if model_type.lower() == "yolov8":
                model = self._load_yolov8(model_path, **kwargs)
            elif model_type.lower() == "yolov5":
                model = self._load_yolov5(model_path, **kwargs)
            else:
                raise ValueError(f"Unsupported model type: {model_type}")
            
            # Cache model if enabled
            if self.cache_models:
                self.loaded_models[model_name] = model
            
            logger.info(f"Model loaded successfully: {model_name}")
            return model
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def _load_yolov8(self, model_path: Path, **kwargs) -> Any:
        """Load YOLOv8 model using ultralytics."""
        try:
            from ultralytics import YOLO
        except ImportError:
            raise ImportError(
                "ultralytics not installed. Install with: pip install ultralytics"
            )
        
        model = YOLO(str(model_path))
        model.to(self.device)
        
        return model
    
    def _load_yolov5(self, model_path: Path, **kwargs) -> Any:
        """Load YOLOv5 model using torch.hub."""
        # Check if it's a standard YOLOv5 model
        if model_path.stem.startswith("yolov5"):
            model = torch.hub.load(
                'ultralytics/yolov5',
                model_path.stem,
                pretrained=True
            )
        else:
            model = torch.hub.load(
                'ultralytics/yolov5',
                'custom',
                path=str(model_path)
            )
        
        model.to(self.device)
        model.eval()
        
        return model
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """
        Get information about a loaded model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Dictionary with model information
        """
        if model_name not in self.loaded_models:
            logger.warning(f"Model {model_name} not loaded")
            return {
                'name': model_name,
                'status': 'not_loaded',
                'path': str(self.models_dir / model_name)
            }
        
        model = self.loaded_models[model_name]
        
        info = {
            'name': model_name,
            'status': 'loaded',
            'path': str(self.models_dir / model_name),
            'device': str(self.device),
            'cached': True
        }
        
        # Add model-specific info
        if hasattr(model, 'names'):
            info['num_classes'] = len(model.names)
            info['class_names'] = model.names
        
        return info
    
    def get_device_info(self) -> Dict[str, Any]:
        """
        Get detailed information about the compute device.
        
        Returns:
            Dictionary with device information
        """
        info = {
            'device': str(self.device),
            'device_type': self.device.type,
            'pytorch_version': torch.__version__,
            'cuda_available': torch.cuda.is_available(),
        }
        
        if torch.cuda.is_available():
            info.update({
                'cuda_version': torch.version.cuda,
                'cudnn_version': torch.backends.cudnn.version(),
                'num_gpus': torch.cuda.device_count(),
                'current_gpu': torch.cuda.current_device(),
                'gpu_name': torch.cuda.get_device_name(0),
                'gpu_memory_total': f"{torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB",
                'gpu_memory_allocated': f"{torch.cuda.memory_allocated(0) / 1e9:.2f} GB",
                'gpu_memory_reserved': f"{torch.cuda.memory_reserved(0) / 1e9:.2f} GB",
            })
        
        if hasattr(torch.backends, 'mps'):
            info['mps_available'] = torch.backends.mps.is_available()
        
        return info
    
    def list_models(self) -> list:
        """
        List all available models in the models directory.
        
        Returns:
            List of model file names
        """
        model_files = list(self.models_dir.glob("*.pt"))
        model_files += list(self.models_dir.glob("*.pth"))
        return [f.name for f in sorted(model_files)]
    
    def unload_model(self, model_name: str):
        """
        Unload a model from memory.
        
        Args:
            model_name: Name of the model to unload
        """
        if model_name in self.loaded_models:
            del self.loaded_models[model_name]
            
            # Clear CUDA cache if on GPU
            if self.device.type == "cuda":
                torch.cuda.empty_cache()
            
            logger.info(f"Unloaded model: {model_name}")
        else:
            logger.warning(f"Model not loaded: {model_name}")
    
    def unload_all(self):
        """Unload all cached models."""
        num_models = len(self.loaded_models)
        self.loaded_models.clear()
        
        if self.device.type == "cuda":
            torch.cuda.empty_cache()
        
        logger.info(f"Unloaded {num_models} models")
    
    def change_device(self, device: str):
        """
        Change the compute device and reload models.
        
        Args:
            device: New device specification
        """
        old_device = self.device
        self.device = self._setup_device(device)
        
        if old_device != self.device:
            logger.info(f"Device changed: {old_device} -> {self.device}")
            
            # Reload cached models on new device
            if self.loaded_models:
                logger.info("Reloading models on new device...")
                models_to_reload = list(self.loaded_models.keys())
                self.unload_all()
                
                for model_name in models_to_reload:
                    try:
                        self.load_model(model_name)
                    except Exception as e:
                        logger.error(f"Failed to reload {model_name}: {e}")
    
    def __repr__(self) -> str:
        return (
            f"ModelLoader(device={self.device}, "
            f"models_dir={self.models_dir}, "
            f"cached={len(self.loaded_models)})"
        )
