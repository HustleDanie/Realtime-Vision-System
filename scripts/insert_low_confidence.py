#!/usr/bin/env python3
"""
Low-Confidence Prediction Insertion and Labeling Queue Verification

This script:
1. Generates synthetic predictions with controlled low confidence
2. Inserts them into the labeling_queue table
3. Verifies they were successfully queued
4. Reports queue status and pending items

This is useful for testing the annotation workflow and ensuring low-confidence
predictions are properly routed for human review.
"""

import os
import json
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple
import sys

# Don't import from src - use direct SQLite instead
SQLALCHEMY_AVAILABLE = False


class LabelingQueueManager:
    """Manages low-confidence predictions and labeling queue."""
    
    def __init__(self, db_path: str = "vision_logs.db"):
        self.db_path = db_path
        self.confidence_threshold = 0.5  # Below this = needs labeling
        self.use_sqlalchemy = False  # Always use SQLite
    
    def generate_low_confidence_predictions(
        self,
        count: int = 10,
        confidence_range: Tuple[float, float] = (0.1, 0.5),
        seed: int = 42
    ) -> List[Dict[str, Any]]:
        """Generate synthetic low-confidence predictions."""
        import numpy as np
        np.random.seed(seed)
        
        predictions = []
        defect_types = ["crack", "dent", "scratch", "discoloration", "burn_mark"]
        
        for i in range(count):
            # Random confidence in low range
            confidence = np.random.uniform(confidence_range[0], confidence_range[1])
            
            # Create synthetic prediction
            pred = {
                "image_id": f"low_conf_pred_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i:03d}",
                "image_path": f"./predictions/low_conf_{i:03d}.png",
                "timestamp": datetime.utcnow(),
                "model_version": "v1.0",
                "model_name": "yolov8m",
                "confidence_score": float(confidence),
                "defect_detected": bool(np.random.rand() > 0.5),
                "defect_type": np.random.choice(defect_types) if np.random.rand() > 0.3 else None,
                "bounding_boxes": json.dumps([
                    {
                        "x": float(np.random.uniform(0, 640)),
                        "y": float(np.random.uniform(0, 480)),
                        "width": float(np.random.uniform(50, 200)),
                        "height": float(np.random.uniform(50, 200)),
                        "confidence": float(confidence),
                    }
                ]) if np.random.rand() > 0.3 else None,
                "inference_time_ms": float(np.random.uniform(10, 100)),
                "processing_notes": f"Low confidence prediction: {confidence:.3f}. Requires human review."
            }
            predictions.append(pred)
        
        return predictions
    
    def insert_into_labeling_queue_sqlite(
        self,
        predictions: List[Dict[str, Any]]
    ) -> Tuple[int, List[str]]:
        """Insert predictions into labeling queue using SQLite."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Ensure table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS labeling_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_id VARCHAR(255) NOT NULL UNIQUE,
                    image_path VARCHAR(512) NOT NULL,
                    timestamp DATETIME NOT NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    confidence_score REAL,
                    defect_detected BOOLEAN,
                    model_version VARCHAR(50),
                    model_name VARCHAR(100),
                    metadata TEXT
                )
            """)
            
            inserted_count = 0
            inserted_ids = []
            
            for pred in predictions:
                # Create metadata JSON
                metadata = json.dumps({
                    "bounding_boxes": pred.get("bounding_boxes"),
                    "processing_notes": pred.get("processing_notes"),
                    "defect_type": pred.get("defect_type"),
                    "inference_time_ms": pred.get("inference_time_ms")
                })
                
                try:
                    cursor.execute("""
                        INSERT INTO labeling_queue 
                        (image_id, image_path, timestamp, status, confidence_score, 
                         defect_detected, model_version, model_name, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        pred["image_id"],
                        pred["image_path"],
                        pred["timestamp"].isoformat() if hasattr(pred["timestamp"], "isoformat") else pred["timestamp"],
                        "pending",
                        pred["confidence_score"],
                        pred["defect_detected"],
                        pred["model_version"],
                        pred["model_name"],
                        metadata
                    ))
                    inserted_ids.append(pred["image_id"])
                    inserted_count += 1
                except sqlite3.IntegrityError as e:
                    print(f"⚠️ Warning: Skipping duplicate image_id: {pred['image_id']}")
            
            conn.commit()
            conn.close()
            
            return inserted_count, inserted_ids
        except Exception as e:
            print(f"❌ Error inserting into queue: {e}")
            return 0, []
    
    def insert_into_labeling_queue(
        self,
        predictions: List[Dict[str, Any]]
    ) -> Tuple[int, List[str]]:
        """Insert predictions into labeling queue."""
        return self.insert_into_labeling_queue_sqlite(predictions)
        if self.use_sqlalchemy:
            return self.insert_into_labeling_queue_sqlalchemy(predictions)
        else:
            return self.insert_into_labeling_queue_sqlite(predictions)
    
    def verify_queue_entries(self, image_ids: List[str]) -> Dict[str, Any]:
        """Verify entries were successfully added to labeling queue."""
        return self._verify_queue_sqlite(image_ids)
    
    def _verify_queue_sqlite(self, image_ids: List[str]) -> Dict[str, Any]:
        """Verify queue entries using SQLite."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            verified = []
            failed = []
            
            for image_id in image_ids:
                cursor.execute(
                    "SELECT * FROM labeling_queue WHERE image_id = ?",
                    (image_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    verified.append({
                        "id": row["id"],
                        "image_id": row["image_id"],
                        "status": row["status"],
                        "confidence_score": row["confidence_score"],
                        "timestamp": row["timestamp"]
                    })
                else:
                    failed.append(image_id)
            
            conn.close()
            
            return {
                "total_requested": len(image_ids),
                "verified": len(verified),
                "failed": len(failed),
                "entries": verified,
                "failed_ids": failed
            }
        except Exception as e:
            print(f"❌ Error verifying entries: {e}")
            return {"error": str(e)}
    
    def _verify_queue_sqlalchemy(self, image_ids: List[str]) -> Dict[str, Any]:
        """Verify queue entries using SQLAlchemy."""
        try:
            session = self.db_connection.get_session()
            
            verified = []
            failed = []
            
            for image_id in image_ids:
                task = session.query(LabelingTask).filter(
                    LabelingTask.image_id == image_id
                ).first()
                
                if task:
                    verified.append({
                        "id": task.id,
                        "image_id": task.image_id,
                        "status": task.status,
                        "confidence_score": task.confidence_score,
                        "timestamp": task.timestamp.isoformat() if task.timestamp else None
                    })
                else:
                    failed.append(image_id)
            
            session.close()
            
            return {
                "total_requested": len(image_ids),
                "verified": len(verified),
                "failed": len(failed),
                "entries": verified,
                "failed_ids": failed
            }
        except Exception as e:
            print(f"❌ Error verifying entries: {e}")
            return {"error": str(e)}
    
    def _verify_queue_sqlalchemy(self, image_ids: List[str]) -> Dict[str, Any]:
        """Verify queue entries using SQLAlchemy."""
        try:
            session = self.db_connection.get_session()
            
            verified = []
            failed = []
            
            for image_id in image_ids:
                task = session.query(LabelingTask).filter(
                    LabelingTask.image_id == image_id
                ).first()
                
                if task:
                    verified.append({
                        "id": task.id,
                        "image_id": task.image_id,
                        "status": task.status,
                        "confidence_score": task.confidence_score,
                        "timestamp": task.timestamp.isoformat() if task.timestamp else None
                    })
                else:
                    failed.append(image_id)
            
            session.close()
            
            return {
                "total_requested": len(image_ids),
                "verified": len(verified),
                "failed": len(failed),
                "entries": verified,
                "failed_ids": failed
            }
        except Exception as e:
            print(f"❌ Error verifying entries: {e}")
            return {"error": str(e)}
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get overall labeling queue status."""
        return self._get_queue_status_sqlite()
    
    def _get_queue_status_sqlite(self) -> Dict[str, Any]:
        """Get queue status using SQLite."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Count by status
            cursor.execute("SELECT status, COUNT(*) as count FROM labeling_queue GROUP BY status")
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Total count
            cursor.execute("SELECT COUNT(*) FROM labeling_queue")
            total = cursor.fetchone()[0]
            
            # Average confidence for pending
            cursor.execute(
                "SELECT AVG(confidence_score) FROM labeling_queue WHERE status = 'pending'"
            )
            avg_conf = cursor.fetchone()[0]
            
            # Defect rate
            cursor.execute(
                "SELECT COUNT(*) FROM labeling_queue WHERE defect_detected = 1 AND status = 'pending'"
            )
            defects = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "total_items": total,
                "status_breakdown": status_counts,
                "pending_items": status_counts.get("pending", 0),
                "completed_items": status_counts.get("completed", 0),
                "avg_confidence_pending": float(avg_conf) if avg_conf else None,
                "defects_pending": defects
            }
        except Exception as e:
            print(f"❌ Error getting queue status: {e}")
            return {"error": str(e)}
    
    def _get_queue_status_sqlalchemy(self) -> Dict[str, Any]:
        """Get queue status using SQLAlchemy."""
        try:
            session = self.db_connection.get_session()
            
            # Count by status
            from sqlalchemy import func
            status_counts = {}
            for status in ["pending", "completed", "rejected"]:
                count = session.query(func.count(LabelingTask.id)).filter(
                    LabelingTask.status == status
                ).scalar()
                if count > 0:
                    status_counts[status] = count
            
            # Total count
            total = session.query(func.count(LabelingTask.id)).scalar()
            
            # Average confidence for pending
            avg_conf = session.query(func.avg(LabelingTask.confidence_score)).filter(
                LabelingTask.status == "pending"
            ).scalar()
            
            # Defect count
            defects = session.query(func.count(LabelingTask.id)).filter(
                LabelingTask.status == "pending",
                LabelingTask.defect_detected == True
            ).scalar()
            
            session.close()
            
            return {
                "total_items": total,
                "status_breakdown": status_counts,
                "pending_items": status_counts.get("pending", 0),
                "completed_items": status_counts.get("completed", 0),
                "avg_confidence_pending": float(avg_conf) if avg_conf else None,
                "defects_pending": defects or 0
            }
        except Exception as e:
            print(f"❌ Error getting queue status: {e}")
            return {"error": str(e)}
    
    def _get_queue_status_sqlalchemy(self) -> Dict[str, Any]:
        """Get queue status using SQLAlchemy."""
        try:
            session = self.db_connection.get_session()
            
            # Count by status
            from sqlalchemy import func
            status_counts = {}
            for status in ["pending", "completed", "rejected"]:
                count = session.query(func.count(LabelingTask.id)).filter(
                    LabelingTask.status == status
                ).scalar()
                if count > 0:
                    status_counts[status] = count
            
            # Total count
            total = session.query(func.count(LabelingTask.id)).scalar()
            
            # Average confidence for pending
            avg_conf = session.query(func.avg(LabelingTask.confidence_score)).filter(
                LabelingTask.status == "pending"
            ).scalar()
            
            # Defect count
            defects = session.query(func.count(LabelingTask.id)).filter(
                LabelingTask.status == "pending",
                LabelingTask.defect_detected == True
            ).scalar()
            
            session.close()
            
            return {
                "total_items": total,
                "status_breakdown": status_counts,
                "pending_items": status_counts.get("pending", 0),
                "completed_items": status_counts.get("completed", 0),
                "avg_confidence_pending": float(avg_conf) if avg_conf else None,
                "defects_pending": defects or 0
            }
        except Exception as e:
            print(f"❌ Error getting queue status: {e}")
            return {"error": str(e)}
    
    def get_pending_items(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get pending labeling items."""
        return self._get_pending_sqlite(limit)
    
    def _get_pending_sqlite(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get pending items using SQLite."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM labeling_queue 
                WHERE status = 'pending' 
                ORDER BY timestamp ASC 
                LIMIT ?
            """, (limit,))
            
            items = []
            for row in cursor.fetchall():
                items.append({
                    "id": row["id"],
                    "image_id": row["image_id"],
                    "image_path": row["image_path"],
                    "timestamp": row["timestamp"],
                    "confidence_score": row["confidence_score"],
                    "defect_detected": row["defect_detected"],
                    "model_version": row["model_version"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else None
                })
            
            conn.close()
            return items
        except Exception as e:
            print(f"❌ Error getting pending items: {e}")
            return []
    
    def _get_pending_sqlalchemy(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get pending items using SQLAlchemy."""
        try:
            session = self.db_connection.get_session()
            
            tasks = session.query(LabelingTask).filter(
                LabelingTask.status == "pending"
            ).order_by(LabelingTask.timestamp).limit(limit).all()
            
            items = []
            for task in tasks:
                items.append({
                    "id": task.id,
                    "image_id": task.image_id,
                    "image_path": task.image_path,
                    "timestamp": task.timestamp.isoformat() if task.timestamp else None,
                    "confidence_score": task.confidence_score,
                    "defect_detected": task.defect_detected,
                    "model_version": task.model_version,
                    "metadata": json.loads(task.metadata) if task.metadata else None
                })
            
            session.close()
            return items
        except Exception as e:
            print(f"❌ Error getting pending items: {e}")
            return []


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Insert low-confidence predictions into labeling queue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Insert 10 low-confidence predictions
  python insert_low_confidence.py
  
  # Insert 20 predictions with custom confidence range
  python insert_low_confidence.py --count 20 --confidence-min 0.2 --confidence-max 0.6
  
  # Verify specific predictions
  python insert_low_confidence.py --count 5 --verify-only
  
  # Get queue status
  python insert_low_confidence.py --queue-status
        """
    )
    
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of low-confidence predictions to generate"
    )
    
    parser.add_argument(
        "--confidence-min",
        type=float,
        default=0.1,
        help="Minimum confidence score"
    )
    
    parser.add_argument(
        "--confidence-max",
        type=float,
        default=0.5,
        help="Maximum confidence score (above this = not low-confidence)"
    )
    
    parser.add_argument(
        "--db",
        type=str,
        default="vision_logs.db",
        help="Path to database file"
    )
    
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify insertion, don't generate new predictions"
    )
    
    parser.add_argument(
        "--queue-status",
        action="store_true",
        help="Show labeling queue status"
    )
    
    parser.add_argument(
        "--show-pending",
        action="store_true",
        help="Show pending labeling items"
    )
    
    args = parser.parse_args()
    
    manager = LabelingQueueManager(args.db)
    
    print("\n" + "=" * 80)
    print("Labeling Queue Manager - Low-Confidence Prediction Insertion")
    print("=" * 80)
    
    # Show queue status if requested
    if args.queue_status:
        print("\nCurrent Queue Status:")
        status = manager.get_queue_status()
        if "error" not in status:
            print(f"  Total Items: {status['total_items']}")
            print(f"  Pending: {status['pending_items']}")
            print(f"  Completed: {status['completed_items']}")
            if status['avg_confidence_pending']:
                print(f"  Avg Confidence (pending): {status['avg_confidence_pending']:.3f}")
            print(f"  Defects Pending: {status['defects_pending']}")
        print()
    
    # Show pending items if requested
    if args.show_pending:
        print("\nPending Labeling Items (First 5):")
        pending = manager.get_pending_items(limit=5)
        for item in pending:
            print(f"  • {item['image_id']}")
            print(f"    Confidence: {item['confidence_score']:.3f}")
            print(f"    Defect: {item['defect_detected']}")
            print(f"    Status: {item['metadata'].get('processing_notes', 'N/A') if item['metadata'] else 'N/A'}")
        print()
    
    if not args.verify_only:
        # Generate predictions
        print(f"\nStep 1: Generating {args.count} low-confidence predictions...")
        print(f"  Confidence Range: [{args.confidence_min:.2f}, {args.confidence_max:.2f}]")
        
        predictions = manager.generate_low_confidence_predictions(
            count=args.count,
            confidence_range=(args.confidence_min, args.confidence_max)
        )
        
        print(f"  ✓ Generated {len(predictions)} predictions")
        print(f"    Avg Confidence: {sum(p['confidence_score'] for p in predictions) / len(predictions):.3f}")
        
        # Insert into queue
        print(f"\nStep 2: Inserting into labeling queue...")
        count, inserted_ids = manager.insert_into_labeling_queue(predictions)
        print(f"  ✓ Inserted {count} predictions into labeling queue")
        
        # Verify insertion
        print(f"\nStep 3: Verifying insertion...")
        verification = manager.verify_queue_entries(inserted_ids)
        
        print(f"  Total Requested: {verification['total_requested']}")
        print(f"  Verified: {verification['verified']}")
        print(f"  Failed: {verification['failed']}")
        
        if verification['entries']:
            print(f"\n  ✓ First 3 verified entries:")
            for entry in verification['entries'][:3]:
                print(f"    • ID {entry['id']}: {entry['image_id']}")
                print(f"      Confidence: {entry['confidence_score']:.3f}")
                print(f"      Status: {entry['status']}")
        
        if verification['failed']:
            print(f"\n  ✗ Failed entries:")
            for image_id in verification['failed']:
                print(f"    • {image_id}")
    
    # Show updated queue status
    print(f"\n" + "-" * 80)
    print("Updated Queue Status:")
    status = manager.get_queue_status()
    if "error" not in status:
        print(f"  Total Items: {status['total_items']}")
        print(f"  Pending: {status['pending_items']}")
        if status['avg_confidence_pending']:
            print(f"  Avg Confidence (pending): {status['avg_confidence_pending']:.3f}")
        print(f"  Defects Pending: {status['defects_pending']}")
    
    print("\n" + "=" * 80)
    print("✓ Operation complete!")
    print("=" * 80 + "\n")
    
    return 0


if __name__ == "__main__":
    exit(main())
