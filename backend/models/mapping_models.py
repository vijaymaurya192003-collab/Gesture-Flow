"""
Gesture Mapping Schemas
"""
from typing import Optional
from pydantic import BaseModel, Field


class MappingCreate(BaseModel):
    """Create or update gesture mapping."""
    gesture: str
    action: str
    sensitivity: float = Field(default=1.0, ge=0.1, le=5.0)
    confidence_threshold: float = Field(default=0.70, ge=0.40, le=0.99)
    cooldown_ms: int = Field(default=400, ge=10, le=5000)
    enabled: bool = True
    description: Optional[str] = ""


class MappingUpdate(BaseModel):
    """Update existing mapping parameters."""
    action: Optional[str] = None
    sensitivity: Optional[float] = None
    confidence_threshold: Optional[float] = None
    cooldown_ms: Optional[int] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None


class MappingResponse(BaseModel):
    """Mapping response item."""
    user_id: Optional[str] = None
    gesture: str
    action: str
    sensitivity: float
    confidence_threshold: float
    cooldown_ms: int
    enabled: bool
    description: str = ""

