from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.monitoring_api.routers import inspection_logs, metrics, model_status, health

app = FastAPI(
    title="AI Monitoring Dashboard API",
    version="1.0.0",
    description="Backend API for inspection logs, metrics, model status, and system health.",
)

# CORS middleware for frontend connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(inspection_logs.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(model_status.router, prefix="/api")
app.include_router(health.router, prefix="/api")


@app.get("/")
def root():
    return {"message": "AI Monitoring Dashboard API"}
