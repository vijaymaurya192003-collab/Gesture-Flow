"""
Gesture Models and Data Structures
"""
from enum import Enum
from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field


class GestureStateEnum(str, Enum):
    """Lifecycle states of gesture detection."""
    IDLE = "IDLE"
    TRACKING = "TRACKING"
    GESTURE_DETECTED = "GESTURE_DETECTED"
    ACTION_TRIGGERED = "ACTION_TRIGGERED"
    COOLDOWN = "COOLDOWN"


class LandmarkPoint(BaseModel):
    """Normalized 3D hand landmark coordinate."""
    x: float
    y: float
    z: float = 0.0
    visibility: float = 1.0


class PipelineMetrics(BaseModel):
    """Real-time latency instrumentation metrics (in milliseconds)."""
    camera_capture_ms: float = 0.0
    vision_ms: float = 0.0
    smoothing_ms: float = 0.0
    feature_ms: float = 0.0
    classification_ms: float = 0.0
    action_ms: float = 0.0
    total_pipeline_ms: float = 0.0
    fps: float = 0.0


class HandFrameData(BaseModel):
    """Extracted data from a single camera frame."""
    hand_detected: bool = False
    handedness: str = "Right"  # "Left" or "Right"
    landmarks: List[LandmarkPoint] = Field(default_factory=list)
    raw_landmarks: Optional[List[Tuple[float, float, float]]] = None
    bounding_box: Optional[Tuple[int, int, int, int]] = None  # (min_x, min_y, max_x, max_y)
    timestamp: float = 0.0


class GestureResult(BaseModel):
    """Result of gesture classification on a hand frame."""
    gesture: str
    confidence: float
    action: str
    state: GestureStateEnum = GestureStateEnum.IDLE
    pointer_coords: Optional[Tuple[float, float]] = None  # (norm_x, norm_y)
    raw_pinch_distance: Optional[float] = None
    raw_velocity: Optional[Tuple[float, float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    metrics: Optional[PipelineMetrics] = None


class GestureMappingItem(BaseModel):
    """Custom mapping definition for a gesture."""
    gesture: str
    action: str
    sensitivity: float = 1.0
    confidence_threshold: float = 0.70
    cooldown_ms: int = 400
    enabled: bool = True
    description: str = ""
