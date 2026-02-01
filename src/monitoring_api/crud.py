from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.logging_service.database import PredictionLog


def get_inspection_logs(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    defects_only: bool = False,
    model_name: Optional[str] = None,
) -> List[PredictionLog]:
    query = db.query(PredictionLog)

    if defects_only:
        query = query.filter(PredictionLog.defect_detected == True)
    if model_name:
        query = query.filter(PredictionLog.model_name == model_name)

    return (
        query.order_by(PredictionLog.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_inspection_logs_advanced(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    defects_only: bool = False,
    model_name: Optional[str] = None,
    min_confidence: Optional[float] = None,
    max_confidence: Optional[float] = None,
    defect_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    days_back: Optional[int] = None,
) -> List[PredictionLog]:
    """Get inspection logs with advanced filtering."""
    query = db.query(PredictionLog)
    
    if defects_only:
        query = query.filter(PredictionLog.defect_detected == True)
    if model_name:
        query = query.filter(PredictionLog.model_name == model_name)
    if defect_type:
        query = query.filter(PredictionLog.defect_type == defect_type)
    if min_confidence is not None:
        query = query.filter(PredictionLog.confidence_score >= min_confidence)
    if max_confidence is not None:
        query = query.filter(PredictionLog.confidence_score <= max_confidence)
    
    # Date filtering
    if days_back:
        cutoff_date = datetime.now() - timedelta(days=days_back)
        query = query.filter(PredictionLog.timestamp >= cutoff_date)
    else:
        if start_date:
            query = query.filter(PredictionLog.timestamp >= start_date)
        if end_date:
            query = query.filter(PredictionLog.timestamp <= end_date)
    
    return (
        query.order_by(PredictionLog.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_inspection_log(db: Session, log_id: int) -> Optional[PredictionLog]:
    return db.query(PredictionLog).filter(PredictionLog.id == log_id).first()


def get_latest_inspection_logs(
    db: Session,
    count: int = 10,
    defects_only: bool = False,
    model_name: Optional[str] = None,
) -> List[PredictionLog]:
    query = db.query(PredictionLog)

    if defects_only:
        query = query.filter(PredictionLog.defect_detected == True)
    if model_name:
        query = query.filter(PredictionLog.model_name == model_name)

    return query.order_by(PredictionLog.timestamp.desc()).limit(count).all()


def get_metrics(db: Session):
    total = db.query(func.count(PredictionLog.id)).scalar() or 0
    defects = (
        db.query(func.count(PredictionLog.id))
        .filter(PredictionLog.defect_detected == True)
        .scalar()
        or 0
    )
    avg_confidence = db.query(func.avg(PredictionLog.confidence_score)).scalar()
    avg_inference = db.query(func.avg(PredictionLog.inference_time_ms)).scalar()
    latest_ts = db.query(func.max(PredictionLog.timestamp)).scalar()

    defect_rate = (defects / total) if total else 0.0

    return {
        "total_predictions": total,
        "defects_detected": defects,
        "defect_rate": defect_rate,
        "avg_confidence": float(avg_confidence) if avg_confidence is not None else None,
        "avg_inference_time_ms": float(avg_inference) if avg_inference is not None else None,
        "latest_timestamp": latest_ts,
    }


def get_model_status(db: Session):
    latest = (
        db.query(PredictionLog)
        .order_by(PredictionLog.timestamp.desc())
        .first()
    )

    total = db.query(func.count(PredictionLog.id)).scalar() or 0
    defects = (
        db.query(func.count(PredictionLog.id))
        .filter(PredictionLog.defect_detected == True)
        .scalar()
        or 0
    )

    return {
        "model_name": latest.model_name if latest else None,
        "model_version": latest.model_version if latest else None,
        "last_prediction_time": latest.timestamp if latest else None,
        "total_predictions": total,
        "defects_detected": defects,
    }


def create_inspection_log(
    db: Session,
    image_id: str,
    image_path: str,
    model_version: Optional[str] = None,
    model_name: Optional[str] = None,
    confidence_score: Optional[float] = None,
    defect_detected: Optional[bool] = None,
    defect_type: Optional[str] = None,
    bounding_boxes: Optional[str] = None,
    inference_time_ms: Optional[float] = None,
    processing_notes: Optional[str] = None,
) -> PredictionLog:
    """Create a new inspection log entry."""
    log = PredictionLog(
        image_id=image_id,
        image_path=image_path,
        timestamp=datetime.now(),
        model_version=model_version,
        model_name=model_name,
        confidence_score=confidence_score,
        defect_detected=defect_detected,
        defect_type=defect_type,
        bounding_boxes=bounding_boxes,
        inference_time_ms=inference_time_ms,
        processing_notes=processing_notes,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

