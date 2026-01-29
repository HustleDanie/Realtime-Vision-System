"""
Configuration for cloud logging service
"""

from dataclasses import dataclass
from typing import Optional
from pathlib import Path
import os


@dataclass
class CloudLoggingConfig:
    """Cloud logging configuration"""
    
    # API Configuration
    api_endpoint: str = os.getenv(
        "CLOUD_LOGGING_ENDPOINT",
        "http://logging-service:8001/log"
    )
    api_key: Optional[str] = os.getenv("CLOUD_LOGGING_API_KEY")
    
    # Batching Configuration
    batch_size: int = int(os.getenv("BATCH_SIZE", "32"))
    batch_timeout_seconds: int = int(os.getenv("BATCH_TIMEOUT_SECONDS", "10"))
    
    # Retry Configuration
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    retry_backoff_multiplier: float = float(os.getenv("RETRY_BACKOFF_MULTIPLIER", "2.0"))
    timeout_seconds: int = int(os.getenv("TIMEOUT_SECONDS", "30"))
    
    # Buffering Configuration
    buffer_file: Optional[str] = os.getenv(
        "BUFFER_FILE",
        "/app/data/prediction_buffer.jsonl"
    )
    
    # Edge Device Configuration
    edge_device_id: str = os.getenv("EDGE_DEVICE_ID", "edge-device-default")
    
    # Enable/Disable
    enabled: bool = os.getenv("CLOUD_LOGGING_ENABLED", "true").lower() == "true"
    
    def validate(self):
        """Validate configuration"""
        if self.enabled and not self.api_endpoint:
            raise ValueError("CLOUD_LOGGING_ENDPOINT is required when enabled")
        
        if self.batch_size <= 0:
            raise ValueError("BATCH_SIZE must be positive")
        
        if self.batch_timeout_seconds <= 0:
            raise ValueError("BATCH_TIMEOUT_SECONDS must be positive")
        
        if self.buffer_file:
            Path(self.buffer_file).parent.mkdir(parents=True, exist_ok=True)
    
    def __str__(self):
        """String representation (hide API key)"""
        return (
            f"CloudLoggingConfig("
            f"endpoint={self.api_endpoint}, "
            f"batch_size={self.batch_size}, "
            f"timeout={self.timeout_seconds}s, "
            f"retries={self.max_retries}, "
            f"buffer={self.buffer_file}, "
            f"enabled={self.enabled})"
        )


def get_config() -> CloudLoggingConfig:
    """Get cloud logging configuration from environment"""
    config = CloudLoggingConfig()
    config.validate()
    return config
