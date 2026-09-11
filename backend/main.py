"""
Gesture Flow FastAPI Application
Main backend API entry point for cloud synchronization with MongoDB Atlas on Render.
"""
import sys
import os

# Guarantee repository root is in python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.database import db_manager
from backend.routes.auth_routes import router as auth_router
from backend.routes.mapping_routes import router as mapping_router
from backend.routes.settings_routes import router as settings_router
from backend.routes.calibration_routes import router as calibration_router
from backend.routes.stats_routes import router as stats_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifespan hooks."""
    print("[FastAPI] Starting Gesture Flow Backend...")
    await db_manager.connect_db()
    yield
    print("[FastAPI] Shutting down Gesture Flow Backend...")
    await db_manager.close_db()


app = FastAPI(
    title="Gesture Flow Cloud API",
    description="Secure REST API backend for Gesture Flow touchless HCI system, synchronizing with MongoDB Atlas.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for Vercel Web Dashboard, Capacitor Android Mobile App, and local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers under root, /api, and /api/v1
for prefix in ["", "/api", "/api/v1"]:
    app.include_router(auth_router, prefix=prefix)
    app.include_router(mapping_router, prefix=prefix)
    app.include_router(settings_router, prefix=prefix)
    app.include_router(calibration_router, prefix=prefix)
    app.include_router(stats_router, prefix=prefix)


@app.get("/health", tags=["Health"])
async def health_check():
    """
    System health check endpoint.
    Verifies backend status and database liveliness without exposing credentials.
    """
    db_connected = False
    if db_manager.is_connected:
        db_connected = await db_manager.ping_db()

    return {
        "status": "healthy",
        "service": "Gesture Flow API",
        "version": "1.0.0",
        "database": "connected" if db_connected else ("in-memory fallback" if not db_manager.is_connected else "degraded"),
        "database_name": settings.mongodb_database,
        "environment": settings.environment
    }


@app.get("/", tags=["Root"])
async def root():
    """Root metadata endpoint."""
    return {
        "message": "Welcome to Gesture Flow Cloud API",
        "docs_url": "/docs",
        "health_url": "/health",
        "api_v1_prefix": "/api/v1"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.host, port=settings.port, reload=True)
