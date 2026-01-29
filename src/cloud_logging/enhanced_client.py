"""
Enhanced AsyncLoggingClient with advanced retry and buffering
"""

import asyncio
import json
import logging
from typing import Optional, List
import aiohttp

from src.cloud_logging.async_client import AsyncLoggingClient as BaseAsyncLoggingClient
from src.cloud_logging.async_client import PredictionResult
from src.cloud_logging.buffer_manager import LocalBufferManager, BufferRecoveryManager

logger = logging.getLogger(__name__)


class EnhancedAsyncLoggingClient(BaseAsyncLoggingClient):
    """
    Enhanced AsyncLoggingClient with persistent local buffering and recovery
    
    Features:
    - SQLite-based persistent buffer
    - Automatic retry of buffered predictions
    - Network failure detection and recovery
    - Buffer statistics and monitoring
    """
    
    def __init__(
        self,
        api_endpoint: str,
        api_key: Optional[str] = None,
        batch_size: int = 32,
        batch_timeout_seconds: int = 10,
        max_retries: int = 3,
        retry_backoff_multiplier: float = 2.0,
        buffer_db_path: str = "/app/data/prediction_buffer.db",
        max_buffer_size_mb: int = 500,
        cleanup_after_days: int = 7,
        timeout_seconds: int = 30,
        edge_device_id: Optional[str] = None,
    ):
        """
        Initialize EnhancedAsyncLoggingClient
        
        Args:
            api_endpoint: Cloud API endpoint
            api_key: Optional API key
            batch_size: Predictions per batch
            batch_timeout_seconds: Max wait before sending batch
            max_retries: Max retry attempts
            retry_backoff_multiplier: Backoff multiplier
            buffer_db_path: Path to local SQLite buffer database
            max_buffer_size_mb: Max buffer size before cleanup
            cleanup_after_days: Delete sent predictions after N days
            timeout_seconds: Request timeout
            edge_device_id: Edge device identifier
        """
        super().__init__(
            api_endpoint=api_endpoint,
            api_key=api_key,
            batch_size=batch_size,
            batch_timeout_seconds=batch_timeout_seconds,
            max_retries=max_retries,
            retry_backoff_multiplier=retry_backoff_multiplier,
            buffer_file=None,  # Use SQLite instead of JSONL
            timeout_seconds=timeout_seconds,
            edge_device_id=edge_device_id,
        )
        
        # Initialize persistent buffer manager
        self.buffer_manager = LocalBufferManager(
            db_path=buffer_db_path,
            max_buffer_size_mb=max_buffer_size_mb,
            cleanup_after_days=cleanup_after_days,
        )
        
        # Initialize recovery manager
        self.recovery_manager = BufferRecoveryManager(
            buffer_manager=self.buffer_manager,
            send_function=self._send_predictions,
        )
        
        self._connectivity_monitor_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the client and recovery mechanisms"""
        await super().start()
        
        # Load buffered predictions from persistent storage
        await self._load_buffered_from_persistent()
        
        # Start connectivity monitoring
        self._connectivity_monitor_task = asyncio.create_task(
            self._connectivity_monitor()
        )
        
        logger.info("EnhancedAsyncLoggingClient started with persistent buffering")
    
    async def shutdown(self):
        """Gracefully shutdown"""
        # Stop connectivity monitor
        if self._connectivity_monitor_task:
            self._connectivity_monitor_task.cancel()
            try:
                await self._connectivity_monitor_task
            except asyncio.CancelledError:
                pass
        
        # Stop recovery
        await self.recovery_manager.stop_recovery()
        
        # Call parent shutdown
        await super().shutdown()
        
        logger.info("EnhancedAsyncLoggingClient shutdown complete")
    
    async def log_prediction(self, prediction: PredictionResult) -> bool:
        """
        Log prediction with automatic persistent buffering
        
        Args:
            prediction: PredictionResult to log
            
        Returns:
            True if queued successfully
        """
        if prediction.edge_device_id is None:
            prediction.edge_device_id = self.edge_device_id
        
        # Always buffer to persistent storage (in addition to in-memory batch)
        await self.buffer_manager.add_prediction(prediction)
        
        # Also add to in-memory batch for normal processing
        async with self._batch_lock:
            self._batch.append(prediction)
            
            # Send if batch is full
            if len(self._batch) >= self.batch_size:
                await self._flush_batch()
        
        return True
    
    async def _send_predictions(
        self,
        predictions: List[PredictionResult],
        retry_count: int = 0,
    ) -> bool:
        """
        Send predictions with enhanced error handling
        
        On failure, predictions are preserved in persistent buffer for later retry
        
        Args:
            predictions: List of predictions
            retry_count: Current retry attempt
            
        Returns:
            True if successful
        """
        if not predictions:
            return True
        
        payload = {
            "predictions": [p.to_dict() for p in predictions],
            "batch_size": len(predictions),
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            "edge_device_id": self.edge_device_id,
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "EdgeInferenceService/2.0",
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
            logger.warning(f"Request timeout to {self.api_endpoint}")
            return self._handle_send_failure(predictions, "timeout", retry_count)
        
        except aiohttp.ClientConnectorError as e:
            logger.warning(f"Connection error: {e}")
            return self._handle_send_failure(predictions, "connection_error", retry_count)
        
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            return self._handle_send_failure(predictions, "http_error", retry_count)
        
        except Exception as e:
            logger.error(f"Unexpected error sending predictions: {e}")
            return self._handle_send_failure(predictions, "unexpected_error", retry_count)
    
    def _handle_send_failure(
        self,
        predictions: List[PredictionResult],
        error_type: str,
        retry_count: int,
    ) -> bool:
        """
        Handle send failure with retry logic
        
        Args:
            predictions: Predictions that failed to send
            error_type: Type of error
            retry_count: Current retry attempt
            
        Returns:
            True if retry scheduled, False if max retries exhausted
        """
        if retry_count < self.max_retries:
            wait_time = (self.retry_backoff_multiplier ** retry_count)
            logger.info(
                f"Retrying in {wait_time}s ({error_type}, "
                f"attempt {retry_count + 1}/{self.max_retries})"
            )
            self._stats["retried"] += len(predictions)
            
            # Schedule retry asynchronously
            asyncio.create_task(
                self._retry_send(predictions, retry_count + 1, wait_time)
            )
            return False
        else:
            logger.error(
                f"Failed to send {len(predictions)} predictions after "
                f"{self.max_retries} retries ({error_type}). "
                f"Predictions persisted in local buffer."
            )
            self._stats["failed"] += len(predictions)
            return False
    
    async def _retry_send(
        self,
        predictions: List[PredictionResult],
        retry_count: int,
        wait_time: float,
    ):
        """Retry sending after delay"""
        await asyncio.sleep(wait_time)
        await self._send_predictions(predictions, retry_count)
    
    async def _connectivity_monitor(self):
        """
        Background task that monitors cloud connectivity
        
        - Detects when connection is restored
        - Triggers recovery of buffered predictions
        """
        last_known_status = True  # Assume initially connected
        
        while not self._shutdown:
            try:
                # Try to reach cloud API
                connectivity_ok = await self._check_connectivity()
                
                # On status change, trigger recovery if reconnected
                if not last_known_status and connectivity_ok:
                    logger.info("Cloud connectivity restored, starting recovery")
                    await self.recovery_manager.start_recovery(self.batch_size)
                elif last_known_status and not connectivity_ok:
                    logger.warning("Cloud connectivity lost, buffering to persistent storage")
                    await self.recovery_manager.stop_recovery()
                
                last_known_status = connectivity_ok
                
                # Check buffer stats periodically
                if (await self.buffer_manager.get_stats())["pending"] > 0:
                    stats = await self.buffer_manager.get_stats()
                    logger.debug(f"Buffer stats: {stats}")
                    
                    # Cleanup if needed
                    await self.buffer_manager.cleanup()
                
                await asyncio.sleep(30)  # Check every 30 seconds
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in connectivity monitor: {e}")
                await asyncio.sleep(30)
    
    async def _check_connectivity(self) -> bool:
        """
        Check if cloud API is reachable
        
        Returns:
            True if reachable, False otherwise
        """
        try:
            async with self._session.head(
                self.api_endpoint,
                timeout=aiohttp.ClientTimeout(total=5),
                ssl=False,
            ) as response:
                return response.status < 500
        except Exception:
            return False
    
    async def _load_buffered_from_persistent(self):
        """Load buffered predictions from persistent storage and queue them"""
        batch = await self.buffer_manager.get_batch(self.batch_size)
        
        if batch:
            logger.info(f"Loaded {len(batch)} buffered predictions from persistent storage")
            
            # Queue for sending
            for pred_id, pred in batch:
                async with self._batch_lock:
                    self._batch.append(pred)
    
    async def get_buffer_status(self) -> dict:
        """Get detailed buffer status"""
        stats = await self.buffer_manager.get_stats()
        recovery_status = await self.recovery_manager.get_recovery_status()
        
        return {
            **stats,
            **recovery_status,
        }
