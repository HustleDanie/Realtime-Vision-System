"""
Example: Integrating Structured Logging and Prometheus Metrics
into the Inference Service

This shows how to add logging and metrics to the existing FastAPI
inference service with minimal code changes.
"""

# ===== ORIGINAL INFERENCE SERVICE WITH LOGGING & METRICS =====

from fastapi import FastAPI, Response
from pydantic import BaseModel
import torch
import mlflow
import mlflow.pytorch
from datetime import datetime
import time

# NEW: Import monitoring utilities
from src.monitoring.structured_logging import (
    setup_structured_logging,
    MetricsRegistry,
    log_prediction,
    LogContext,
    log_data_quality,
)

# ===== SETUP =====

app = FastAPI(title="Inference Service")

# NEW: Initialize structured logging
logger = setup_structured_logging(
    service_name='inference-service',
    log_level='INFO',
    log_format='json'
)

# NEW: Initialize Prometheus metrics
metrics = MetricsRegistry('inference-service')

# NEW: Data quality logging
log_validation_error = log_data_quality(logger, metrics)

# Existing setup
MODEL_NAME = "cifar10-model"
MODEL_STAGE = "Production"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

model = None


class InferenceRequest(BaseModel):
    data: list


# ===== STARTUP EVENT (Enhanced with Logging) =====

@app.on_event("startup")
async def startup_event():
    global model
    
    # NEW: Use logging context
    with LogContext(logger, 'model_loading', model=MODEL_NAME, stage=MODEL_STAGE):
        try:
            model_load_start = time.time()
            
            # NEW: Log startup step
            logger.info(
                'mlflow_connecting',
                extra={
                    'service': 'inference',
                    'mlflow_tracking_uri': 'http://mlflow:5000',  # or your URI
                }
            )
            
            # Load model
            model_uri = f"models:/{MODEL_NAME}/{MODEL_STAGE}"
            model = mlflow.pytorch.load_model(model_uri)
            model.to(DEVICE)
            model.eval()
            
            # NEW: Record model load time
            load_time = time.time() - model_load_start
            metrics.model_load_time.labels(model=MODEL_NAME).observe(load_time)
            metrics.model_loaded.labels(model=MODEL_NAME).set(1)
            
            logger.info(
                'model_loaded_successfully',
                extra={
                    'service': 'inference',
                    'model': MODEL_NAME,
                    'device': DEVICE,
                    'load_time_seconds': round(load_time, 4),
                }
            )
        
        except Exception as e:
            metrics.model_loaded.labels(model=MODEL_NAME).set(0)
            
            logger.error(
                'model_load_failed',
                extra={
                    'service': 'inference',
                    'model': MODEL_NAME,
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                }
            )
            raise


# ===== PREDICTION ENDPOINT (Enhanced with Logging & Metrics) =====

@app.post("/predict")
def predict(request: InferenceRequest, response: Response):
    """
    Serve predictions with logging and metrics.
    """
    try:
        # NEW: Log input validation
        if not request.data:
            logger.warning(
                'empty_input_received',
                extra={'service': 'inference', 'model': MODEL_NAME}
            )
            log_validation_error(MODEL_NAME, 'empty_input', {})
            response.status_code = 400
            return {"error": "Empty input"}
        
        # NEW: Start timing prediction
        prediction_start = time.time()
        
        # NEW: Log prediction details
        logger.debug(
            'prediction_input_received',
            extra={
                'service': 'inference',
                'model': MODEL_NAME,
                'input_shape': [len(request.data)],
                'input_size_bytes': len(str(request.data)),
            }
        )
        
        # Original prediction code
        x = torch.tensor(request.data, dtype=torch.float32, device=DEVICE)
        x = x.view(1, 3, 32, 32)
        
        # NEW: Validate tensor shape
        expected_shape = (1, 3, 32, 32)
        if x.shape != expected_shape:
            logger.error(
                'invalid_tensor_shape',
                extra={
                    'service': 'inference',
                    'model': MODEL_NAME,
                    'expected': expected_shape,
                    'got': tuple(x.shape),
                }
            )
            log_validation_error(
                MODEL_NAME,
                'invalid_shape',
                {'expected': expected_shape, 'got': tuple(x.shape)}
            )
            response.status_code = 400
            return {"error": f"Invalid shape: expected {expected_shape}, got {x.shape}"}
        
        # Run inference
        with torch.no_grad():
            logits = model(x)
            probs = torch.softmax(logits, dim=1)
            pred = torch.argmax(probs, dim=1).item()
            confidence = probs[0, pred].item()
        
        # Calculate latency
        latency = time.time() - prediction_start
        
        # NEW: Log successful prediction
        logger.info(
            'prediction_successful',
            extra={
                'service': 'inference',
                'model': MODEL_NAME,
                'class': int(pred),
                'confidence': round(float(confidence), 4),
                'latency_seconds': round(latency, 4),
                'device': DEVICE,
            }
        )
        
        # NEW: Record metrics
        metrics.predictions_total.labels(
            model=MODEL_NAME,
            status='success'
        ).inc()
        metrics.prediction_latency.labels(model=MODEL_NAME).observe(latency)
        metrics.prediction_confidence.labels(model=MODEL_NAME).observe(confidence)
        
        return {
            "class": int(pred),
            "confidence": float(confidence),
            "latency_ms": round(latency * 1000, 2),
        }
    
    except torch.cuda.OutOfMemoryError as e:
        logger.error(
            'cuda_out_of_memory',
            extra={
                'service': 'inference',
                'model': MODEL_NAME,
                'error_message': str(e),
            }
        )
        metrics.prediction_errors.labels(
            model=MODEL_NAME,
            error_type='cuda_oom'
        ).inc()
        response.status_code = 503
        return {"error": "GPU out of memory"}
    
    except Exception as e:
        latency = time.time() - prediction_start
        
        # NEW: Log error with full context
        logger.error(
            'prediction_error',
            extra={
                'service': 'inference',
                'model': MODEL_NAME,
                'error_type': type(e).__name__,
                'error_message': str(e),
                'latency_seconds': round(latency, 4),
            }
        )
        
        # NEW: Record error metric
        metrics.prediction_errors.labels(
            model=MODEL_NAME,
            error_type=type(e).__name__
        ).inc()
        
        response.status_code = 500
        return {"error": str(e)}


# ===== METRICS ENDPOINT (NEW) =====

@app.get("/metrics")
def metrics_endpoint():
    """Prometheus metrics endpoint for scraping."""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    
    logger.debug(
        'metrics_requested',
        extra={'service': 'inference', 'endpoint': '/metrics'}
    )
    
    return generate_latest(metrics.registry)


# ===== HEALTH ENDPOINTS (Keep existing) =====

@app.get("/health")
def health(response: Response):
    """Liveness probe."""
    logger.debug('health_check_requested', extra={'service': 'inference'})
    return {
        "status": "healthy",
        "service": "inference-service",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/ready")
def ready(response: Response):
    """Readiness probe."""
    logger.debug('readiness_check_requested', extra={'service': 'inference'})
    
    if model is None:
        logger.warning('model_not_loaded', extra={'service': 'inference'})
        response.status_code = 503
        return {"status": "not_ready", "reason": "model_not_loaded"}
    
    return {
        "status": "ready",
        "model_loaded": True,
        "timestamp": datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info(
        'starting_service',
        extra={
            'service': 'inference',
            'host': '0.0.0.0',
            'port': 8000,
        }
    )
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
