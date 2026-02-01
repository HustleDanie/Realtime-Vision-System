from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from src.monitoring_api.db import get_db
from src.monitoring_api import crud
from src.monitoring_api.schemas import InspectionLogOut

router = APIRouter(prefix="/inspection-logs", tags=["inspection-logs"])


@router.get("/latest", response_model=List[InspectionLogOut])
def get_latest_inspection_logs(
    count: int = Query(10, ge=1, le=200),
    defects_only: bool = False,
    model_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return crud.get_latest_inspection_logs(
        db=db,
        count=count,
        defects_only=defects_only,
        model_name=model_name,
    )


@router.get("", response_model=List[InspectionLogOut])
def list_inspection_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    defects_only: bool = False,
    model_name: Optional[str] = None,
    min_confidence: Optional[float] = Query(None, ge=0, le=1, description="Minimum confidence score"),
    max_confidence: Optional[float] = Query(None, ge=0, le=1, description="Maximum confidence score"),
    defect_type: Optional[str] = Query(None, description="Filter by specific defect type"),
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    days_back: Optional[int] = Query(None, ge=1, le=365, description="Last N days"),
    db: Session = Depends(get_db),
):
    """
    List inspection logs with advanced filtering options.
    
    Supports:
    - Confidence score range filtering
    - Defect type filtering
    - Date range filtering
    - Time window filtering (last N days)
    """
    return crud.get_inspection_logs_advanced(
        db=db,
        limit=limit,
        offset=offset,
        defects_only=defects_only,
        model_name=model_name,
        min_confidence=min_confidence,
        max_confidence=max_confidence,
        defect_type=defect_type,
        start_date=start_date,
        end_date=end_date,
        days_back=days_back,
    )


@router.get("/{log_id}", response_model=InspectionLogOut)
def get_inspection_log(log_id: int, db: Session = Depends(get_db)):
    record = crud.get_inspection_log(db, log_id)
    if not record:
        raise HTTPException(status_code=404, detail="Inspection log not found")
    return record
