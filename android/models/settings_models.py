"""
Settings and Calibration Models
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class CalibrationProfileModel(BaseModel):
    """Hand calibration baseline for specific user hand size and resting posture."""
    profile_id: str = "default"
    user_id: Optional[str] = None
    pinch_threshold: float = 0.35  # Normalized distance between thumb & index tip
    hand_size_baseline: float = 0.35  # Wrist to middle finger tip baseline
    neutral_jitter_std: float = 0.003
    min_confidence_floor: float = 0.60
    calibrated_at: Optional[str] = None


class UserSettingsModel(BaseModel):
    """User preferences, UI theme, and camera parameters."""
    user_id: Optional[str] = None
    theme: str = "Dark"
    camera_resolution: str = "640x480"
    target_fps: int = 30
    pointer_sensitivity: float = 1.2
    scroll_sensitivity: float = 1.0
    global_cooldown_multiplier: float = 1.0
    show_landmark_overlay: bool = True
    show_hud_metrics: bool = True
    vibration_feedback: bool = True
    cloud_sync_enabled: bool = True
    extra_preferences: Dict[str, Any] = Field(default_factory=dict)

