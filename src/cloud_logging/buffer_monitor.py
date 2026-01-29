"""
Monitoring and debugging utilities for buffer management
"""

import asyncio
import logging
from typing import Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class BufferMonitor:
    """
    Monitor and report on buffer status and health
    """
    
    def __init__(self, buffer_manager, client):
        """
        Initialize BufferMonitor
        
        Args:
            buffer_manager: LocalBufferManager instance
            client: EnhancedAsyncLoggingClient instance
        """
        self.buffer_manager = buffer_manager
        self.client = client
        self._monitor_task = None
    
    async def start(self, interval_seconds: int = 60):
        """
        Start monitoring buffer
        
        Args:
            interval_seconds: Monitoring interval
        """
        self._monitor_task = asyncio.create_task(
            self._monitor_loop(interval_seconds)
        )
        logger.info("BufferMonitor started")
    
    async def stop(self):
        """Stop monitoring"""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("BufferMonitor stopped")
    
    async def _monitor_loop(self, interval_seconds: int):
        """Background monitoring loop"""
        while True:
            try:
                stats = await self.get_full_status()
                
                # Log warnings if threshold exceeded
                if stats["buffer_stats"]["pending"] > 100:
                    logger.warning(
                        f"High pending predictions: "
                        f"{stats['buffer_stats']['pending']}"
                    )
                
                if stats["buffer_stats"]["buffer_size_mb"] > 100:
                    logger.warning(
                        f"Large buffer size: "
                        f"{stats['buffer_stats']['buffer_size_mb']}MB"
                    )
                
                if stats["buffer_stats"]["failed"] > 10:
                    logger.warning(
                        f"High failed predictions: "
                        f"{stats['buffer_stats']['failed']}"
                    )
                
                await asyncio.sleep(interval_seconds)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(interval_seconds)
    
    async def get_full_status(self) -> Dict:
        """Get comprehensive buffer and client status"""
        buffer_stats = await self.buffer_manager.get_stats()
        client_stats = self.client.get_stats()
        
        return {
            "buffer_stats": buffer_stats,
            "client_stats": client_stats,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }
    
    async def print_status(self):
        """Pretty print buffer status"""
        status = await self.get_full_status()
        
        print("\n" + "="*60)
        print("BUFFER STATUS REPORT")
        print("="*60)
        print(f"Timestamp: {status['timestamp']}")
        print()
        print("Buffer Statistics:")
        print(f"  Pending predictions: {status['buffer_stats']['pending']}")
        print(f"  Sent predictions: {status['buffer_stats']['sent']}")
        print(f"  Failed predictions: {status['buffer_stats']['failed']}")
        print(f"  Buffer size: {status['buffer_stats']['buffer_size_mb']:.2f}MB / "
              f"{status['buffer_stats']['buffer_limit_mb']}MB")
        print()
        print("Client Statistics:")
        print(f"  Total sent: {status['client_stats']['sent']}")
        print(f"  Total failed: {status['client_stats']['failed']}")
        print(f"  Total retried: {status['client_stats']['retried']}")
        print(f"  Total buffered: {status['client_stats']['buffered']}")
        print("="*60 + "\n")


async def cleanup_old_buffer_database(db_path: str, days: int = 7):
    """
    Manually cleanup old predictions from buffer database
    
    Args:
        db_path: Path to buffer database
        days: Delete predictions older than this many days
    """
    import sqlite3
    from datetime import datetime, timedelta
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            DELETE FROM prediction_buffer
            WHERE status = 'sent' AND buffered_at < ?
        """, (cutoff_date,))
        
        deleted = cursor.rowcount
        
        cursor.execute("VACUUM")
        conn.commit()
        conn.close()
        
        logger.info(f"Cleaned up {deleted} old predictions from buffer")
        return deleted
    
    except Exception as e:
        logger.error(f"Failed to cleanup buffer: {e}")
        return 0


async def reset_failed_predictions(db_path: str):
    """
    Reset failed predictions to pending for retry
    
    Args:
        db_path: Path to buffer database
    """
    import sqlite3
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE prediction_buffer
            SET status = 'pending', retry_count = 0
            WHERE status = 'failed'
        """)
        
        reset_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"Reset {reset_count} failed predictions to pending")
        return reset_count
    
    except Exception as e:
        logger.error(f"Failed to reset failed predictions: {e}")
        return 0


async def export_buffer_statistics(db_path: str, output_file: str):
    """
    Export buffer statistics to JSON file
    
    Args:
        db_path: Path to buffer database
        output_file: Output JSON file path
    """
    import sqlite3
    import json
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get statistics
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM prediction_buffer
            GROUP BY status
        """)
        
        stats_by_status = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Get sample failed predictions
        cursor.execute("""
            SELECT image_id, last_error FROM prediction_buffer
            WHERE status = 'failed'
            LIMIT 10
        """)
        
        failed_samples = [
            {"image_id": row[0], "error": row[1]}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        output_data = {
            "statistics": stats_by_status,
            "failed_samples": failed_samples,
            "exported_at": __import__("datetime").datetime.utcnow().isoformat(),
        }
        
        Path(output_file).write_text(json.dumps(output_data, indent=2))
        logger.info(f"Exported buffer statistics to {output_file}")
    
    except Exception as e:
        logger.error(f"Failed to export buffer statistics: {e}")


async def repair_buffer_database(db_path: str) -> bool:
    """
    Repair corrupted buffer database
    
    Args:
        db_path: Path to buffer database
        
    Returns:
        True if repair successful
    """
    import sqlite3
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Run integrity check
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        
        if result == "ok":
            logger.info("Buffer database integrity check passed")
            return True
        else:
            logger.warning(f"Database integrity check failed: {result}")
            
            # Attempt VACUUM to repair
            cursor.execute("VACUUM")
            conn.commit()
            logger.info("Ran VACUUM to repair database")
            return True
    
    except Exception as e:
        logger.error(f"Failed to repair buffer database: {e}")
        return False
