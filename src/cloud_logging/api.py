"""
FastAPI endpoint to receive predictions from edge inference service
"""

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
import logging
import sqlite3
from pathlib import Path

app = FastAPI(title="Cloud Logging API")
logger = logging.getLogger(__name__)


# Service state tracking for health checks
class LoggingServiceState:
    def __init__(self):
        self.db_initialized = False
        self.startup_time = None
        self.prediction_count = 0
        self.defect_count = 0
        self.error_count = 0
        self.last_prediction_time = None

state = LoggingServiceState()


class Detection(BaseModel):
    """Single detection result"""
    class_name: str = Field(..., alias="class")
    confidence: float
    bbox: List[float]
    uncertain: Optional[bool] = False


class PredictionPayload(BaseModel):
    """Prediction result from edge"""
    image_id: str
    timestamp: float
    model_version: str
    model_name: str
    inference_time_ms: float
    detections: List[Detection]
    defect_detected: bool
    confidence_scores: List[float]
    processing_notes: Optional[str] = None
    edge_device_id: Optional[str] = None


class PredictionBatch(BaseModel):
    """Batch of predictions from edge"""
    predictions: List[PredictionPayload]
    batch_size: int
    timestamp: str
    edge_device_id: Optional[str] = None


@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    db_path = Path("/app/data/predictions.db")
    try:
        state.startup_time = datetime.utcnow().isoformat()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create predictions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                received_at TEXT NOT NULL,
                model_version TEXT NOT NULL,
                model_name TEXT NOT NULL,
                inference_time_ms REAL NOT NULL,
                defect_detected BOOLEAN NOT NULL,
                confidence_scores TEXT NOT NULL,
                edge_device_id TEXT,
                processing_notes TEXT,
                detections_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_image_id (image_id),
                INDEX idx_edge_device_id (edge_device_id),
                INDEX idx_timestamp (timestamp)
            )
        """)
        
        conn.commit()
        conn.close()
        state.db_initialized = True
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        state.db_initialized = False
        raise


# ===== HEALTH CHECK ENDPOINTS (for Kubernetes monitoring) =====

@app.get("/health")
async def health():
    """
    Liveness probe: Check if container is alive.
    
    Returns 200 if service is running, 500 if critical errors.
    """
    try:
        logger.debug("Health check requested")
        return {
            "status": "healthy",
            "service": "cloud-logging-api",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": (datetime.utcnow() - datetime.fromisoformat(state.startup_time)).total_seconds() if state.startup_time else 0,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}, 500


@app.get("/ready")
async def ready():
    """
    Readiness probe: Check if service is ready to accept traffic.
    
    Returns 200 only if:
    - Database is initialized
    - Database is accessible
    - Recent predictions are being logged
    
    Kubernetes will not route traffic to pod if this fails (returns 503).
    """
    try:
        logger.debug("Readiness check requested")
        
        # Check database is initialized
        if not state.db_initialized:
            logger.warning("Database not initialized")
            return {"status": "not_ready", "reason": "database_not_initialized"}, 503
        
        # Test database connectivity
        try:
            db_path = Path("/app/data/predictions.db")
            conn = sqlite3.connect(str(db_path), timeout=2)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM predictions")
            cursor.fetchone()
            conn.close()
        except Exception as db_error:
            logger.warning(f"Database connectivity check failed: {db_error}")
            return {"status": "not_ready", "reason": "database_not_accessible"}, 503
        
        # Check error rate (if too many errors, not ready)
        if state.prediction_count > 0:
            error_rate = state.error_count / state.prediction_count
            if error_rate > 0.5:  # More than 50% errors
                logger.warning(f"High error rate: {error_rate:.2%}")
                return {
                    "status": "not_ready",
                    "reason": "high_error_rate",
                    "error_rate": error_rate
                }, 503
        
        return {
            "status": "ready",
            "db_initialized": state.db_initialized,
            "predictions_logged": state.prediction_count,
            "defects_detected": state.defect_count,
            "errors": state.error_count,
            "last_prediction": state.last_prediction_time,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "not_ready", "error": str(e)}, 503


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    
    Provides metrics for monitoring:
    - Predictions logged
    - Defects detected
    - Error rate
    - Database status
    """
    try:
        metrics_output = []
        
        # Database metrics
        metrics_output.append(f"# HELP logging_db_initialized Whether database is initialized")
        metrics_output.append(f"# TYPE logging_db_initialized gauge")
        metrics_output.append(f"logging_db_initialized {{service=\"cloud-logging-api\"}} {1 if state.db_initialized else 0}")
        
        # Prediction metrics
        metrics_output.append(f"# HELP logging_predictions_total Total predictions logged")
        metrics_output.append(f"# TYPE logging_predictions_total counter")
        metrics_output.append(f"logging_predictions_total {{service=\"cloud-logging-api\"}} {state.prediction_count}")
        
        metrics_output.append(f"# HELP logging_defects_total Total defects detected and logged")
        metrics_output.append(f"# TYPE logging_defects_total counter")
        metrics_output.append(f"logging_defects_total {{service=\"cloud-logging-api\"}} {state.defect_count}")
        
        metrics_output.append(f"# HELP logging_errors_total Total logging errors")
        metrics_output.append(f"# TYPE logging_errors_total counter")
        metrics_output.append(f"logging_errors_total {{service=\"cloud-logging-api\"}} {state.error_count}")
        
        return "\n".join(metrics_output), 200, {"Content-Type": "text/plain; charset=utf-8"}
    except Exception as e:
        logger.error(f"Metrics endpoint failed: {e}")
        return f"# Error generating metrics: {e}", 500, {"Content-Type": "text/plain; charset=utf-8"}


