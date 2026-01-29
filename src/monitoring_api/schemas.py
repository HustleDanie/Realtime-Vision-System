from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class InspectionLogOut(BaseModel):
    id: int
    image_id: str
    image_path: str
    timestamp: datetime
    model_version: Optional[str] = None
    model_name: Optional[str] = None
    confidence_score: Optional[float] = None
    defect_detected: Optional[bool] = None
    defect_type: Optional[str] = None
    bounding_boxes: Optional[str] = None
    inference_time_ms: Optional[float] = None
    processing_notes: Optional[str] = None

    model_config = {"from_attributes": True}


class MetricsResponse(BaseModel):
    total_predictions: int
    defects_detected: int
    defect_rate: float
    avg_confidence: Optional[float] = None
    avg_inference_time_ms: Optional[float] = None
    latest_timestamp: Optional[datetime] = None


class ModelStatusResponse(BaseModel):
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    last_prediction_time: Optional[datetime] = None
    total_predictions: int
    defects_detected: int


class HealthResponse(BaseModel):
    status: str
    database: str
    timestamp: datetime
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    disk_percent: Optional[float] = None
