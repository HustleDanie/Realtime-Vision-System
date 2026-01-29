"""
Minimal real-time inference service that pulls the latest Production model
from MLflow Model Registry and serves predictions via FastAPI.

Health check endpoints for Kubernetes:
- GET /health: Basic liveness check
- GET /ready: Readiness check (model loaded, dependencies available)
"""

import os
import sys
import mlflow
import mlflow.pytorch
import torch
from fastapi import FastAPI, Response
from pydantic import BaseModel
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration (override via env vars)
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
MODEL_NAME = os.getenv("MODEL_NAME", "simple-cnn-demo")
MODEL_STAGE = os.getenv("MODEL_STAGE", "Production")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

app = FastAPI(title="Realtime Inference Service", version="1.0")

# Global state tracking
class ServiceState:
    def __init__(self):
        self.model = None
        self.model_loaded = False
        self.startup_time = None
        self.last_prediction_time = None
        self.prediction_count = 0
        self.error_count = 0
        self.mlflow_accessible = False

state = ServiceState()

class InferenceRequest(BaseModel):
    # Expect flattened 3x32x32 image (use your own schema as needed)
    data: list[float]  # length must be 3*32*32 = 3072 for this demo


def load_production_model():
    """Load the latest Production model from MLflow Registry."""
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        
        # Test MLflow connectivity
        mlflow.tracking.MlflowClient().search_registered_models(max_results=1)
        state.mlflow_accessible = True
        logger.info(f"MLflow accessible at {MLFLOW_TRACKING_URI}")
        
        # Load model
        model_uri = f"models:/{MODEL_NAME}/{MODEL_STAGE}"
        logger.info(f"Loading model from {model_uri}")
        model = mlflow.pytorch.load_model(model_uri)
        model.to(DEVICE)
        model.eval()
        
        state.model = model
        state.model_loaded = True
        logger.info(f"Model {MODEL_NAME} ({MODEL_STAGE}) loaded successfully")
        return model
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        state.model_loaded = False
        raise


@app.on_event("startup")
def startup_event():
    """Initialize service and load model on startup."""
    state.startup_time = datetime.utcnow().isoformat()
    logger.info("Service starting up...")
    try:
        load_production_model()
        logger.info("Startup complete")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        # Continue anyway, let readiness probe catch it


# ===== HEALTH CHECK ENDPOINTS (for Kubernetes monitoring) =====

@app.get("/health")
def health(response: Response):
    """
    Liveness probe: Check if container is alive.
    
    Returns 200 if service is running (even if not fully ready).
    Kubernetes will restart container if this fails.
    """
    try:
        logger.debug("Health check requested")
        return {
            "status": "healthy",
            "service": "inference-service",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": (datetime.utcnow() - datetime.fromisoformat(state.startup_time)).total_seconds() if state.startup_time else 0,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        response.status_code = 500
        return {"status": "unhealthy", "error": str(e)}


@app.get("/ready")
def ready(response: Response):
    """
    Readiness probe: Check if service is ready to accept traffic.
    
    Returns 200 only if:
    - Model is loaded
    - MLflow is accessible
    - No recent errors
    
    Kubernetes will not route traffic to pod if this fails.
    """
    try:
        logger.debug("Readiness check requested")
        
        # Check model is loaded
        if not state.model_loaded:
            logger.warning("Model not loaded")
            response.status_code = 503
            return {"status": "not_ready", "reason": "model_not_loaded"}
        
        # Check MLflow is accessible
        if not state.mlflow_accessible:
            logger.warning("MLflow not accessible")
            response.status_code = 503
            return {"status": "not_ready", "reason": "mlflow_not_accessible"}
        
        # Check error rate (if too many errors, not ready)
        if state.prediction_count > 0:
            error_rate = state.error_count / state.prediction_count
            if error_rate > 0.5:  # More than 50% errors
                logger.warning(f"High error rate: {error_rate:.2%}")
                response.status_code = 503
                return {
                    "status": "not_ready",
                    "reason": "high_error_rate",
                    "error_rate": error_rate
                }
        
        return {
            "status": "ready",
            "model_loaded": state.model_loaded,
            "mlflow_accessible": state.mlflow_accessible,
            "predictions_served": state.prediction_count,
            "errors": state.error_count,
            "last_prediction": state.last_prediction_time,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        response.status_code = 503
        return {"status": "not_ready", "error": str(e)}


@app.get("/metrics")
def metrics(response: Response):
    """
    Prometheus metrics endpoint.
    
    Provides metrics for monitoring:
    - Predictions served
    - Errors encountered
    - Model info
    """
    try:
        metrics_output = []
        
        # Model metrics
        metrics_output.append(f"# HELP inference_model_loaded Whether model is loaded")
        metrics_output.append(f"# TYPE inference_model_loaded gauge")
        metrics_output.append(f"inference_model_loaded{{model=\"{MODEL_NAME}\",stage=\"{MODEL_STAGE}\"}} {1 if state.model_loaded else 0}")
        
        # Prediction metrics
        metrics_output.append(f"# HELP inference_predictions_total Total predictions served")
        metrics_output.append(f"# TYPE inference_predictions_total counter")
        metrics_output.append(f"inference_predictions_total{{model=\"{MODEL_NAME}\"}} {state.prediction_count}")
        
        metrics_output.append(f"# HELP inference_errors_total Total prediction errors")
        metrics_output.append(f"# TYPE inference_errors_total counter")
        metrics_output.append(f"inference_errors_total{{model=\"{MODEL_NAME}\"}} {state.error_count}")
        
        # MLflow metrics
        metrics_output.append(f"# HELP inference_mlflow_accessible Whether MLflow is accessible")
        metrics_output.append(f"# TYPE inference_mlflow_accessible gauge")
        metrics_output.append(f"inference_mlflow_accessible 1" if state.mlflow_accessible else "inference_mlflow_accessible 0")
        
        response.media_type = "text/plain; charset=utf-8"
        return "\n".join(metrics_output)
    except Exception as e:
        logger.error(f"Metrics endpoint failed: {e}")
        response.status_code = 500
        return f"# Error generating metrics: {e}"

# ===== PREDICTION ENDPOINT =====

@app.post("/predict")
def predict(request: InferenceRequest, response: Response):
    """Serve predictions using the loaded model."""
    try:
        # Convert flat list to tensor [1, 3, 32, 32]
        x = torch.tensor(request.data, dtype=torch.float32, device=DEVICE)
        x = x.view(1, 3, 32, 32)
        with torch.no_grad():
            logits = state.model(x)
            probs = torch.softmax(logits, dim=1)
            pred = torch.argmax(probs, dim=1).item()
            confidence = probs[0, pred].item()
        
        state.prediction_count += 1
        state.last_prediction_time = datetime.utcnow().isoformat()
        logger.info(f"Prediction served (total: {state.prediction_count})")
        
        return {
            "class": int(pred),
            "confidence": confidence,
        }
    except Exception as e:
        state.error_count += 1
        logger.error(f"Prediction failed: {e}")
        response.status_code = 500
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
