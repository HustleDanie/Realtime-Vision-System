"""Retraining trigger and status endpoints."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from src.logging_service.database import (
    DatabaseConnection,
    RetrainingEvent,
    ReviewedLabel,
    LabelingTask,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["retraining"])

# Database connection (will be injected via dependency)
db_connection: Optional[DatabaseConnection] = None


class RetrainingConditions(BaseModel):
    """Current conditions for retraining."""
    drift_detected: bool
    drift_score: Optional[float] = None
    new_labels_count: int
    should_retrain: bool
    reason: str


class RetrainingStatus(BaseModel):
    """Status of retraining system."""
    status: str  # idle, running, completed, failed
    last_retrain_time: Optional[str] = None
    current_retrain_event_id: Optional[str] = None
    drift_detected: bool
    new_labels_count: int
    should_retrain: bool


class RetrainingEvent(BaseModel):
    """Retraining event details."""
    event_id: str
    triggered_by: str
    drift_score: Optional[float]
    new_labels_count: int
    status: str
    started_at: str
    completed_at: Optional[str]
    new_model_version: Optional[str]
    improvement_metrics: Optional[dict]


def get_db_session() -> Session:
    """Get database session."""
    if db_connection is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return db_connection.get_session()


@router.get("/conditions", response_model=RetrainingConditions)
async def check_conditions() -> RetrainingConditions:
    """Check if retraining should be triggered."""
    try:
        session = get_db_session()
        
        # Check for new labeled samples
        new_labels = session.query(ReviewedLabel).filter(
            ReviewedLabel.used_for_training == False
        ).count()
        
        # Check for recent drift (would be from external drift detection)
        drift_detected = new_labels >= 50  # Simplified for now
        drift_score = min(float(new_labels) / 100.0, 1.0)
        
        should_retrain = drift_detected or new_labels >= 50
        reason = ""
        if drift_detected and new_labels >= 50:
            reason = "Drift detected AND sufficient new labels"
        elif drift_detected:
            reason = "Drift detected"
        elif new_labels >= 50:
            reason = f"{new_labels} new labeled samples ready"
        
        session.close()
        
        return RetrainingConditions(
            drift_detected=drift_detected,
            drift_score=drift_score,
            new_labels_count=new_labels,
            should_retrain=should_retrain,
            reason=reason,
        )
    except Exception as e:
        logger.error(f"Error checking retraining conditions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=RetrainingStatus)
async def get_status() -> RetrainingStatus:
    """Get current retraining status."""
    try:
        session = get_db_session()
        
        # Get latest retraining event
        latest_event = session.query(RetrainingEvent).order_by(
            RetrainingEvent.started_at.desc()
        ).first()
        
        # Get conditions
        conditions = await check_conditions()
        
        status = "idle"
        current_event_id = None
        last_retrain_time = None
        
        if latest_event:
            status = latest_event.status
            current_event_id = latest_event.event_id
            last_retrain_time = latest_event.completed_at.isoformat() if latest_event.completed_at else None
        
        session.close()
        
        return RetrainingStatus(
            status=status,
            last_retrain_time=last_retrain_time,
            current_retrain_event_id=current_event_id,
            drift_detected=conditions.drift_detected,
            new_labels_count=conditions.new_labels_count,
            should_retrain=conditions.should_retrain,
        )
    except Exception as e:
        logger.error(f"Error getting retraining status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger")
async def trigger_retraining() -> dict:
    """Manually trigger retraining."""
    try:
        session = get_db_session()
        
        # Check conditions
        conditions = await check_conditions()
        
        if not conditions.should_retrain:
            session.close()
            return {
                "status": "skipped",
                "reason": "Conditions not met for retraining",
                "conditions": conditions.dict(),
            }
        
        # Create retraining event
        event_id = f"retrain_{datetime.utcnow().timestamp()}"
        triggered_by = "drift" if conditions.drift_detected else "new_labels"
        
        retrain_event = RetrainingEvent(
            event_id=event_id,
            triggered_by=triggered_by,
            drift_score=conditions.drift_score,
            new_labels_count=conditions.new_labels_count,
            status="started",
            model_version=None,
            previous_model_version=None,
            new_model_version=None,
        )
        
        session.add(retrain_event)
        session.commit()
        
        logger.info(f"Retraining triggered: {event_id}")
        logger.info(f"Triggered by: {triggered_by}")
        logger.info(f"New labels: {conditions.new_labels_count}")
        logger.info(f"Drift score: {conditions.drift_score}")
        
        # TODO: In production, would invoke:
        # - scripts/train_yolo_dvc_mlflow.py
        # - Or kick off a background job
        # - Or invoke Azure ML pipeline
        
        session.close()
        
        return {
            "status": "triggered",
            "event_id": event_id,
            "triggered_by": triggered_by,
            "new_labels_count": conditions.new_labels_count,
            "message": "Retraining pipeline started",
        }
    except Exception as e:
        logger.error(f"Error triggering retraining: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_history(limit: int = 10) -> list:
    """Get retraining event history."""
    try:
        session = get_db_session()
        
        events = session.query(RetrainingEvent).order_by(
            RetrainingEvent.started_at.desc()
        ).limit(limit).all()
        
        result = []
        for event in events:
            result.append({
                "event_id": event.event_id,
                "triggered_by": event.triggered_by,
                "drift_score": event.drift_score,
                "new_labels_count": event.new_labels_count,
                "status": event.status,
                "started_at": event.started_at.isoformat(),
                "completed_at": event.completed_at.isoformat() if event.completed_at else None,
                "new_model_version": event.new_model_version,
                "error_message": event.error_message,
            })
        
        session.close()
        return result
    except Exception as e:
        logger.error(f"Error getting retraining history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mark-completed/{event_id}")
async def mark_completed(
    event_id: str,
    new_model_version: Optional[str] = None,
    improvement_metrics: Optional[dict] = None,
) -> dict:
    """Mark retraining event as completed (for pipeline callbacks)."""
    try:
        session = get_db_session()
        
        event = session.query(RetrainingEvent).filter(
            RetrainingEvent.event_id == event_id
        ).first()
        
        if not event:
            session.close()
            raise HTTPException(status_code=404, detail="Event not found")
        
        event.status = "completed"
        event.completed_at = datetime.utcnow()
        event.new_model_version = new_model_version
        if improvement_metrics:
            event.improvement_metrics = json.dumps(improvement_metrics)
        
        session.commit()
        logger.info(f"Retraining event marked completed: {event_id}")
        
        session.close()
        return {"status": "completed", "event_id": event_id}
    except Exception as e:
        logger.error(f"Error marking completed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def set_db_connection(db_conn: DatabaseConnection):
    """Set the database connection (call this on app startup)."""
    global db_connection
    db_connection = db_conn
