"""
Configuration management for ML vision logging service.
Handles settings for database, storage, and logging behavior.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration."""

    url: str = "sqlite:///./vision_logs.db"
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    auto_migrate: bool = True

    def __post_init__(self):
        """Validate configuration."""
        if not self.url:
            raise ValueError("Database URL cannot be empty")


@dataclass
class StorageConfig:
    """Image storage configuration."""

    base_path: str = "./prediction_images"
    organize_by_date: bool = True
    organize_by_result: bool = True
    image_quality: int = 95
    max_image_age_days: int = 90

    def __post_init__(self):
        """Validate configuration."""
        if not 0 < self.image_quality <= 100:
            raise ValueError("Image quality must be between 1 and 100")
        if self.max_image_age_days <= 0:
            raise ValueError("Max image age must be positive")


@dataclass
class LoggingConfig:
    """Application logging configuration."""

    log_level: str = "INFO"
    log_file: Optional[str] = None
    log_format: str = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    max_bytes: int = 10485760  # 10MB
    backup_count: int = 5

    def __post_init__(self):
        """Validate configuration."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")


@dataclass
class LoggingServiceConfig:
    """Complete logging service configuration."""

    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    model_version: str = "unknown"
    model_name: str = "unknown"
    enable_async_writes: bool = False
    batch_size: int = 10

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "LoggingServiceConfig":
        """
        Create configuration from dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            LoggingServiceConfig instance
        """
        return cls(
            database=DatabaseConfig(**config_dict.get("database", {})),
            storage=StorageConfig(**config_dict.get("storage", {})),
            logging=LoggingConfig(**config_dict.get("logging", {})),
            model_version=config_dict.get("model_version", "unknown"),
            model_name=config_dict.get("model_name", "unknown"),
            enable_async_writes=config_dict.get("enable_async_writes", False),
            batch_size=config_dict.get("batch_size", 10),
        )

    @classmethod
    def from_json_file(cls, filepath: str) -> "LoggingServiceConfig":
        """
        Load configuration from JSON file.

        Args:
            filepath: Path to JSON config file

        Returns:
            LoggingServiceConfig instance

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If JSON is invalid
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {filepath}")

        with open(path, "r") as f:
            config_dict = json.load(f)

        return cls.from_dict(config_dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "database": {
                "url": self.database.url,
                "echo": self.database.echo,
                "pool_size": self.database.pool_size,
                "max_overflow": self.database.max_overflow,
                "auto_migrate": self.database.auto_migrate,
            },
            "storage": {
                "base_path": self.storage.base_path,
                "organize_by_date": self.storage.organize_by_date,
                "organize_by_result": self.storage.organize_by_result,
                "image_quality": self.storage.image_quality,
                "max_image_age_days": self.storage.max_image_age_days,
            },
            "logging": {
                "log_level": self.logging.log_level,
                "log_file": self.logging.log_file,
                "log_format": self.logging.log_format,
                "max_bytes": self.logging.max_bytes,
                "backup_count": self.logging.backup_count,
            },
            "model_version": self.model_version,
            "model_name": self.model_name,
            "enable_async_writes": self.enable_async_writes,
            "batch_size": self.batch_size,
        }

    def save_to_json(self, filepath: str) -> None:
        """
        Save configuration to JSON file.

        Args:
            filepath: Path where to save config file
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

        logger.info(f"Configuration saved to {filepath}")


# Default configuration
DEFAULT_CONFIG = LoggingServiceConfig()
