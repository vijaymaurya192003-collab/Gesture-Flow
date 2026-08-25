"""
User Settings Schemas
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class SettingsUpdate(BaseModel):
    """Payload to update user settings."""
    theme: Optional[str] = None
    camera_resolution: Optional[str] = None
    target_fps: Optional[int] = Field(default=None, ge=10, le=60)
    pointer_sensitivity: Optional[float] = Field(default=None, ge=0.2, le=5.0)
    scroll_sensitivity: Optional[float] = Field(default=None, ge=0.2, le=5.0)
    global_cooldown_multiplier: Optional[float] = Field(default=None, ge=0.5, le=3.0)
    show_landmark_overlay: Optional[bool] = None
    show_hud_metrics: Optional[bool] = None
    vibration_feedback: Optional[bool] = None
    extra_preferences: Optional[Dict[str, Any]] = None


class SettingsResponse(BaseModel):
    """Settings response model."""
    user_id: str
    theme: str = "Dark"
    camera_resolution: str = "640x480"
    target_fps: int = 30
    pointer_sensitivity: float = 1.2
    scroll_sensitivity: float = 1.0
    global_cooldown_multiplier: float = 1.0
    show_landmark_overlay: bool = True
    show_hud_metrics: bool = True
    vibration_feedback: bool = True
    extra_preferences: Dict[str, Any] = Field(default_factory=dict)

