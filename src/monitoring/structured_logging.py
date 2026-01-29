"""
Structured Logging and Prometheus Metrics for ML Microservices

This module provides:
1. Structured logging (JSON format for log aggregation)
2. Prometheus metrics (model performance, prediction latency, errors)
3. FastAPI integration patterns
"""

import json
import time
import logging
from datetime import datetime
from functools import wraps
from typing import Optional, Dict, Any

from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry
from pythonjsonlogger import jsonlogger


# ===== PROMETHEUS METRICS SETUP =====

class MetricsRegistry:
    """Centralized Prometheus metrics registry for ML services."""
    
    def __init__(self, service_name: str):
        self.registry = CollectorRegistry()
        self.service_name = service_name
        
        # Service info
        self.service_info = Info(
            'service_info',
            'Service information',
            ['service_name', 'version'],
            registry=self.registry
        )
        self.service_info.labels(service_name=service_name, version='1.0.0').inc()
        
        # Prediction metrics
        self.predictions_total = Counter(
            'predictions_total',
            'Total predictions served',
            ['model', 'status'],
            registry=self.registry
        )
        
        self.prediction_latency = Histogram(
            'prediction_latency_seconds',
            'Prediction latency in seconds',
            ['model'],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
            registry=self.registry
        )
        
        self.prediction_confidence = Histogram(
            'prediction_confidence',
            'Prediction confidence scores',
            ['model'],
            buckets=(0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0),
            registry=self.registry
        )
        
        # Model metrics
        self.model_loaded = Gauge(
            'model_loaded',
            'Whether model is loaded (1=yes, 0=no)',
            ['model'],
            registry=self.registry
        )
        
        self.model_load_time = Histogram(
            'model_load_time_seconds',
            'Time to load model in seconds',
            ['model'],
            registry=self.registry
        )
        
        # Error metrics
        self.prediction_errors = Counter(
            'prediction_errors_total',
            'Total prediction errors',
            ['model', 'error_type'],
            registry=self.registry
        )
        
        # Data quality metrics
        self.input_validation_errors = Counter(
            'input_validation_errors_total',
            'Input validation errors',
            ['model', 'error_reason'],
            registry=self.registry
        )
        
        # Request metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.http_request_latency = Histogram(
            'http_request_latency_seconds',
            'HTTP request latency',
            ['method', 'endpoint'],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
            registry=self.registry
        )


# ===== STRUCTURED LOGGING SETUP =====

def setup_structured_logging(
    service_name: str,
    log_level: str = 'INFO',
    log_format: str = 'json'
) -> logging.Logger:
    """
    Set up structured logging with JSON output.
    
    Args:
        service_name: Name of the service for log context
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_format: 'json' for JSON logs, 'text' for text logs
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level))
    
    # Remove default handlers
    logger.handlers.clear()
    
    handler = logging.StreamHandler()
    
    if log_format == 'json':
        formatter = jsonlogger.JsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s %(service)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


# ===== LOGGING DECORATORS =====

def log_prediction(logger: logging.Logger, metrics: Optional[MetricsRegistry] = None):
    """
    Decorator to log and instrument prediction endpoints.
    
    Logs:
    - Input data characteristics
    - Prediction latency
    - Confidence scores
    - Any errors
    
    Metrics:
    - Prediction latency histogram
    - Prediction count
    - Error count
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, request=None, **kwargs):
            start_time = time.time()
            model_name = getattr(request, 'model_name', 'unknown') if request else 'unknown'
            
            try:
                # Log incoming request
                logger.info(
                    'prediction_started',
                    extra={
                        'service': 'inference',
                        'model': model_name,
                        'timestamp': datetime.utcnow().isoformat(),
                        'request_size': len(str(request)) if request else 0,
                    }
                )
                
                # Execute prediction
                result = func(*args, request=request, **kwargs)
                
                # Calculate latency
                latency = time.time() - start_time
                
                # Extract confidence if available
                confidence = result.get('confidence', 0) if isinstance(result, dict) else 0
                
                # Log success
                logger.info(
                    'prediction_completed',
                    extra={
                        'service': 'inference',
                        'model': model_name,
                        'latency_seconds': round(latency, 4),
                        'confidence': round(confidence, 4),
                        'status': 'success',
                    }
                )
                
                # Record metrics
                if metrics:
                    metrics.predictions_total.labels(
                        model=model_name,
                        status='success'
                    ).inc()
                    metrics.prediction_latency.labels(model=model_name).observe(latency)
                    if confidence > 0:
                        metrics.prediction_confidence.labels(model=model_name).observe(confidence)
                
                return result
            
            except Exception as e:
                latency = time.time() - start_time
                
                # Log error
                logger.error(
                    'prediction_failed',
                    extra={
                        'service': 'inference',
                        'model': model_name,
                        'latency_seconds': round(latency, 4),
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        'status': 'error',
                    }
                )
                
                # Record metrics
                if metrics:
                    metrics.predictions_total.labels(
                        model=model_name,
                        status='error'
                    ).inc()
                    metrics.prediction_errors.labels(
                        model=model_name,
                        error_type=type(e).__name__
                    ).inc()
                
                raise
        
        return wrapper
    return decorator


