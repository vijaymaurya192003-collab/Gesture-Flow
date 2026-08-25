"""
Usage Statistics and Telemetry Schemas
"""
from typing import Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class StatsRecord(BaseModel):
    """Telemetry report for gesture usage counts (No video/camera data)."""
    session_duration_seconds: float = 0.0
    gesture_counts: Dict[str, int] = Field(default_factory=dict)
    average_fps: float = 0.0
    app_version: str = "1.0.0"
    platform: str = "Android"


class StatsSummary(BaseModel):
    """Aggregated usage statistics."""
    user_id: str
    total_sessions: int = 0
    total_duration_seconds: float = 0.0
    gesture_breakdown: Dict[str, int] = Field(default_factory=dict)
    last_active: Optional[str] = None

