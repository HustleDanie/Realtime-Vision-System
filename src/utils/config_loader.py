"""Configuration loading and management utilities."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional
import json

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Handles loading and managing configuration files."""
    
    def __init__(self, config_dir: str = "configs"):
        """
        Initialize configuration loader.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self.configs = {}
        logger.info(f"ConfigLoader initialized with config directory: {config_dir}")
    
    def load_config(self, config_name: str, format: str = "yaml") -> Dict[str, Any]:
        """
        Load configuration file.
        
        Args:
            config_name: Name of configuration file
            format: Configuration file format (yaml, json)
            
        Returns:
            Configuration dictionary
        """
        config_path = self.config_dir / f"{config_name}.{format}"
        
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            raise FileNotFoundError(f"Config not found: {config_path}")
        
        logger.info(f"Loading configuration from {config_path}")
        
        # Placeholder: would load actual config based on format
        if format == "json":
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:  # yaml
            # Would use yaml.safe_load in production
            config = {}
        
        self.configs[config_name] = config
        return config
    
    def get_config(self, config_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a loaded configuration.
        
        Args:
            config_name: Name of configuration
            
        Returns:
            Configuration dictionary or None
        """
        return self.configs.get(config_name)
    
    def get_value(self, config_name: str, key: str, default: Any = None) -> Any:
        """
        Get a specific value from configuration.
        
        Args:
            config_name: Name of configuration
            key: Configuration key (supports dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        config = self.get_config(config_name)
        if config is None:
            return default
        
        # Support dot notation for nested keys
        keys = key.split('.')
        value = config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        
        return value if value is not None else default
