"""
Unit tests for async cloud logging client
"""

import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.cloud_logging.async_client import (
    PredictionResult,
    AsyncLoggingClient,
    BatchedLogger,
)


@pytest.fixture
def prediction():
    """Create a test prediction"""
    return PredictionResult(
        image_id="test_image_001",
        timestamp=1234567890.0,
        model_version="v1.0",
        model_name="yolov8-test",
        inference_time_ms=45.2,
        detections=[
            {
                "class": "defect",
                "confidence": 0.95,
                "bbox": [100, 100, 200, 200],
            }
        ],
        defect_detected=True,
        confidence_scores=[0.95],
        processing_notes="test",
    )


@pytest.fixture
def client():
    """Create a test client"""
    return AsyncLoggingClient(
        api_endpoint="http://localhost:8001/log",
        batch_size=2,
        batch_timeout_seconds=5,
    )


@pytest.mark.asyncio
async def test_prediction_to_dict(prediction):
    """Test PredictionResult serialization"""
    data = prediction.to_dict()
    
    assert data["image_id"] == "test_image_001"
    assert data["model_version"] == "v1.0"
    assert data["defect_detected"] is True
    assert len(data["detections"]) == 1


@pytest.mark.asyncio
async def test_client_initialization(client):
    """Test client initialization"""
    assert client.api_endpoint == "http://localhost:8001/log"
    assert client.batch_size == 2
    assert len(client._batch) == 0


@pytest.mark.asyncio
async def test_start_shutdown(client):
    """Test client start and shutdown"""
    await client.start()
    assert client._session is not None
    assert client._background_task is not None
    
    await client.shutdown()
    assert client._session.closed


@pytest.mark.asyncio
async def test_log_prediction(client, prediction):
    """Test logging a single prediction"""
    await client.start()
    
    result = await client.log_prediction(prediction)
    assert result is True
    assert len(client._batch) == 1
    assert client._batch[0].image_id == "test_image_001"
    
    await client.shutdown()


@pytest.mark.asyncio
async def test_batch_flush_on_size(client, prediction):
    """Test batch flush when size is reached"""
    await client.start()
    
    # Mock the send method
    client._send_predictions = AsyncMock(return_value=True)
    
    # Add predictions until batch size reached
    await client.log_prediction(prediction)
    assert len(client._batch) == 1
    
    await client.log_prediction(prediction)
    # Batch should be flushed automatically when size reaches 2
    assert client._send_predictions.called
    
    await client.shutdown()


@pytest.mark.asyncio
async def test_send_predictions_success(client, prediction):
    """Test successful prediction sending"""
    await client.start()
    
    predictions = [prediction, prediction]
    
    with patch.object(client._session, "post") as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_post.return_value.__aenter__.return_value = mock_response
        
        result = await client._send_predictions(predictions)
        
        assert result is True
        assert client._stats["sent"] == 2
    
    await client.shutdown()


@pytest.mark.asyncio
async def test_send_predictions_failure(client, prediction):
    """Test failed prediction sending"""
    await client.start()
    
    predictions = [prediction]
    
    with patch.object(client._session, "post") as mock_post:
        mock_post.side_effect = Exception("Connection failed")
        
        result = await client._send_predictions(predictions)
        
        assert result is False
        assert client._stats["failed"] == 1
    
    await client.shutdown()


@pytest.mark.asyncio
async def test_buffer_predictions(client, prediction, tmp_path):
    """Test buffering predictions to disk"""
    buffer_file = tmp_path / "buffer.jsonl"
    client.buffer_file = buffer_file
    
    predictions = [prediction, prediction]
    await client._buffer_predictions(predictions)
    
    assert buffer_file.exists()
    
    # Verify content
    lines = buffer_file.read_text().strip().split("\n")
    assert len(lines) == 2
    
    for line in lines:
        data = json.loads(line)
        assert data["image_id"] == "test_image_001"


@pytest.mark.asyncio
async def test_load_buffered_predictions(client, prediction, tmp_path):
    """Test loading buffered predictions from disk"""
    buffer_file = tmp_path / "buffer.jsonl"
    client.buffer_file = buffer_file
    
    # Create buffer file
    with open(buffer_file, "w") as f:
        f.write(json.dumps(prediction.to_dict()) + "\n")
    
    # Mock the send method
    client._send_predictions = AsyncMock(return_value=True)
    
    # Load and send
    await client._load_buffered_predictions()
    
    assert client._send_predictions.called
    assert not buffer_file.exists()  # Buffer should be cleared


@pytest.mark.asyncio
async def test_batched_logger(client, tmp_path):
    """Test BatchedLogger wrapper"""
    await client.start()
    
    logger = BatchedLogger(client)
    
    result = await logger.log_detection(
        image_id="test_001",
        model_version="v1.0",
        model_name="yolov8",
        inference_time_ms=45.0,
        detections=[{"class": "defect", "confidence": 0.95}],
        defect_detected=True,
    )
    
    assert result is True
    assert len(client._batch) == 1
    
    await client.shutdown()


@pytest.mark.asyncio
async def test_get_stats(client, prediction):
    """Test statistics tracking"""
    await client.start()
    
    # Mock send method
    client._send_predictions = AsyncMock(return_value=True)
    
    await client.log_prediction(prediction)
    await client.log_prediction(prediction)
    
    # Trigger flush
    await client._flush_batch()
    
    stats = client.get_stats()
    assert stats["sent"] == 2
    assert stats["failed"] == 0
    
    await client.shutdown()


@pytest.mark.asyncio
async def test_edge_device_id_assignment(client, prediction):
    """Test edge device ID assignment"""
    client.edge_device_id = "edge-device-01"
    await client.start()
    
    assert prediction.edge_device_id is None
    
    await client.log_prediction(prediction)
    
    # Edge device ID should be assigned
    assert client._batch[0].edge_device_id == "edge-device-01"
    
    await client.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