def log_http_request(logger: logging.Logger, metrics: Optional[MetricsRegistry] = None):
    """
    Middleware to log and instrument all HTTP requests.
    
    Logs:
    - HTTP method, endpoint, status code
    - Request/response latency
    - Error details if applicable
    """
    from fastapi import Request
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import Response
    
    class LoggingMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            start_time = time.time()
            
            # Log request start
            logger.info(
                'http_request_started',
                extra={
                    'service': 'api',
                    'method': request.method,
                    'endpoint': request.url.path,
                    'remote_addr': request.client.host if request.client else 'unknown',
                }
            )
            
            try:
                response = await call_next(request)
                latency = time.time() - start_time
                
                # Log request completion
                logger.info(
                    'http_request_completed',
                    extra={
                        'service': 'api',
                        'method': request.method,
                        'endpoint': request.url.path,
                        'status_code': response.status_code,
                        'latency_seconds': round(latency, 4),
                    }
                )
                
                # Record metrics
                if metrics:
                    metrics.http_requests_total.labels(
                        method=request.method,
                        endpoint=request.url.path,
                        status=response.status_code
                    ).inc()
                    metrics.http_request_latency.labels(
                        method=request.method,
                        endpoint=request.url.path
                    ).observe(latency)
                
                return response
            
            except Exception as e:
                latency = time.time() - start_time
                
                # Log error
                logger.error(
                    'http_request_failed',
                    extra={
                        'service': 'api',
                        'method': request.method,
                        'endpoint': request.url.path,
                        'latency_seconds': round(latency, 4),
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                    }
                )
                
                # Record metrics
                if metrics:
                    metrics.http_requests_total.labels(
                        method=request.method,
                        endpoint=request.url.path,
                        status=500
                    ).inc()
                
                raise
    
    return LoggingMiddleware


def log_data_quality(
    logger: logging.Logger,
    metrics: Optional[MetricsRegistry] = None
):
    """
    Log data quality issues (validation errors, anomalies).
    """
    def log_validation_error(
        model_name: str,
        error_type: str,
        details: Dict[str, Any]
    ):
        logger.warning(
            'data_validation_error',
            extra={
                'service': 'data_quality',
                'model': model_name,
                'error_type': error_type,
                'details': json.dumps(details),
            }
        )
        
        if metrics:
            metrics.input_validation_errors.labels(
                model=model_name,
                error_reason=error_type
            ).inc()
    
    return log_validation_error


# ===== CONTEXT LOGGING =====

class LogContext:
    """Context manager for adding structured context to logs."""
    
    def __init__(
        self,
        logger: logging.Logger,
        operation: str,
        **context
    ):
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(
            f'{self.operation}_started',
            extra={
                'timestamp': datetime.utcnow().isoformat(),
                **self.context,
            }
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        latency = time.time() - self.start_time
        
        if exc_type is None:
            self.logger.info(
                f'{self.operation}_completed',
                extra={
                    'status': 'success',
                    'latency_seconds': round(latency, 4),
                    'timestamp': datetime.utcnow().isoformat(),
                    **self.context,
                }
            )
        else:
            self.logger.error(
                f'{self.operation}_failed',
                extra={
                    'status': 'error',
                    'latency_seconds': round(latency, 4),
                    'error_type': exc_type.__name__,
                    'error_message': str(exc_val),
                    'timestamp': datetime.utcnow().isoformat(),
                    **self.context,
                }
            )


# ===== FASTAPI INTEGRATION EXAMPLE =====

def create_instrumented_app(service_name: str):
    """
    Factory function to create a FastAPI app with logging and metrics.
    
    Returns:
        tuple: (app, logger, metrics)
    """
    from fastapi import FastAPI
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    
    app = FastAPI(title=service_name)
    logger = setup_structured_logging(service_name)
    metrics = MetricsRegistry(service_name)
    
    # Add logging middleware
    app.add_middleware(log_http_request(logger, metrics))
    
    # Add metrics endpoint
    @app.get('/metrics')
    async def metrics_endpoint():
        """Prometheus metrics endpoint."""
        return generate_latest(metrics.registry)
    
    return app, logger, metrics


if __name__ == '__main__':
    # Example usage
    logger = setup_structured_logging('example-service', log_format='json')
    metrics = MetricsRegistry('example-service')
    
    # Example 1: Log with context
    with LogContext(logger, 'model_training', model='cifar10', epoch=1):
        time.sleep(0.1)
    
    # Example 2: Log validation error
    log_error = log_data_quality(logger, metrics)
    log_error('cifar10', 'invalid_shape', {'expected': (3, 32, 32), 'got': (3, 64, 64)})
    
    # Example 3: Simulate metrics
    metrics.predictions_total.labels(model='cifar10', status='success').inc(5)
    metrics.prediction_latency.labels(model='cifar10').observe(0.125)
    metrics.prediction_confidence.labels(model='cifar10').observe(0.95)
