"""
Example: Running edge inference with async cloud logging
"""

import asyncio
import logging
from pathlib import Path
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

from src.cloud_logging.edge_integration import EdgeInferenceWithCloudLogging
from src.cloud_logging.config import get_config


async def main():
    """
    Main example: Process images from edge with async cloud logging
    """
    
    # Load configuration
    config = get_config()
    logger.info(f"Configuration: {config}")
    
    if not config.enabled:
        logger.warning("Cloud logging is disabled")
        return
    
    # Create service
    service = EdgeInferenceWithCloudLogging(
        yolo_model_path="yolov8n.pt",
        cloud_api_endpoint=config.api_endpoint,
        cloud_api_key=config.api_key,
        batch_size=config.batch_size,
        batch_timeout_seconds=config.batch_timeout_seconds,
        buffer_file=config.buffer_file,
        edge_device_id=config.edge_device_id,
    )
    
    await service.start()
    
    try:
        logger.info("Edge inference service started")
        
        # Process images (example: from a video stream or folder)
        sample_images = [
            "sample_images/frame_001.jpg",
            "sample_images/frame_002.jpg",
            "sample_images/frame_003.jpg",
        ]
        
        processed_count = 0
        
        for image_path in sample_images:
            try:
                # Process image asynchronously (logging happens in background)
                result = await service.process_image_async(image_path)
                
                logger.info(
                    f"Processed {image_path}: "
                    f"{len(result['detections'])} detections, "
                    f"inference: {result['inference_time_ms']:.2f}ms"
                )
                
                processed_count += 1
                
                # Small delay between images
                await asyncio.sleep(0.5)
            
            except FileNotFoundError:
                logger.warning(f"Image not found: {image_path}")
            except Exception as e:
                logger.error(f"Error processing {image_path}: {e}")
        
        logger.info(f"Processed {processed_count} images")
        
        # Wait for final batches to be sent (important!)
        logger.info("Waiting for final batch to be sent...")
        await asyncio.sleep(config.batch_timeout_seconds + 2)
        
        # Print final statistics
        stats = service.get_cloud_logging_stats()
        logger.info(f"Cloud logging stats: {stats}")
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        await service.shutdown()
        logger.info("Service shutdown complete")


async def continuous_monitoring():
    """
    Example: Continuous monitoring from video stream with buffering
    """
    
    config = get_config()
    
    service = EdgeInferenceWithCloudLogging(
        cloud_api_endpoint=config.api_endpoint,
        cloud_api_key=config.api_key,
        batch_size=config.batch_size,
        batch_timeout_seconds=config.batch_timeout_seconds,
        buffer_file=config.buffer_file,
        edge_device_id=config.edge_device_id,
    )
    
    await service.start()
    
    try:
        # Simulate continuous video stream
        frame_count = 0
        
        while True:
            # Get frame from camera/stream
            # frame = capture_frame_from_camera()
            
            # For demo, just increment counter
            frame_count += 1
            
            # Process asynchronously (non-blocking)
            # result = await service.process_image_async(
            #     image_path=frame_path,
            #     image_id=f"frame_{frame_count:06d}",
            # )
            
            # Simulate processing delay
            await asyncio.sleep(0.033)  # ~30 FPS
            
            if frame_count % 100 == 0:
                stats = service.get_cloud_logging_stats()
                logger.info(f"Processed {frame_count} frames, stats: {stats}")
            
            if frame_count >= 1000:
                break
    
    except KeyboardInterrupt:
        logger.info("Stream monitoring stopped")
    finally:
        await service.shutdown()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        asyncio.run(continuous_monitoring())
    else:
        asyncio.run(main())
