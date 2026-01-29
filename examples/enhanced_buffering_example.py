"""
Example: Edge inference with enhanced buffering and recovery
"""

import asyncio
import logging
from pathlib import Path
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

from src.cloud_logging.enhanced_client import EnhancedAsyncLoggingClient
from src.cloud_logging.buffer_monitor import BufferMonitor


async def example_with_buffering():
    """
    Example: Process images with persistent local buffering
    
    Simulates network failure and recovery
    """
    
    # Create client with persistent buffering
    client = EnhancedAsyncLoggingClient(
        api_endpoint="http://logging-service:8001/log",
        batch_size=32,
        batch_timeout_seconds=10,
        max_buffer_size_mb=500,
        cleanup_after_days=7,
        edge_device_id="factory-camera-01",
    )
    
    await client.start()
    
    # Create monitor
    monitor = BufferMonitor(client.buffer_manager, client)
    await monitor.start(interval_seconds=10)
    
    try:
        logger.info("Starting image processing with buffering...")
        
        from src.cloud_logging.async_client import PredictionResult
        import time
        
        # Process simulated images
        for i in range(100):
            prediction = PredictionResult(
                image_id=f"image_{i:06d}",
                timestamp=time.time(),
                model_version="v1.0",
                model_name="yolov8-defect",
                inference_time_ms=45.2 + (i % 5) * 2,
                detections=[
                    {
                        "class": "defect",
                        "confidence": 0.92 + (i % 3) * 0.02,
                        "bbox": [100, 100, 200, 200],
                    }
                ],
                defect_detected=i % 3 == 0,  # 33% defect rate
                confidence_scores=[0.92 + (i % 3) * 0.02],
            )
            
            # Log prediction (will be buffered if cloud unavailable)
            await client.log_prediction(prediction)
            
            # Every 30 predictions, print status
            if i % 30 == 0:
                await monitor.print_status()
            
            await asyncio.sleep(0.1)
        
        # Wait for final batch
        logger.info("Waiting for final batch...")
        await asyncio.sleep(15)
        
        # Print final status
        await monitor.print_status()
    
    finally:
        await monitor.stop()
        await client.shutdown()


async def example_with_network_failure():
    """
    Example: Simulate network failure and recovery
    """
    
    client = EnhancedAsyncLoggingClient(
        api_endpoint="http://localhost:8001/log",  # Local service
        batch_size=32,
        batch_timeout_seconds=5,
        edge_device_id="factory-camera-02",
    )
    
    await client.start()
    monitor = BufferMonitor(client.buffer_manager, client)
    await monitor.start(interval_seconds=5)
    
    try:
        from src.cloud_logging.async_client import PredictionResult
        import time
        
        logger.info("Phase 1: Cloud available (5 predictions)")
        
        # Send predictions while cloud is available
        for i in range(5):
            prediction = PredictionResult(
                image_id=f"phase1_{i:03d}",
                timestamp=time.time(),
                model_version="v1.0",
                model_name="yolov8",
                inference_time_ms=45.0,
                detections=[{"class": "defect", "confidence": 0.95}],
                defect_detected=True,
                confidence_scores=[0.95],
            )
            await client.log_prediction(prediction)
            await asyncio.sleep(0.5)
        
        await asyncio.sleep(8)
        logger.info("Batch sent successfully")
        
        # Simulate network failure
        logger.info("Phase 2: Network failure (5 predictions buffered locally)")
        
        # Buffer some predictions while network is "down"
        for i in range(5):
            prediction = PredictionResult(
                image_id=f"phase2_{i:03d}",
                timestamp=time.time(),
                model_version="v1.0",
                model_name="yolov8",
                inference_time_ms=45.0,
                detections=[{"class": "defect", "confidence": 0.95}],
                defect_detected=True,
                confidence_scores=[0.95],
            )
            await client.log_prediction(prediction)
            await asyncio.sleep(0.5)
        
        await asyncio.sleep(8)
        
        # These should be in the local buffer
        status = await client.get_buffer_status()
        logger.info(f"Buffer status: pending={status['pending']}, sent={status['sent']}")
        
        logger.info("Phase 3: Network restored (recovery in progress)")
        
        # These should be recovered
        await asyncio.sleep(10)
        
        status = await client.get_buffer_status()
        logger.info(f"Final buffer status: {status}")
        
        await monitor.print_status()
    
    finally:
        await monitor.stop()
        await client.shutdown()


async def example_recovery_mode():
    """
    Example: Start with buffered predictions from previous session
    """
    
    logger.info("Simulating restart with buffered predictions...")
    
    # First session: buffer some predictions
    logger.info("Session 1: Creating buffered predictions")
    
    from src.cloud_logging.buffer_manager import LocalBufferManager
    from src.cloud_logging.async_client import PredictionResult
    import time
    
    buffer_db = "/tmp/test_buffer.db"
    buffer_mgr = LocalBufferManager(db_path=buffer_db)
    
    for i in range(10):
        pred = PredictionResult(
            image_id=f"buffered_{i:03d}",
            timestamp=time.time(),
            model_version="v1.0",
            model_name="yolov8",
            inference_time_ms=45.0,
            detections=[{"class": "defect", "confidence": 0.95}],
            defect_detected=True,
            confidence_scores=[0.95],
        )
        await buffer_mgr.add_prediction(pred)
    
    stats = await buffer_mgr.get_stats()
    logger.info(f"Session 1 complete. Buffer stats: {stats}")
    
    # Second session: load and recover buffered predictions
    logger.info("\nSession 2: Loading and recovering buffered predictions")
    
    client = EnhancedAsyncLoggingClient(
        api_endpoint="http://logging-service:8001/log",
        buffer_db_path=buffer_db,
    )
    
    await client.start()
    
    # Should automatically load and queue buffered predictions
    await asyncio.sleep(10)
    
    status = await client.get_buffer_status()
    logger.info(f"Session 2 recovery status: {status}")
    
    await client.shutdown()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "buffering":
            asyncio.run(example_with_buffering())
        elif sys.argv[1] == "network-failure":
            asyncio.run(example_with_network_failure())
        elif sys.argv[1] == "recovery":
            asyncio.run(example_recovery_mode())
    else:
        print("Usage:")
        print("  python examples/enhanced_buffering_example.py buffering")
        print("  python examples/enhanced_buffering_example.py network-failure")
        print("  python examples/enhanced_buffering_example.py recovery")
