"""
Calibration Profile Schemas
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class CalibrationUpdate(BaseModel):
    """Payload to update calibration profile."""
    pinch_threshold: Optional[float] = Field(default=None, ge=0.10, le=0.80)
    hand_scale_baseline: Optional[float] = Field(default=None, ge=0.10, le=0.80)
    hand_size_baseline: Optional[float] = Field(default=None, ge=0.10, le=0.80)
    jitter_deadband: Optional[float] = Field(default=None, ge=0.0001, le=0.08)
    neutral_jitter_std: Optional[float] = Field(default=None, ge=0.0001, le=0.08)
    confidence_threshold: Optional[float] = Field(default=None, ge=0.40, le=0.95)
    min_confidence_floor: Optional[float] = Field(default=None, ge=0.40, le=0.95)


class CalibrationResponse(BaseModel):
    """Calibration response model."""
    user_id: str
    pinch_threshold: float = 0.45
    hand_scale_baseline: float = 0.20
    hand_size_baseline: float = 0.20
    jitter_deadband: float = 0.012
    neutral_jitter_std: float = 0.012
    confidence_threshold: float = 0.70
    min_confidence_floor: float = 0.70
    calibrated_at: Optional[str] = None
