"""Performance monitoring endpoints for tracking API metrics."""

from fastapi import APIRouter, Query
from src.monitoring_api.performance_monitor import get_endpoint_metrics, reset_metrics

router = APIRouter(prefix="/performance", tags=["performance"])


@router.get("/metrics")
def get_performance_metrics(
    endpoint: str = Query(None, description="Specific endpoint (optional)"),
):
    """
    Get performance metrics for endpoints.
    
    Includes:
    - Total requests and success rate
    - Latency statistics (avg, min, max, p95, p99)
    - Error rates
    - Recent request samples
    
    Example: /performance/metrics?endpoint=POST%20/api/predict/upload
    """
    return get_endpoint_metrics(endpoint)


@router.get("/metrics/summary")
def get_performance_summary():
    """
    Get high-level performance summary across all endpoints.
    Quick overview of system health and throughput.
    """
    metrics = get_endpoint_metrics()
    
    if not metrics.get("endpoints") and not metrics:
        return {
            "total_endpoints": 0,
            "total_requests": 0,
            "avg_success_rate": 0,
            "overall_avg_latency_ms": 0,
        }
    
    endpoints = metrics if isinstance(metrics, dict) else {}
    total_requests = sum(m.get("total_requests", 0) for m in endpoints.values())
    total_successes = sum(m.get("successful_requests", 0) for m in endpoints.values())
    
    all_latencies = []
    for ep_metrics in endpoints.values():
        if "recent_samples" in ep_metrics:
            all_latencies.extend([s.get("duration_ms", 0) for s in ep_metrics["recent_samples"]])
    
    avg_latency = sum(all_latencies) / len(all_latencies) if all_latencies else 0
    success_rate = (total_successes / total_requests * 100) if total_requests > 0 else 0
    
    return {
        "total_endpoints": len(endpoints),
        "total_requests": total_requests,
        "successful_requests": total_successes,
        "failed_requests": total_requests - total_successes,
        "overall_success_rate": success_rate,
        "overall_avg_latency_ms": avg_latency,
        "slowest_endpoint": max(
            [(k, v.get("latency_ms", {}).get("avg", 0)) for k, v in endpoints.items()],
            key=lambda x: x[1],
            default=(None, 0)
        )[0],
        "endpoints_tracked": len(endpoints),
    }


@router.post("/metrics/reset")
def reset_performance_metrics(
    endpoint: str = Query(None, description="Specific endpoint (optional)"),
):
    """
    Reset performance metrics.
    Useful for isolating testing periods or performance baselines.
    """
    reset_metrics(endpoint)
    return {
        "status": "ok",
        "message": f"Metrics reset for {endpoint or 'all endpoints'}",
    }


@router.get("/metrics/endpoints")
def list_tracked_endpoints():
    """List all endpoints being tracked with basic stats."""
    metrics = get_endpoint_metrics()
    
    endpoints_list = []
    for ep, stats in metrics.items():
        if isinstance(stats, dict) and "total_requests" in stats:
            endpoints_list.append({
                "endpoint": ep,
                "total_requests": stats.get("total_requests", 0),
                "success_rate": stats.get("success_rate", 0),
                "avg_latency_ms": stats.get("latency_ms", {}).get("avg", 0),
                "p95_latency_ms": stats.get("latency_ms", {}).get("p95", 0),
            })
    
    return {
        "total_tracked": len(endpoints_list),
        "endpoints": endpoints_list,
    }
