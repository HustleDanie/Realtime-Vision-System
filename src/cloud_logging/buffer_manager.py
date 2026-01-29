"""
Advanced local buffering and persistence for edge predictions

Handles:
- Persistent buffer to disk (SQLite-based)
- Buffer recovery on service restart
- Priority-based buffer management (recent predictions sent first)
- Disk space management (configurable max size)
- Buffer statistics and monitoring
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import asdict
import asyncio

from src.cloud_logging.async_client import PredictionResult

logger = logging.getLogger(__name__)


class LocalBufferManager:
    """
    Manages local persistent buffer for predictions
    
    Uses SQLite for reliable storage and efficient queries:
    - Insert new predictions
    - Retrieve batches for retry
    - Mark as successfully sent
    - Clean up old/sent predictions
    - Monitor buffer size and status
    """
    
    def __init__(
        self,
        db_path: str = "/app/data/prediction_buffer.db",
        max_buffer_size_mb: int = 500,
        cleanup_after_days: int = 7,
    ):
        """
        Initialize LocalBufferManager
        
        Args:
            db_path: Path to SQLite database
            max_buffer_size_mb: Maximum buffer size in MB before cleanup
            cleanup_after_days: Delete successfully sent predictions after N days
        """
        self.db_path = Path(db_path)
        self.max_buffer_size_mb = max_buffer_size_mb
        self.cleanup_after_days = cleanup_after_days
        
        # Create parent directory
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        logger.info(f"LocalBufferManager initialized: {db_path}")
    
    def _init_database(self):
        """Initialize SQLite database schema"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Create buffer table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prediction_buffer (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_data TEXT NOT NULL,
                    image_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    buffered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent_at TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    retry_count INTEGER DEFAULT 0,
                    last_error TEXT,
                    
                    INDEX idx_status (status),
                    INDEX idx_image_id (image_id),
                    INDEX idx_timestamp (timestamp),
                    INDEX idx_buffered_at (buffered_at)
                )
            """)
            
            # Create metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS buffer_metadata (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    total_buffered INTEGER DEFAULT 0,
                    total_sent INTEGER DEFAULT 0,
                    total_failed INTEGER DEFAULT 0,
                    last_cleanup TIMESTAMP
                )
            """)
            
            # Insert default metadata
            cursor.execute("""
                INSERT OR IGNORE INTO buffer_metadata (id)
                VALUES (1)
            """)
            
            conn.commit()
            conn.close()
            logger.info("Database schema initialized")
        
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def add_prediction(self, prediction: PredictionResult) -> bool:
        """
        Add prediction to local buffer
        
        Args:
            prediction: PredictionResult to buffer
            
        Returns:
            True if successfully buffered, False otherwise
        """
        try:
            prediction_json = json.dumps(asdict(prediction))
            
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO prediction_buffer (
                    prediction_data, image_id, timestamp, status
                ) VALUES (?, ?, ?, ?)
            """, (prediction_json, prediction.image_id, prediction.timestamp, "pending"))
            
            # Update metadata
            cursor.execute("""
                UPDATE buffer_metadata
                SET total_buffered = total_buffered + 1
                WHERE id = 1
            """)
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Buffered prediction: {prediction.image_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to buffer prediction: {e}")
            return False
    
    async def get_batch(self, batch_size: int = 32) -> List[Tuple[int, PredictionResult]]:
        """
        Get batch of pending predictions for retry
        
        Returns most recent pending predictions first (higher priority)
        
        Args:
            batch_size: Number of predictions to retrieve
            
        Returns:
            List of (id, PredictionResult) tuples
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Get recent pending predictions
            cursor.execute("""
                SELECT id, prediction_data FROM prediction_buffer
                WHERE status = 'pending'
                ORDER BY timestamp DESC
                LIMIT ?
            """, (batch_size,))
            
            rows = cursor.fetchall()
            conn.close()
            
            predictions = []
            for row_id, prediction_json in rows:
                try:
                    data = json.loads(prediction_json)
                    pred = PredictionResult(**data)
                    predictions.append((row_id, pred))
                except Exception as e:
                    logger.warning(f"Failed to deserialize prediction {row_id}: {e}")
                    await self.mark_failed(row_id, str(e))
            
            return predictions
        
        except Exception as e:
            logger.error(f"Failed to get batch from buffer: {e}")
            return []
    
    async def mark_sent(self, prediction_id: int) -> bool:
        """
        Mark prediction as successfully sent to cloud
        
        Args:
            prediction_id: Database ID of prediction
            
        Returns:
            True if successful
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE prediction_buffer
                SET status = 'sent', sent_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (prediction_id,))
            
            # Update metadata
            cursor.execute("""
                UPDATE buffer_metadata
                SET total_sent = total_sent + 1
                WHERE id = 1
            """)
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Marked prediction {prediction_id} as sent")
            return True
        
        except Exception as e:
            logger.error(f"Failed to mark prediction as sent: {e}")
            return False
    
    async def mark_failed(self, prediction_id: int, error: str) -> bool:
        """
        Mark prediction as failed with error message
        
        Args:
            prediction_id: Database ID of prediction
            error: Error message
            
        Returns:
            True if successful
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE prediction_buffer
                SET status = 'failed', last_error = ?, retry_count = retry_count + 1
                WHERE id = ?
            """, (error, prediction_id))
            
            # Update metadata
            cursor.execute("""
                UPDATE buffer_metadata
                SET total_failed = total_failed + 1
                WHERE id = 1
            """)
            
            conn.commit()
            conn.close()
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to mark prediction as failed: {e}")
            return False
    
    async def get_stats(self) -> Dict:
        """Get buffer statistics"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Get metadata
            cursor.execute("""
                SELECT total_buffered, total_sent, total_failed
                FROM buffer_metadata WHERE id = 1
            """)
            metadata = cursor.fetchone()
            
            # Count pending
            cursor.execute("""
                SELECT COUNT(*) FROM prediction_buffer WHERE status = 'pending'
            """)
            pending_count = cursor.fetchone()[0]
            
            # Count sent
            cursor.execute("""
                SELECT COUNT(*) FROM prediction_buffer WHERE status = 'sent'
            """)
            sent_count = cursor.fetchone()[0]
            
            # Count failed
            cursor.execute("""
                SELECT COUNT(*) FROM prediction_buffer WHERE status = 'failed'
            """)
            failed_count = cursor.fetchone()[0]
            
            # Get database size
            db_size_mb = self.db_path.stat().st_size / (1024 * 1024)
            
            conn.close()
            
            return {
                "pending": pending_count,
                "sent": sent_count,
                "failed": failed_count,
                "buffer_size_mb": round(db_size_mb, 2),
                "buffer_limit_mb": self.max_buffer_size_mb,
            }
        
        except Exception as e:
            logger.error(f"Failed to get buffer stats: {e}")
            return {
                "pending": 0,
                "sent": 0,
                "failed": 0,
                "buffer_size_mb": 0,
                "buffer_limit_mb": self.max_buffer_size_mb,
            }
    
    async def cleanup(self, force: bool = False) -> Dict:
        """
        Clean up old and successfully sent predictions
        
        Args:
            force: Force cleanup regardless of time
            
        Returns:
            Cleanup statistics
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Check if cleanup is needed
            cursor.execute("""
                SELECT last_cleanup FROM buffer_metadata WHERE id = 1
            """)
            result = cursor.fetchone()
            last_cleanup = result[0] if result else None
            
            # Only cleanup if enough time has passed or force=True
            if not force and last_cleanup:
                last_cleanup_dt = datetime.fromisoformat(last_cleanup)
                if datetime.now() - last_cleanup_dt < timedelta(hours=1):
                    return {"cleaned": 0, "reason": "too_recent"}
            
            cutoff_date = (datetime.now() - timedelta(days=self.cleanup_after_days)).isoformat()
            
            # Delete old sent predictions
            cursor.execute("""
                DELETE FROM prediction_buffer
                WHERE status = 'sent' AND buffered_at < ?
            """, (cutoff_date,))
            
            deleted_count = cursor.rowcount
            
            # Update last cleanup time
            cursor.execute("""
                UPDATE buffer_metadata
                SET last_cleanup = CURRENT_TIMESTAMP
                WHERE id = 1
            """)
            
            # Vacuum database to reclaim space
            cursor.execute("VACUUM")
            
            conn.commit()
            conn.close()
            
            db_size_mb = self.db_path.stat().st_size / (1024 * 1024)
            logger.info(f"Cleaned up {deleted_count} old predictions, size: {db_size_mb:.2f}MB")
            
            return {
                "cleaned": deleted_count,
                "buffer_size_mb": round(db_size_mb, 2),
            }
        
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return {"cleaned": 0, "error": str(e)}
    
    async def check_space(self) -> bool:
        """
        Check if buffer is near capacity
        
        Returns:
            True if buffer usage is below limit, False if near/over limit
        """
        try:
            stats = await self.get_stats()
            buffer_size_mb = stats["buffer_size_mb"]
            
            if buffer_size_mb > self.max_buffer_size_mb * 0.9:
                logger.warning(
                    f"Buffer near capacity: {buffer_size_mb:.2f}MB / "
                    f"{self.max_buffer_size_mb}MB"
                )
                # Trigger cleanup
                await self.cleanup()
                return False
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to check buffer space: {e}")
            return True


class BufferRecoveryManager:
    """
    Manages recovery of buffered predictions when connectivity is restored
    
    - Monitors network connectivity
    - Retries buffered predictions
    - Tracks recovery progress
    """
    
    def __init__(
        self,
        buffer_manager: LocalBufferManager,
        send_function,
    ):
        """
        Initialize BufferRecoveryManager
        
        Args:
            buffer_manager: LocalBufferManager instance
            send_function: Async function to send predictions to cloud
        """
        self.buffer_manager = buffer_manager
        self.send_function = send_function
        self._recovery_task: Optional[asyncio.Task] = None
        self._is_recovering = False
    
    async def start_recovery(self, batch_size: int = 32):
        """
        Start recovering buffered predictions
        
        Args:
            batch_size: Predictions per batch
        """
        if self._is_recovering:
            logger.warning("Recovery already in progress")
            return
        
        self._is_recovering = True
        self._recovery_task = asyncio.create_task(
            self._recovery_loop(batch_size)
        )
        logger.info("Started buffer recovery")
    
    async def stop_recovery(self):
        """Stop recovery task"""
        self._is_recovering = False
        if self._recovery_task:
            self._recovery_task.cancel()
            try:
                await self._recovery_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped buffer recovery")
    
    async def _recovery_loop(self, batch_size: int):
        """Background task for recovery"""
        while self._is_recovering:
            try:
                # Get pending predictions
                batch = await self.buffer_manager.get_batch(batch_size)
                
                if not batch:
                    # No pending predictions, wait before checking again
                    await asyncio.sleep(60)
                    continue
                
                logger.info(f"Recovering {len(batch)} buffered predictions")
                
                # Send batch
                predictions = [pred for _, pred in batch]
                success = await self.send_function(predictions)
                
                if success:
                    # Mark all as sent
                    for pred_id, _ in batch:
                        await self.buffer_manager.mark_sent(pred_id)
                    logger.info(f"Recovered {len(batch)} predictions")
                else:
                    # Wait before retry
                    await asyncio.sleep(30)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in recovery loop: {e}")
                await asyncio.sleep(30)
    
    async def get_recovery_status(self) -> Dict:
        """Get buffer recovery status"""
        stats = await self.buffer_manager.get_stats()
        return {
            "is_recovering": self._is_recovering,
            "pending_predictions": stats["pending"],
            "recovered_predictions": stats["sent"],
            "failed_predictions": stats["failed"],
            "buffer_size_mb": stats["buffer_size_mb"],
        }
