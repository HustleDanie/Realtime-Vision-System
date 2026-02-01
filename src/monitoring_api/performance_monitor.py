"""Performance monitoring middleware and utilities for endpoint tracking."""

import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from datetime import datetime
from collections import defaultdict
from typing import Dict, List


# In-memory metrics storage
endpoint_metrics: Dict[str, List[dict]] = defaultdict(list)
MAX_SAMPLES_PER_ENDPOINT = 1000  # Keep last 1000 requests per endpoint


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track endpoint performance metrics.
    Collects latency, throughput, and error rates.
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        # Get endpoint path
        path = request.url.path
        method = request.method
        endpoint = f"{method} {path}"
        
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            
            # Record metric
            metric = {
                "timestamp": datetime.now().isoformat(),
                "duration_ms": duration_ms,
                "status_code": response.status_code,
                "success": 200 <= response.status_code < 300,
            }
            
            # Add to metrics
            if len(endpoint_metrics[endpoint]) >= MAX_SAMPLES_PER_ENDPOINT:
                endpoint_metrics[endpoint].pop(0)
            endpoint_metrics[endpoint].append(metric)
            
            # Add custom headers for response time
            response.headers["X-Response-Time"] = str(duration_ms)
            response.headers["X-Endpoint"] = endpoint
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # Record error metric
            metric = {
                "timestamp": datetime.now().isoformat(),
                "duration_ms": duration_ms,
                "status_code": 500,
                "success": False,
                "error": str(e),
            }
            
            if len(endpoint_metrics[endpoint]) >= MAX_SAMPLES_PER_ENDPOINT:
                endpoint_metrics[endpoint].pop(0)
            endpoint_metrics[endpoint].append(metric)
            
            raise


def get_endpoint_metrics(endpoint: str = None) -> dict:
    """
    Get performance metrics for specific endpoint or all endpoints.
    
    Returns:
        - Endpoint name
        - Total requests
        - Average latency
        - Min/Max latency
        - Success rate
        - Error rate
        - Throughput (requests/second)
    """
    if endpoint and endpoint in endpoint_metrics:
        metrics_list = endpoint_metrics[endpoint]
    elif endpoint:
        return {"error": f"No metrics for endpoint {endpoint}"}
    else:
        # Combine all metrics
        metrics_list = []
        for all_metrics in endpoint_metrics.values():
            metrics_list.extend(all_metrics)
    
    if not metrics_list:
        return {"endpoints": {}, "total_requests": 0}
    
    results = {}
    
    # Group by endpoint if getting all
    if not endpoint:
        for ep, metrics in endpoint_metrics.items():
            if not metrics:
                continue
            
            durations = [m["duration_ms"] for m in metrics]
            successes = sum(1 for m in metrics if m["success"])
            
            results[ep] = {
                "total_requests": len(metrics),
                "successful_requests": successes,
                "failed_requests": len(metrics) - successes,
                "success_rate": (successes / len(metrics)) * 100,
                "error_rate": ((len(metrics) - successes) / len(metrics)) * 100,
                "latency_ms": {
                    "avg": sum(durations) / len(durations),
                    "min": min(durations),
                    "max": max(durations),
                    "median": sorted(durations)[len(durations) // 2],
                    "p95": sorted(durations)[int(len(durations) * 0.95)] if len(durations) > 1 else durations[0],
                    "p99": sorted(durations)[int(len(durations) * 0.99)] if len(durations) > 1 else durations[0],
                },
                "recent_samples": metrics[-10:],  # Last 10 requests
            }
    else:
        # Single endpoint metrics
        durations = [m["duration_ms"] for m in metrics_list]
        successes = sum(1 for m in metrics_list if m["success"])
        
        results = {
            "endpoint": endpoint,
            "total_requests": len(metrics_list),
            "successful_requests": successes,
            "failed_requests": len(metrics_list) - successes,
            "success_rate": (successes / len(metrics_list)) * 100,
            "error_rate": ((len(metrics_list) - successes) / len(metrics_list)) * 100,
            "latency_ms": {
                "avg": sum(durations) / len(durations),
                "min": min(durations),
                "max": max(durations),
                "median": sorted(durations)[len(durations) // 2],
                "p95": sorted(durations)[int(len(durations) * 0.95)] if len(durations) > 1 else durations[0],
                "p99": sorted(durations)[int(len(durations) * 0.99)] if len(durations) > 1 else durations[0],
            },
            "recent_samples": metrics_list[-10:],
        }
    
    return results


def reset_metrics(endpoint: str = None):
    """Reset metrics for specific endpoint or all endpoints."""
    if endpoint:
        if endpoint in endpoint_metrics:
            endpoint_metrics[endpoint].clear()
    else:
        endpoint_metrics.clear()
