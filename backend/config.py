"""
FastAPI Backend Configuration
Loads settings from environment variables and local .env with safe defaults.
Never hardcodes credentials or secrets.
"""
import os
from typing import List
from pydantic import BaseModel


def _load_env_file() -> None:
    """Native .env loader without third-party dependencies."""
    possible_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        os.path.join(os.getcwd(), ".env"),
        ".env"
    ]
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k not in os.environ:
                                os.environ[k] = v
                break
            except Exception:
                pass


_load_env_file()


def _get_int_env(key: str, default: int) -> int:
    val = os.getenv(key)
    if val and val.strip().isdigit():
        return int(val.strip())
    return default


class BackendSettings(BaseModel):
    """Configuration settings for FastAPI server."""
    app_name: str = "Gesture Flow Cloud API"
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "False").lower() in ("true", "1")

    # Server Binding
    port: int = _get_int_env("PORT", 8000)
    host: str = os.getenv("HOST", "0.0.0.0")

    # JWT Authentication
    jwt_secret: str = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY") or "gestureflow_default_dev_secret_key_change_in_prod"
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM") or os.getenv("ALGORITHM") or "HS256"
    access_token_expire_minutes: int = _get_int_env("ACCESS_TOKEN_EXPIRE_MINUTES", 1440)

    # MongoDB Atlas Connection
    mongodb_uri: str = os.getenv("MONGODB_URI", "")
    mongodb_database: str = os.getenv("MONGODB_DB") or os.getenv("MONGODB_DATABASE") or os.getenv("MONGODB_DB_NAME") or "gesture_flow"

    @property
    def cors_origins(self) -> List[str]:
        env_cors = os.getenv("CORS_ORIGINS")
        origins = []
        if env_cors:
            origins = [orig.strip() for orig in env_cors.split(",") if orig.strip() and orig.strip() != "*"]
        else:
            origins = [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
                "https://gestureflow.vercel.app",
                "https://gesture-flow.vercel.app",
                "https://gesture-flow-dun.vercel.app",
            ]
        
        # Always guarantee Android Capacitor and localhost WebView origins
        for mobile_origin in ["https://localhost", "capacitor://localhost", "http://localhost"]:
            if mobile_origin not in origins:
                origins.append(mobile_origin)
        
        return origins


settings = BackendSettings()
