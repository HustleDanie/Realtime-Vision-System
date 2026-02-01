"""Labeling queue and review endpoints for active learning."""

import json
import logging
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from src.logging_service.database import (
    DatabaseConnection,
    LabelingTask,
    ReviewedLabel,
    PredictionLog,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["labeling"])

# Database connection
db_connection: Optional[DatabaseConnection] = None


class LabelingQueueItem(BaseModel):
    """Item in labeling queue."""
    id: int
    image_id: str
    image_path: str
    timestamp: str
    status: str
    confidence_score: Optional[float]
    defect_detected: Optional[bool]
    reason: Optional[str]
    model_version: Optional[str]


class LabelSubmission(BaseModel):
    """Human label submission."""
    queue_id: int
    label: str
    reviewer_notes: Optional[str] = None


class LabelStats(BaseModel):
    """Labeling queue statistics."""
    pending_count: int
    labeled_count: int
    approved_count: int
    ready_for_training: int


def get_db_session() -> Session:
    """Get database session."""
    if db_connection is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return db_connection.get_session()


@router.get("/queue", response_model=List[LabelingQueueItem])
async def get_queue(
    status: str = "pending",
    limit: int = 50,
) -> List[LabelingQueueItem]:
    """Get items from labeling queue."""
    try:
        session = get_db_session()
        
        items = session.query(LabelingTask).filter(
            LabelingTask.status == status
        ).order_by(
            LabelingTask.timestamp.desc()
        ).limit(limit).all()
        
        result = [
            LabelingQueueItem(
                id=item.id,
                image_id=item.image_id,
                image_path=item.image_path,
                timestamp=item.timestamp.isoformat(),
                status=item.status,
                confidence_score=item.confidence_score,
                defect_detected=item.defect_detected,
                reason=item.reason,
                model_version=item.model_version,
            )
            for item in items
        ]
        
        session.close()
        return result
    except Exception as e:
        logger.error(f"Error fetching queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=LabelStats)
async def get_stats() -> LabelStats:
    """Get labeling queue statistics."""
    try:
        session = get_db_session()
        
        pending = session.query(LabelingTask).filter(
            LabelingTask.status == "pending"
        ).count()
        
        labeled = session.query(LabelingTask).filter(
            LabelingTask.status == "labeled"
        ).count()
        
        approved = session.query(ReviewedLabel).count()
        
        ready = session.query(ReviewedLabel).filter(
            ReviewedLabel.used_for_training == False
        ).count()
        
        session.close()
        
        return LabelStats(
            pending_count=pending,
            labeled_count=labeled,
            approved_count=approved,
            ready_for_training=ready,
        )
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit-label")
async def submit_label(submission: LabelSubmission) -> dict:
    """Submit a human label for a queue item."""
    try:
        session = get_db_session()
        
        # Get the queue item
        queue_item = session.query(LabelingTask).filter(
            LabelingTask.id == submission.queue_id
        ).first()
        
        if not queue_item:
            session.close()
            raise HTTPException(status_code=404, detail="Queue item not found")
        
        # Update queue item
        queue_item.status = "labeled"
        queue_item.human_label = submission.label
        queue_item.reviewer_notes = submission.reviewer_notes
        queue_item.labeled_at = datetime.utcnow()
        
        # Create reviewed label
        reviewed = ReviewedLabel(
            image_id=queue_item.image_id,
            image_path=queue_item.image_path,
            label=submission.label,
            confidence=queue_item.confidence_score,
            reviewer="human_annotator",  # In production, would get from auth
            used_for_training=False,
        )
        
        session.add(reviewed)
        session.commit()
        
        logger.info(f"Label submitted for {queue_item.image_id}: {submission.label}")
        
        session.close()
        
        return {
            "status": "success",
            "queue_id": submission.queue_id,
            "image_id": queue_item.image_id,
            "label": submission.label,
            "message": "Label saved successfully",
        }
    except Exception as e:
        logger.error(f"Error submitting label: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve-label/{reviewed_id}")
async def approve_label(reviewed_id: int) -> dict:
    """Approve a reviewed label for training."""
    try:
        session = get_db_session()
        
        label = session.query(ReviewedLabel).filter(
            ReviewedLabel.id == reviewed_id
        ).first()
        
        if not label:
            session.close()
            raise HTTPException(status_code=404, detail="Label not found")
        
        label.used_for_training = True
        session.commit()
        
        logger.info(f"Label approved for training: {label.image_id}")
        
        session.close()
        
        return {
            "status": "approved",
            "reviewed_id": reviewed_id,
            "image_id": label.image_id,
            "label": label.label,
        }
    except Exception as e:
        logger.error(f"Error approving label: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/skip/{queue_id}")
async def skip_item(queue_id: int) -> dict:
    """Skip a labeling queue item."""
    try:
        session = get_db_session()
        
        item = session.query(LabelingTask).filter(
            LabelingTask.id == queue_id
        ).first()
        
        if not item:
            session.close()
            raise HTTPException(status_code=404, detail="Queue item not found")
        
        item.status = "skipped"
        session.commit()
        
        logger.info(f"Queue item skipped: {item.image_id}")
        
        session.close()
        
        return {
            "status": "skipped",
            "queue_id": queue_id,
            "image_id": item.image_id,
        }
    except Exception as e:
        logger.error(f"Error skipping item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
async def export_labels(format: str = "yolo") -> dict:
    """Export approved labels for training."""
    try:
        session = get_db_session()
        
        labels = session.query(ReviewedLabel).filter(
            ReviewedLabel.used_for_training == False
        ).all()
        
        if format == "yolo":
            # Export in YOLO format
            export_data = {
                "images": [],
                "labels": [],
                "count": len(labels),
            }
            
            for label in labels:
                export_data["images"].append({
                    "id": label.image_id,
                    "path": label.image_path,
                })
                export_data["labels"].append({
                    "image_id": label.image_id,
                    "label": label.label,
                    "confidence": label.confidence,
                })
        else:
            export_data = {
                "labels": [label.to_dict() for label in labels],
                "count": len(labels),
            }
        
        session.close()
        
        return {
            "status": "exported",
            "format": format,
            "count": len(labels),
            "data": export_data,
        }
    except Exception as e:
        logger.error(f"Error exporting labels: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enqueue")
async def enqueue_prediction(
    image_id: str,
    image_path: str,
    confidence_score: float,
    defect_detected: bool,
    reason: str = "low_confidence",
    model_version: str = "unknown",
) -> dict:
    """Enqueue a prediction for labeling."""
    try:
        session = get_db_session()
        
        # Check if already in queue
        existing = session.query(LabelingTask).filter(
            LabelingTask.image_id == image_id
        ).first()
        
        if existing:
            session.close()
            return {
                "status": "duplicate",
                "image_id": image_id,
                "message": "Already in labeling queue",
            }
        
        task = LabelingTask(
            image_id=image_id,
            image_path=image_path,
            timestamp=datetime.utcnow(),
            status="pending",
            confidence_score=confidence_score,
            defect_detected=defect_detected,
            reason=reason,
            model_version=model_version,
        )
        
        session.add(task)
        session.commit()
        
        logger.info(f"Prediction enqueued: {image_id} (confidence: {confidence_score:.3f})")
        
        session.close()
        
        return {
            "status": "enqueued",
            "image_id": image_id,
            "reason": reason,
            "confidence_score": confidence_score,
        }
    except Exception as e:
        logger.error(f"Error enqueueing prediction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def set_db_connection(db_conn: DatabaseConnection):
    """Set the database connection (call this on app startup)."""
    global db_connection
    db_connection = db_conn
