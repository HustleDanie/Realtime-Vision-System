from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.monitoring_api.routers import inspection_logs, metrics, model_status, health, prediction, retraining, labeling, export, performance
from src.monitoring_api.performance_monitor import PerformanceMonitoringMiddleware
from src.logging_service.database import DatabaseConnection

app = FastAPI(
    title="AI Monitoring Dashboard API",
    version="1.0.0",
    description="Backend API for inspection logs, metrics, model status, and system health.",
)

# Add performance monitoring middleware
app.add_middleware(PerformanceMonitoringMiddleware)

# CORS middleware for frontend connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://localhost:3003",
        "http://127.0.0.1:3003",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(inspection_logs.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(model_status.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(prediction.router, prefix="/api")
app.include_router(retraining.router, prefix="/api")
app.include_router(labeling.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(performance.router, prefix="/api")

# Initialize database connections
@app.on_event("startup")
async def startup_event():
    """Initialize database connections on startup."""
    db_conn = DatabaseConnection()
    retraining.set_db_connection(db_conn)
    labeling.set_db_connection(db_conn)


@app.get("/")
def root():
    return {"message": "AI Monitoring Dashboard API"}

