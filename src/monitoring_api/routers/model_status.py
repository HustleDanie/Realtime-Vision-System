from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.monitoring_api.db import get_db
from src.monitoring_api import crud
from src.monitoring_api.schemas import ModelStatusResponse
from src.logging_service.database import PredictionLog

router = APIRouter(prefix="/model-status", tags=["model-status"])


@router.get("", response_model=ModelStatusResponse)
def get_model_status(db: Session = Depends(get_db)):
    return crud.get_model_status(db)


@router.get("/versions/history")
def get_model_versions_history(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Get historical model versions used in predictions.
    Helps track model deployment history.
    """
    versions = (
        db.query(
            PredictionLog.model_version,
            PredictionLog.model_name,
            func.count(PredictionLog.id).label("usage_count"),
            func.min(PredictionLog.timestamp).label("first_used"),
            func.max(PredictionLog.timestamp).label("last_used"),
            func.avg(PredictionLog.confidence_score).label("avg_confidence"),
            func.avg(PredictionLog.inference_time_ms).label("avg_inference_time"),
        )
        .group_by(PredictionLog.model_version, PredictionLog.model_name)
        .order_by(PredictionLog.model_version.desc())
        .limit(limit)
        .all()
    )
    
    return {
        "model_versions": [
            {
                "version": v[0],
                "model_name": v[1],
                "usage_count": v[2],
                "first_used": v[3].isoformat() if v[3] else None,
                "last_used": v[4].isoformat() if v[4] else None,
                "avg_confidence": float(v[5]) if v[5] else None,
                "avg_inference_time_ms": float(v[6]) if v[6] else None,
            }
            for v in versions
        ]
    }


@router.get("/versions/compare")
def compare_model_versions(
    version1: str = Query(..., description="First model version"),
    version2: str = Query(..., description="Second model version"),
    db: Session = Depends(get_db),
):
    """
    Compare performance between two model versions.
    Useful for A/B testing and regression detection.
    """
    
    def get_version_stats(version: str):
        stats = (
            db.query(
                func.count(PredictionLog.id).label("total"),
                func.sum(
                    func.cast(PredictionLog.defect_detected == True, func.Integer)
                ).label("defects"),
                func.avg(PredictionLog.confidence_score).label("avg_confidence"),
                func.avg(PredictionLog.inference_time_ms).label("avg_inference_time"),
                func.min(PredictionLog.inference_time_ms).label("min_inference_time"),
                func.max(PredictionLog.inference_time_ms).label("max_inference_time"),
            )
            .filter(PredictionLog.model_version == version)
            .first()
        )
        
        total = stats[0] or 0
        defects = stats[1] or 0
        
        return {
            "total_predictions": total,
            "defects_detected": defects,
            "defect_rate": (defects / total) if total else 0,
            "avg_confidence": float(stats[2]) if stats[2] else None,
            "avg_inference_time_ms": float(stats[3]) if stats[3] else None,
            "min_inference_time_ms": float(stats[4]) if stats[4] else None,
            "max_inference_time_ms": float(stats[5]) if stats[5] else None,
        }
    
    v1_stats = get_version_stats(version1)
    v2_stats = get_version_stats(version2)
    
    # Calculate differences
    diff_confidence = None
    diff_inference = None
    diff_defect_rate = None
    
    if v1_stats["avg_confidence"] and v2_stats["avg_confidence"]:
        diff_confidence = v2_stats["avg_confidence"] - v1_stats["avg_confidence"]
    if v1_stats["avg_inference_time_ms"] and v2_stats["avg_inference_time_ms"]:
        diff_inference = v2_stats["avg_inference_time_ms"] - v1_stats["avg_inference_time_ms"]
    if v1_stats["defect_rate"] is not None and v2_stats["defect_rate"] is not None:
        diff_defect_rate = v2_stats["defect_rate"] - v1_stats["defect_rate"]
    
    return {
        "version1": {
            "name": version1,
            "stats": v1_stats,
        },
        "version2": {
            "name": version2,
            "stats": v2_stats,
        },
        "comparison": {
            "confidence_delta": diff_confidence,
            "inference_time_delta_ms": diff_inference,
            "defect_rate_delta": diff_defect_rate,
            "winner": {
                "best_confidence": version2 if diff_confidence and diff_confidence > 0 else version1,
                "fastest_inference": version2 if diff_inference and diff_inference < 0 else version1,
            }
        }
    }


@router.get("/versions/performance-over-time")
def get_model_performance_timeline(
    version: Optional[str] = Query(None, description="Specific model version (optional)"),
    days: int = Query(7, ge=1, le=90, description="Last N days"),
    db: Session = Depends(get_db),
):
    """
    Get model performance metrics over time (daily aggregation).
    Useful for detecting performance degradation or improvements.
    """
    from sqlalchemy import func, cast, Date
    import sqlalchemy
    
    cutoff_date = datetime.now() - timedelta(days=days)
    
    query = db.query(
        cast(PredictionLog.timestamp, Date).label("date"),
        func.count(PredictionLog.id).label("predictions"),
        func.sum(
            cast(PredictionLog.defect_detected == True, sqlalchemy.Integer)
        ).label("defects"),
        func.avg(PredictionLog.confidence_score).label("avg_confidence"),
        func.avg(PredictionLog.inference_time_ms).label("avg_inference_time"),
    ).filter(PredictionLog.timestamp >= cutoff_date)
    
    if version:
        query = query.filter(PredictionLog.model_version == version)
    
    results = (
        query.group_by(cast(PredictionLog.timestamp, Date))
        .order_by(cast(PredictionLog.timestamp, Date))
        .all()
    )
    
    timeline = []
    for date, predictions, defects, avg_conf, avg_inf in results:
        timeline.append({
            "date": date.isoformat() if date else None,
            "predictions": predictions,
            "defects": defects or 0,
            "defect_rate": (defects / predictions) if predictions else 0,
            "avg_confidence": float(avg_conf) if avg_conf else None,
            "avg_inference_time_ms": float(avg_inf) if avg_inf else None,
        })
    
    return {
        "model_version": version or "all",
        "period_days": days,
        "timeline": timeline,
    }

