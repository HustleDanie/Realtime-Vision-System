from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.monitoring_api.db import get_db
from src.monitoring_api import crud
from src.monitoring_api.schemas import MetricsResponse

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("", response_model=MetricsResponse)
def get_metrics(db: Session = Depends(get_db)):
    return crud.get_metrics(db)


@router.get("/summary", response_model=MetricsResponse)
def get_metrics_summary(db: Session = Depends(get_db)):
    return crud.get_metrics(db)
