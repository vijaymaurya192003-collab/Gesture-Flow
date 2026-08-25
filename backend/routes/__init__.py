"""
Backend API Routes
"""
from backend.routes.auth_routes import router as auth_router
from backend.routes.mapping_routes import router as mapping_router
from backend.routes.settings_routes import router as settings_router
from backend.routes.calibration_routes import router as calibration_router
from backend.routes.stats_routes import router as stats_router

__all__ = [
    "auth_router",
    "mapping_router",
    "settings_router",
    "calibration_router",
    "stats_router"
]

