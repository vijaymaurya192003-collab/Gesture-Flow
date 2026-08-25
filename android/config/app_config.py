"""
Application Configuration and Runtime Settings
Manages local defaults, paths, camera parameters, and sync URLs.
"""
import os
from pathlib import Path
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    """Core application settings for Gesture Flow."""
    # App Information
    app_name: str = "Gesture Flow"
    app_version: str = "1.0.0"
    debug: bool = False

    # Camera & Vision Pipeline
    camera_index: int = 0
    camera_width: int = 640
    camera_height: int = 480
    target_fps: int = 30
    frame_buffer_size: int = 2
    max_num_hands: int = 1
    min_detection_confidence: float = 0.65
    min_tracking_confidence: float = 0.60

    # Smoothing & Filters
    smoothing_factor: float = 0.65  # EMA smoothing alpha (0.0 to 1.0)
    jitter_threshold: float = 0.005  # minimum normalized delta to register move

    # State Machine & Debounce
    default_debounce_ms: int = 400
    pinch_hold_time_ms: int = 80
    swipe_min_velocity: float = 0.85
    swipe_window_frames: int = 5

    # Storage Paths
    storage_dir: Path = Field(default_factory=lambda: Path(os.path.expanduser("~/.gestureflow")))
    db_path: Path = Field(default_factory=lambda: Path(os.path.expanduser("~/.gestureflow/local_cache.db")))

    # Cloud Sync & Backend
    api_base_url: str = os.getenv("API_BASE_URL", "https://gesture-flow-mno2.onrender.com/api/v1")
    sync_interval_seconds: int = 60
    offline_mode: bool = False

    def ensure_directories(self) -> None:
        """Create required local directories if they don't exist."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)


# Global configuration singleton
config = AppConfig()
config.ensure_directories()