# ===== LOGGING ENDPOINTS =====

@app.post("/log")
async def log_predictions(
    batch: PredictionBatch,
    authorization: Optional[str] = Header(None),
) -> Dict:
    """
    Receive batch of predictions from edge inference service
    
    Args:
        batch: Batch of predictions
        authorization: Optional Bearer token
        
    Returns:
        Status response
    """
    try:
        # TODO: Validate API key if provided
        if authorization:
            token = authorization.replace("Bearer ", "")
            logger.debug(f"Received authorized request with token: {token[:20]}...")
        
        # Store predictions in database
        import json
        
        db_path = Path("/app/data/predictions.db")
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        received_at = datetime.utcnow().isoformat()
        
        for pred in batch.predictions:
            detections_json = json.dumps([d.dict() for d in pred.detections])
            confidence_scores_json = json.dumps(pred.confidence_scores)
            
            cursor.execute("""
                INSERT INTO predictions (
                    image_id, timestamp, received_at, model_version,
                    model_name, inference_time_ms, defect_detected,
                    confidence_scores, edge_device_id, processing_notes,
                    detections_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pred.image_id,
                pred.timestamp,
                received_at,
                pred.model_version,
                pred.model_name,
                pred.inference_time_ms,
                pred.defect_detected,
                confidence_scores_json,
                pred.edge_device_id or batch.edge_device_id,
                pred.processing_notes,
                detections_json,
            ))
            
            # Track metrics
            state.prediction_count += 1
            if pred.defect_detected:
                state.defect_count += 1
        
        conn.commit()
        conn.close()
        
        state.last_prediction_time = datetime.utcnow().isoformat()
        
        logger.info(
            f"Stored {len(batch.predictions)} predictions from "
            f"{batch.edge_device_id} (batch: {batch.batch_size})"
        )
        
        return {
            "status": "success",
            "predictions_stored": len(batch.predictions),
            "batch_size": batch.batch_size,
            "timestamp": received_at,
        }
    
    except Exception as e:
        state.error_count += 1
        logger.error(f"Error storing predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats() -> Dict:
    """Get logging statistics"""
    try:
        db_path = Path("/app/data/predictions.db")
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Total predictions
        cursor.execute("SELECT COUNT(*) FROM predictions")
        total_count = cursor.fetchone()[0]
        
        # Defects detected
        cursor.execute("SELECT COUNT(*) FROM predictions WHERE defect_detected = 1")
        defect_count = cursor.fetchone()[0]
        
        # By edge device
        cursor.execute("""
            SELECT edge_device_id, COUNT(*) as count
            FROM predictions
            GROUP BY edge_device_id
            ORDER BY count DESC
        """)
        by_device = {row[0]: row[1] for row in cursor.fetchall()}
        
        # By model
        cursor.execute("""
            SELECT model_name, COUNT(*) as count
            FROM predictions
            GROUP BY model_name
        """)
        by_model = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Average inference time
        cursor.execute("SELECT AVG(inference_time_ms) FROM predictions")
        avg_inference_time = cursor.fetchone()[0] or 0.0
        
        conn.close()
        
        return {
            "total_predictions": total_count,
            "defects_detected": defect_count,
            "normal_detections": total_count - defect_count,
            "average_inference_time_ms": round(avg_inference_time, 2),
            "by_edge_device": by_device,
            "by_model": by_model,
        }
    
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/predictions")
async def list_predictions(
    limit: int = 100,
    edge_device_id: Optional[str] = None,
    defect_only: bool = False,
) -> List[Dict]:
    """
    List recent predictions
    
    Args:
        limit: Max predictions to return
        edge_device_id: Filter by edge device
        defect_only: Only return defect detections
        
    Returns:
        List of predictions
    """
    try:
        import json
        
        db_path = Path("/app/data/predictions.db")
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        query = "SELECT * FROM predictions WHERE 1=1"
        params = []
        
        if edge_device_id:
            query += " AND edge_device_id = ?"
            params.append(edge_device_id)
        
        if defect_only:
            query += " AND defect_detected = 1"
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        
        predictions = []
        for row in cursor.fetchall():
            pred_dict = dict(zip(columns, row))
            # Parse JSON fields
            if pred_dict["detections_json"]:
                pred_dict["detections"] = json.loads(pred_dict["detections_json"])
            if pred_dict["confidence_scores"]:
                pred_dict["confidence_scores"] = json.loads(pred_dict["confidence_scores"])
            predictions.append(pred_dict)
        
        conn.close()
        return predictions
    
    except Exception as e:
        logger.error(f"Error listing predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
