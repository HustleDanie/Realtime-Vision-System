"""
Integration of async cloud logging with YOLO edge inference service
"""

import asyncio
import logging
from typing import Dict, List, Optional
from pathlib import Path
import numpy as np
from datetime import datetime

from src.yolo_inference.detector import YOLODetector, Detection
from src.cloud_logging.async_client import AsyncLoggingClient, BatchedLogger

logger = logging.getLogger(__name__)


class EdgeInferenceWithCloudLogging:
    """
    YOLO detector integrated with async cloud logging
    
    - Runs inference on edge
    - Asynchronously sends results to cloud
    - Handles local buffering on network failure
    """
    
    def __init__(
        self,
        yolo_model_path: str = "yolov8n.pt",
        cloud_api_endpoint: str = "http://localhost:8001/log",
        cloud_api_key: Optional[str] = None,
        batch_size: int = 32,
        batch_timeout_seconds: int = 10,
        buffer_file: Optional[str] = None,
        edge_device_id: Optional[str] = None,
        confidence_threshold: float = 0.5,
    ):
        """
        Initialize edge inference service with cloud logging
        
        Args:
            yolo_model_path: Path to YOLO model
            cloud_api_endpoint: Cloud logging API endpoint
            cloud_api_key: Optional API key
            batch_size: Predictions per batch
            batch_timeout_seconds: Max wait before sending partial batch
            buffer_file: Local buffer file for failed predictions
            edge_device_id: Identifier for this edge device
            confidence_threshold: Confidence threshold for detections
        """
        self.detector = YOLODetector(
            model_path=yolo_model_path,
            confidence_threshold=confidence_threshold,
        )
        
        self.cloud_client = AsyncLoggingClient(
            api_endpoint=cloud_api_endpoint,
            api_key=cloud_api_key,
            batch_size=batch_size,
            batch_timeout_seconds=batch_timeout_seconds,
            buffer_file=buffer_file,
            edge_device_id=edge_device_id,
        )
        
        self.logger_wrapper = BatchedLogger(self.cloud_client)
        self.model_version = "v1.0"
        self.model_name = "yolov8-prod"
    
    async def start(self):
        """Start the inference service and cloud logging"""
        await self.cloud_client.start()
        logger.info("EdgeInferenceWithCloudLogging started")
    
    async def shutdown(self):
        """Gracefully shutdown"""
        logger.info("Shutting down EdgeInferenceWithCloudLogging")
        await self.cloud_client.shutdown()
    
    async def process_image_async(
        self,
        image_path: str,
        image_id: Optional[str] = None,
    ) -> Dict:
        """
        Process image with inference and async logging
        
        Args:
            image_path: Path to image file
            image_id: Optional image identifier (uses filename if not provided)
            
        Returns:
            Detection results
        """
        if image_id is None:
            image_id = Path(image_path).stem
        
        # Run inference on edge (blocking, but OK since it's CPU-bound)
        import time
        start_time = time.time()
        results = self.detector.detect(image_path)
        inference_time_ms = (time.time() - start_time) * 1000
        
        # Extract detection info
        detections = []
        confidence_scores = []
        
        for detection in results["detections"]:
            det_dict = {
                "class": detection.class_name,
                "confidence": float(detection.confidence),
                "bbox": detection.bbox,
                "uncertain": detection.uncertain,
            }
            detections.append(det_dict)
            confidence_scores.append(float(detection.confidence))
        
        defect_detected = len(results["detections"]) > 0
        
        # Asynchronously log to cloud (non-blocking)
        await self.logger_wrapper.log_detection(
            image_id=image_id,
            model_version=self.model_version,
            model_name=self.model_name,
            inference_time_ms=inference_time_ms,
            detections=detections,
            defect_detected=defect_detected,
            confidence_scores=confidence_scores or [0.0],
            processing_notes=f"Processed at {datetime.now().isoformat()}",
        )
        
        # Return detection results immediately (don't wait for cloud logging)
        return {
            "image_id": image_id,
            "detections": detections,
            "defect_detected": defect_detected,
            "inference_time_ms": inference_time_ms,
            "logged_to_cloud": True,
        }
    
    def get_cloud_logging_stats(self) -> Dict:
        """Get cloud logging statistics"""
        return self.cloud_client.get_stats()


async def example_inference_pipeline():
    """
    Example: Process multiple images with async cloud logging
    """
    logging.basicConfig(level=logging.INFO)
    
    # Create service
    service = EdgeInferenceWithCloudLogging(
        cloud_api_endpoint="http://localhost:8001/log",
        edge_device_id="factory-camera-01",
        buffer_file="/tmp/edge_predictions.jsonl",
    )
    
    await service.start()
    
    try:
        # Simulate processing images from a folder
        image_files = [
            "sample_images/defect_001.jpg",
            "sample_images/defect_002.jpg",
            "sample_images/normal_001.jpg",
        ]
        
        # Process all images concurrently (or with minimal blocking)
        for image_file in image_files:
            result = await service.process_image_async(image_file)
            print(f"Processed {image_file}: {result}")
            
            # Don't block - logging happens asynchronously
            await asyncio.sleep(0.1)
        
        # Wait for final batch to be sent
        await asyncio.sleep(12)
        
        # Print statistics
        stats = service.get_cloud_logging_stats()
        print(f"\nCloud Logging Stats: {stats}")
    
    finally:
        await service.shutdown()


if __name__ == "__main__":
    asyncio.run(example_inference_pipeline())
