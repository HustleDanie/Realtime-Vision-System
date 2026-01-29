from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.monitoring_api.db import get_db
from src.monitoring_api import crud
from src.monitoring_api.schemas import ModelStatusResponse

router = APIRouter(prefix="/model-status", tags=["model-status"])


@router.get("", response_model=ModelStatusResponse)
def get_model_status(db: Session = Depends(get_db)):
    return crud.get_model_status(db)
