"""
Asynchronous Cloud Logging Client for Edge Inference

Sends prediction results from edge inference service to cloud logging API endpoint
with batching, retries, and error handling.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import aiohttp
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Single prediction result to be logged"""
    image_id: str
    timestamp: float
    model_version: str
    model_name: str
    inference_time_ms: float
    detections: List[Dict[str, Any]]  # [{class, confidence, bbox, ...}]
    defect_detected: bool
    confidence_scores: List[float]
    processing_notes: Optional[str] = None
    edge_device_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class AsyncLoggingClient:
    """
    Async client for sending predictions to cloud logging API
    
    Features:
    - Batching for efficiency
    - Automatic retries with exponential backoff
    - Local buffering on network failure
    - Graceful shutdown
    - Connection pooling
    """
    
    def __init__(
        self,
        api_endpoint: str,
        api_key: Optional[str] = None,
        batch_size: int = 32,
        batch_timeout_seconds: int = 10,
        max_retries: int = 3,
        retry_backoff_multiplier: float = 2.0,
        buffer_file: Optional[str] = None,
        timeout_seconds: int = 30,
        edge_device_id: Optional[str] = None,
    ):
        """
        Initialize AsyncLoggingClient
        
        Args:
            api_endpoint: Cloud API endpoint URL (e.g., http://logging-service:8001/log)
            api_key: Optional API key for authentication
            batch_size: Number of predictions to batch before sending
            batch_timeout_seconds: Max seconds to wait before sending partial batch
            max_retries: Max retries for failed requests
            retry_backoff_multiplier: Multiplier for exponential backoff
            buffer_file: Optional file path to persist failed predictions locally
            timeout_seconds: Request timeout in seconds
            edge_device_id: Identifier for edge device sending predictions
        """
        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.batch_size = batch_size
        self.batch_timeout_seconds = batch_timeout_seconds
        self.max_retries = max_retries
        self.retry_backoff_multiplier = retry_backoff_multiplier
        self.buffer_file = Path(buffer_file) if buffer_file else None
        self.timeout_seconds = timeout_seconds
        self.edge_device_id = edge_device_id
        
        self._batch: List[PredictionResult] = []
        self._batch_lock = asyncio.Lock()
        self._session: Optional[aiohttp.ClientSession] = None
        self._background_task: Optional[asyncio.Task] = None
        self._shutdown = False
        self._stats = {
            "sent": 0,
            "failed": 0,
            "retried": 0,
            "buffered": 0,
        }
        
        logger.info(f"AsyncLoggingClient initialized: {api_endpoint}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.shutdown()
    
    async def start(self):
        """Start the async logging client and background tasks"""
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
            self._session = aiohttp.ClientSession(timeout=timeout)
        
        # Load buffered predictions from disk
        await self._load_buffered_predictions()
        
        # Start background batch sender task
        self._background_task = asyncio.create_task(self._batch_sender())
        logger.info("AsyncLoggingClient started")
    
    async def shutdown(self):
        """Gracefully shutdown the logging client"""
        logger.info("Shutting down AsyncLoggingClient...")
        self._shutdown = True
        
        # Send any remaining batched predictions
        await self._flush_batch()
        
        # Cancel background task
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
        
        # Close session
        if self._session:
            await self._session.close()
        
        logger.info(f"AsyncLoggingClient stats: {self._stats}")
    
    async def log_prediction(self, prediction: PredictionResult) -> bool:
        """
        Queue a prediction for logging
        
        Args:
            prediction: PredictionResult object
            
        Returns:
            True if queued successfully, False if buffer is full
        """
        if prediction.edge_device_id is None:
            prediction.edge_device_id = self.edge_device_id
        
        async with self._batch_lock:
            self._batch.append(prediction)
            
            # Send immediately if batch is full
            if len(self._batch) >= self.batch_size:
                await self._flush_batch()
        
        return True
    
    async def _batch_sender(self):
        """Background task that sends batches periodically"""
        while not self._shutdown:
            try:
                await asyncio.sleep(self.batch_timeout_seconds)
                async with self._batch_lock:
                    if self._batch and not self._shutdown:
                        await self._flush_batch()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in batch sender: {e}")
    
    async def _flush_batch(self):
        """Send current batch to cloud API"""
        if not self._batch:
            return
        
        batch_to_send = self._batch.copy()
        self._batch.clear()
        
        success = await self._send_predictions(batch_to_send)
        
        if not success:
            # Buffer predictions locally on failure
            await self._buffer_predictions(batch_to_send)
    
    async def _send_predictions(
        self,
        predictions: List[PredictionResult],
        retry_count: int = 0,
    ) -> bool:
        """
        Send predictions to cloud API with retry logic
        
        Args:
            predictions: List of predictions to send
            retry_count: Current retry attempt
            
        Returns:
            True if successful, False if all retries exhausted
        """
        if not predictions:
            return True
        
        payload = {
            "predictions": [p.to_dict() for p in predictions],
            "batch_size": len(predictions),
            "timestamp": datetime.utcnow().isoformat(),
            "edge_device_id": self.edge_device_id,
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "EdgeInferenceService/1.0",
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            async with self._session.post(
                self.api_endpoint,
                json=payload,
                headers=headers,
                ssl=False,
            ) as response:
                if response.status == 200:
                    logger.debug(f"Sent {len(predictions)} predictions")
                    self._stats["sent"] += len(predictions)
                    return True
                else:
                    logger.warning(
                        f"API returned {response.status}: {await response.text()}"
                    )
                    return False
        
        except asyncio.TimeoutError:
            logger.error(f"Request timeout to {self.api_endpoint}")
            return False
        
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            
            # Retry with exponential backoff
            if retry_count < self.max_retries:
                wait_time = (self.retry_backoff_multiplier ** retry_count)
                logger.info(f"Retrying in {wait_time}s... (attempt {retry_count + 1})")
                self._stats["retried"] += len(predictions)
                
                await asyncio.sleep(wait_time)
                return await self._send_predictions(predictions, retry_count + 1)
            else:
                logger.error(
                    f"Failed to send predictions after {self.max_retries} retries"
                )
                self._stats["failed"] += len(predictions)
                return False
        
        except Exception as e:
            logger.error(f"Unexpected error sending predictions: {e}")
            self._stats["failed"] += len(predictions)
            return False
    
    async def _buffer_predictions(self, predictions: List[PredictionResult]):
        """
        Buffer predictions to disk for later retry
        
        Args:
            predictions: List of predictions to buffer
        """
        if not self.buffer_file:
            logger.warning("No buffer file configured, predictions will be lost")
            return
        
        try:
            # Append predictions to buffer file (JSONL format)
            self.buffer_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.buffer_file, "a") as f:
                for pred in predictions:
                    line = json.dumps(pred.to_dict())
                    f.write(line + "\n")
            
            self._stats["buffered"] += len(predictions)
            logger.info(f"Buffered {len(predictions)} predictions to {self.buffer_file}")
        
        except Exception as e:
            logger.error(f"Failed to buffer predictions: {e}")
    
    async def _load_buffered_predictions(self):
        """Load buffered predictions from disk and send them"""
        if not self.buffer_file or not self.buffer_file.exists():
            return
        
        try:
            buffered_preds = []
            
            with open(self.buffer_file, "r") as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        pred = PredictionResult(**data)
                        buffered_preds.append(pred)
                    except json.JSONDecodeError:
                        continue
            
            if buffered_preds:
                logger.info(f"Loaded {len(buffered_preds)} buffered predictions")
                
                # Try to send buffered predictions
                success = await self._send_predictions(buffered_preds)
                
                # If successful, clear buffer file
                if success:
                    self.buffer_file.unlink()
                    logger.info("Cleared buffer file")
        
        except Exception as e:
            logger.error(f"Error loading buffered predictions: {e}")
    
    def get_stats(self) -> Dict[str, int]:
        """Get logging statistics"""
        return self._stats.copy()


class BatchedLogger:
    """
    Simplified wrapper for logging predictions with automatic batching
    """
    
    def __init__(self, client: AsyncLoggingClient):
        """
        Initialize BatchedLogger
        
        Args:
            client: AsyncLoggingClient instance
        """
        self.client = client
    
    async def log_detection(
        self,
        image_id: str,
        model_version: str,
        model_name: str,
        inference_time_ms: float,
        detections: List[Dict],
        defect_detected: bool,
        confidence_scores: Optional[List[float]] = None,
        processing_notes: Optional[str] = None,
    ) -> bool:
        """
        Log a detection result
        
        Args:
            image_id: Unique image identifier
            model_version: Model version used for inference
            model_name: Model name
            inference_time_ms: Inference time in milliseconds
            detections: List of detection dicts with class, confidence, bbox
            defect_detected: Whether defect was detected
            confidence_scores: List of confidence scores
            processing_notes: Optional processing notes
            
        Returns:
            True if logged successfully
        """
        if confidence_scores is None:
            confidence_scores = [d.get("confidence", 0.0) for d in detections]
        
        prediction = PredictionResult(
            image_id=image_id,
            timestamp=time.time(),
            model_version=model_version,
            model_name=model_name,
            inference_time_ms=inference_time_ms,
            detections=detections,
            defect_detected=defect_detected,
            confidence_scores=confidence_scores,
            processing_notes=processing_notes,
        )
        
        return await self.client.log_prediction(prediction)


async def example_usage():
    """Example usage of AsyncLoggingClient"""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Initialize client
    async with AsyncLoggingClient(
        api_endpoint="http://logging-service:8001/log",
        batch_size=32,
        batch_timeout_seconds=10,
        edge_device_id="edge-device-01",
        buffer_file="/tmp/prediction_buffer.jsonl",
    ) as client:
        
        logger_wrapper = BatchedLogger(client)
        
        # Simulate inference predictions
        for i in range(100):
            detections = [
                {
                    "class": "defect",
                    "confidence": 0.92 + (i % 5) * 0.01,
                    "bbox": [100, 100, 200, 200],
                },
            ]
            
            await logger_wrapper.log_detection(
                image_id=f"image_{i:06d}",
                model_version="v1.0",
                model_name="yolov8-defect",
                inference_time_ms=45.2 + (i % 10) * 2,
                detections=detections,
                defect_detected=True,
                processing_notes=f"Batch {i // 32}",
            )
            
            # Simulate processing delay
            if i % 10 == 0:
                print(f"Logged {i} predictions, stats: {client.get_stats()}")
            
            await asyncio.sleep(0.1)
        
        # Wait for final batch to be sent
        await asyncio.sleep(15)
        
        print(f"Final stats: {client.get_stats()}")


if __name__ == "__main__":
    asyncio.run(example_usage())
