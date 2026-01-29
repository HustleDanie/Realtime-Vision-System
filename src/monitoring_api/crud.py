from datetime import datetime
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
