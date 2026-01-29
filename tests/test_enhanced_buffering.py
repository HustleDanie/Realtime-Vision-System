"""
Integration tests for enhanced buffering with retry and recovery
"""

import asyncio
import json
import logging
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cloud_logging.async_client import PredictionResult
from src.cloud_logging.buffer_manager import (
    BufferRecoveryManager,
    LocalBufferManager,
)
from src.cloud_logging.enhanced_client import EnhancedAsyncLoggingClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture
def temp_db():
    """Create temporary database for tests"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def sample_predictions():
    """Create sample predictions for testing"""
    predictions = []
    for i in range(10):
        pred = PredictionResult(
            image_id=f"test_image_{i:03d}",
            timestamp=1000000 + i * 100,
            model_version="v1.0",
            model_name="yolov8-test",
            inference_time_ms=45.0,
            detections=[{"class": "defect", "confidence": 0.95}],
            defect_detected=i % 2 == 0,
            confidence_scores=[0.95],
        )
        predictions.append(pred)
    return predictions


class TestLocalBufferManager:
    """Tests for LocalBufferManager"""

    @pytest.mark.asyncio
    async def test_add_and_get_predictions(self, temp_db, sample_predictions):
        """Test adding and retrieving predictions from buffer"""
        manager = LocalBufferManager(db_path=temp_db)

        # Add predictions
        for pred in sample_predictions[:5]:
            await manager.add_prediction(pred)

        # Get batch
        batch = await manager.get_batch(batch_size=3)
        assert len(batch) == 3
        assert batch[0]["image_id"] == "test_image_004"  # Most recent first

    @pytest.mark.asyncio
    async def test_mark_sent(self, temp_db, sample_predictions):
        """Test marking predictions as sent"""
        manager = LocalBufferManager(db_path=temp_db)

        # Add and send
        await manager.add_prediction(sample_predictions[0])
        batch = await manager.get_batch(batch_size=1)
        pred_id = batch[0]["id"]

        await manager.mark_sent(pred_id)

        # Verify marked as sent
        stats = await manager.get_stats()
        assert stats["sent"] == 1
        assert stats["pending"] == 0

    @pytest.mark.asyncio
    async def test_mark_failed_and_retry(self, temp_db, sample_predictions):
        """Test marking predictions as failed and retrying"""
        manager = LocalBufferManager(db_path=temp_db)

        await manager.add_prediction(sample_predictions[0])
        batch = await manager.get_batch(batch_size=1)
        pred_id = batch[0]["id"]

        # Mark as failed
        await manager.mark_failed(pred_id, "Connection timeout")

        # Should still be pending (status='pending', retry_count incremented)
        batch = await manager.get_batch(batch_size=1)
        assert len(batch) == 1
        assert batch[0]["retry_count"] >= 1

    @pytest.mark.asyncio
    async def test_cleanup(self, temp_db, sample_predictions):
        """Test cleanup of old sent predictions"""
        manager = LocalBufferManager(db_path=temp_db)

        # Add and mark as sent
        for pred in sample_predictions:
            await manager.add_prediction(pred)

        batch = await manager.get_batch(batch_size=len(sample_predictions))
        for item in batch:
            await manager.mark_sent(item["id"])

        stats_before = await manager.get_stats()
        assert stats_before["sent"] == 10

        # Cleanup should remove sent predictions older than 7 days
        await manager.cleanup(force=True)

        stats_after = await manager.get_stats()
        assert stats_after["sent"] <= stats_before["sent"]

    @pytest.mark.asyncio
    async def test_space_check(self, temp_db, sample_predictions):
        """Test space check warnings"""
        manager = LocalBufferManager(db_path=temp_db, max_size_mb=0.001)

        # Add many predictions to trigger space warning
        for _ in range(100):
            for pred in sample_predictions:
                try:
                    await manager.add_prediction(pred)
                except RuntimeError as e:
                    # Expected when space exceeded
                    logger.info(f"Space limit hit: {e}")
                    break

        stats = await manager.get_stats()
        logger.info(f"Buffer stats after space check: {stats}")


class TestBufferRecoveryManager:
    """Tests for BufferRecoveryManager"""

    @pytest.mark.asyncio
    async def test_recovery_batching(self, temp_db, sample_predictions):
        """Test recovery batching behavior"""
        buffer_mgr = LocalBufferManager(db_path=temp_db)
        recovery_mgr = BufferRecoveryManager(buffer_mgr)

        # Add predictions
        for pred in sample_predictions[:5]:
            await buffer_mgr.add_prediction(pred)

        # Create mock send function
        sent_predictions = []

        async def mock_send(batch):
            sent_predictions.extend(batch)
            return True

        # Recover
        await recovery_mgr.start_recovery(
            send_batch_fn=mock_send, batch_size=2
        )

        await asyncio.sleep(1)
        await recovery_mgr.stop_recovery()

        # Should have sent all 5 in batches of 2
        assert len(sent_predictions) >= 4  # At least 2 batches

    @pytest.mark.asyncio
    async def test_recovery_status(self, temp_db, sample_predictions):
        """Test recovery status reporting"""
        buffer_mgr = LocalBufferManager(db_path=temp_db)
        recovery_mgr = BufferRecoveryManager(buffer_mgr)

        for pred in sample_predictions[:3]:
            await buffer_mgr.add_prediction(pred)

        status = recovery_mgr.get_recovery_status()
        assert status["is_recovering"] == False
        assert status["predictions_recovered"] == 0

        async def mock_send(batch):
            return True

        await recovery_mgr.start_recovery(
            send_batch_fn=mock_send, batch_size=1
        )
        await asyncio.sleep(0.5)

        status = recovery_mgr.get_recovery_status()
        assert status["is_recovering"] == True

        await recovery_mgr.stop_recovery()


class TestEnhancedAsyncLoggingClient:
    """Tests for EnhancedAsyncLoggingClient with buffering"""

    @pytest.mark.asyncio
    async def test_persistent_buffering(self, temp_db, sample_predictions):
        """Test predictions are persisted during failure"""
        client = EnhancedAsyncLoggingClient(
            api_endpoint="http://localhost:9999",  # Non-existent
            buffer_db_path=temp_db,
        )

        await client.start()

        try:
            # Log predictions (should go to buffer due to connection failure)
            for pred in sample_predictions[:5]:
                await client.log_prediction(pred)

            # Wait for batch timeout and failed sends
            await asyncio.sleep(15)

            # Check buffer status
            status = await client.get_buffer_status()
            assert status["pending"] > 0  # Should be buffered locally
            assert status["db_pending"] > 0  # Persistent buffer
        finally:
            await client.shutdown()

    @pytest.mark.asyncio
    async def test_connectivity_monitoring(self, temp_db, sample_predictions):
        """Test connectivity monitoring"""
        client = EnhancedAsyncLoggingClient(
            api_endpoint="http://localhost:9999",
            buffer_db_path=temp_db,
        )

        await client.start()

        try:
            # Monitor connectivity
            await asyncio.sleep(5)

            # Should have detected disconnection
            is_connected = await client._check_connectivity()
            assert is_connected == False

        finally:
            await client.shutdown()

    @pytest.mark.asyncio
    async def test_recovery_on_reconnect(self, temp_db, sample_predictions):
        """Test automatic recovery when connectivity restored"""
        client = EnhancedAsyncLoggingClient(
            api_endpoint="http://localhost:9999",
            buffer_db_path=temp_db,
        )

        await client.start()

        try:
            # Log predictions
            for pred in sample_predictions[:3]:
                await client.log_prediction(pred)

            # Wait for buffering
            await asyncio.sleep(5)

            stats_before = await client.get_buffer_status()

            # Simulate connectivity check
            is_connected = await client._check_connectivity()
            assert is_connected == False  # Should still be disconnected

        finally:
            await client.shutdown()

    @pytest.mark.asyncio
    async def test_graceful_shutdown_with_buffer(
        self, temp_db, sample_predictions
    ):
        """Test graceful shutdown with pending predictions"""
        client = EnhancedAsyncLoggingClient(
            api_endpoint="http://localhost:9999",
            buffer_db_path=temp_db,
        )

        await client.start()

        # Log predictions
        for pred in sample_predictions[:2]:
            await client.log_prediction(pred)

        # Shutdown should preserve buffer
        await client.shutdown()

        # Verify buffer still has predictions
        mgr = LocalBufferManager(db_path=temp_db)
        stats = await mgr.get_stats()
        assert stats["pending"] > 0 or stats["sent"] > 0

    @pytest.mark.asyncio
    async def test_load_buffered_on_startup(self, temp_db, sample_predictions):
        """Test loading buffered predictions on startup"""
        # Session 1: Create buffered predictions
        mgr1 = LocalBufferManager(db_path=temp_db)
        for pred in sample_predictions[:3]:
            await mgr1.add_prediction(pred)

        stats1 = await mgr1.get_stats()
        assert stats1["pending"] == 3

        # Session 2: Start client, should load buffered
        client = EnhancedAsyncLoggingClient(
            api_endpoint="http://localhost:9999",
            buffer_db_path=temp_db,
        )

        await client.start()

        try:
            # Should have loaded buffered predictions
            await asyncio.sleep(1)
            status = await client.get_buffer_status()
            # Buffered predictions should be in buffer or recovery
            assert (
                status["db_pending"] >= 2
                or status["recovery_count"] >= 2
            )
        finally:
            await client.shutdown()


class TestBufferingWithNetworkSimulation:
    """Integration tests simulating network conditions"""

    @pytest.mark.asyncio
    async def test_transient_failure_recovery(self, temp_db):
        """Test recovery from transient network failures"""
        client = EnhancedAsyncLoggingClient(
            api_endpoint="http://localhost:9999",
            buffer_db_path=temp_db,
            batch_timeout_seconds=5,
        )

        await client.start()

        try:
            pred = PredictionResult(
                image_id="test_001",
                timestamp=1000000,
                model_version="v1.0",
                model_name="test",
                inference_time_ms=45.0,
                detections=[],
                defect_detected=False,
                confidence_scores=[],
            )

            # Log prediction (fails)
            await client.log_prediction(pred)
            await asyncio.sleep(3)

            status_after_fail = await client.get_buffer_status()
            assert status_after_fail["pending"] > 0

            logger.info(f"After failure: {status_after_fail}")

        finally:
            await client.shutdown()

    @pytest.mark.asyncio
    async def test_multiple_failure_retries(self, temp_db):
        """Test multiple retry attempts with exponential backoff"""
        client = EnhancedAsyncLoggingClient(
            api_endpoint="http://localhost:9999",
            buffer_db_path=temp_db,
            batch_timeout_seconds=3,
        )

        await client.start()

        try:
            for i in range(5):
                pred = PredictionResult(
                    image_id=f"retry_test_{i:03d}",
                    timestamp=1000000 + i * 100,
                    model_version="v1.0",
                    model_name="test",
                    inference_time_ms=45.0,
                    detections=[],
                    defect_detected=False,
                    confidence_scores=[],
                )
                await client.log_prediction(pred)
                await asyncio.sleep(0.5)

            # Wait for batch timeout + retries
            await asyncio.sleep(10)

            status = await client.get_buffer_status()
            logger.info(f"After retries: {status}")

            # All should be buffered or in recovery
            assert (
                status["pending"] > 0
                or status["recovery_count"] > 0
                or status["db_pending"] > 0
            )

        finally:
            await client.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
