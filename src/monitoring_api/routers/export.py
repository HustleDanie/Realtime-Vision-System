"""Export and reporting endpoints for inspection logs and metrics."""

import csv
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.monitoring_api.db import get_db
from src.monitoring_api import crud

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/inspection-logs/csv")
def export_inspection_logs_csv(
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    defects_only: bool = False,
    model_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Export inspection logs as CSV.
    
    Useful for data analysis, reporting, and archival.
    """
    logs = crud.get_inspection_logs(
        db=db,
        limit=limit,
        offset=offset,
        defects_only=defects_only,
        model_name=model_name,
    )
    
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "id",
            "image_id",
            "image_path",
            "timestamp",
            "model_name",
            "model_version",
            "defect_detected",
            "confidence_score",
            "defect_type",
            "inference_time_ms",
            "processing_notes",
        ]
    )
    
    writer.writeheader()
    for log in logs:
        writer.writerow({
            "id": log.id,
            "image_id": log.image_id,
            "image_path": log.image_path,
            "timestamp": log.timestamp.isoformat() if log.timestamp else "",
            "model_name": log.model_name,
            "model_version": log.model_version,
            "defect_detected": log.defect_detected,
            "confidence_score": log.confidence_score,
            "defect_type": log.defect_type,
            "inference_time_ms": log.inference_time_ms,
            "processing_notes": log.processing_notes,
        })
    
    output.seek(0)
    filename = f"inspection_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/metrics/csv")
def export_metrics_csv(db: Session = Depends(get_db)):
    """
    Export aggregated metrics as CSV.
    Includes overall statistics and defect summaries.
    """
    metrics = crud.get_metrics(db)
    
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "metric",
            "value",
            "timestamp",
        ]
    )
    
    writer.writeheader()
    timestamp = datetime.now().isoformat()
    
    for key, value in metrics.items():
        writer.writerow({
            "metric": key,
            "value": value,
            "timestamp": timestamp,
        })
    
    output.seek(0)
    filename = f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/inspection-logs/json")
def export_inspection_logs_json(
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    defects_only: bool = False,
    model_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Export inspection logs as JSON for integration with other tools.
    """
    import json
    
    logs = crud.get_inspection_logs(
        db=db,
        limit=limit,
        offset=offset,
        defects_only=defects_only,
        model_name=model_name,
    )
    
    data = {
        "export_timestamp": datetime.now().isoformat(),
        "count": len(logs),
        "logs": [
            {
                "id": log.id,
                "image_id": log.image_id,
                "image_path": log.image_path,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "model_name": log.model_name,
                "model_version": log.model_version,
                "defect_detected": log.defect_detected,
                "confidence_score": log.confidence_score,
                "defect_type": log.defect_type,
                "inference_time_ms": log.inference_time_ms,
                "bounding_boxes": log.bounding_boxes,
                "processing_notes": log.processing_notes,
            }
            for log in logs
        ]
    }
    
    output = io.StringIO()
    json.dump(data, output, indent=2)
    output.seek(0)
    filename = f"inspection_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/summary-report")
def export_summary_report(db: Session = Depends(get_db)):
    """
    Generate a comprehensive summary report with key metrics and insights.
    Returns JSON with executive summary.
    """
    import json
    from sqlalchemy import func
    from src.logging_service.database import PredictionLog
    
    metrics = crud.get_metrics(db)
    
    # Additional insights
    defect_types_query = (
        db.query(
            PredictionLog.defect_type,
            func.count(PredictionLog.id).label("count")
        )
        .filter(PredictionLog.defect_detected == True)
        .group_by(PredictionLog.defect_type)
        .all()
    )
    
    defect_type_breakdown = {
        dtype: count for dtype, count in defect_types_query if dtype
    }
    
    # Model versions used
    model_versions_query = (
        db.query(
            PredictionLog.model_version,
            func.count(PredictionLog.id).label("count")
        )
        .group_by(PredictionLog.model_version)
        .all()
    )
    
    model_versions = {
        version: count for version, count in model_versions_query if version
    }
    
    report = {
        "report_generated": datetime.now().isoformat(),
        "summary": {
            "total_predictions": metrics.get("total_predictions", 0),
            "defects_detected": metrics.get("defects_detected", 0),
            "defect_rate": f"{metrics.get('defect_rate', 0) * 100:.2f}%",
            "avg_confidence": f"{metrics.get('avg_confidence', 0):.3f}",
            "avg_inference_time_ms": f"{metrics.get('avg_inference_time_ms', 0):.2f}",
        },
        "defect_type_breakdown": defect_type_breakdown,
        "model_versions_used": model_versions,
    }
    
    output = io.StringIO()
    json.dump(report, output, indent=2)
    output.seek(0)
    filename = f"summary_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
