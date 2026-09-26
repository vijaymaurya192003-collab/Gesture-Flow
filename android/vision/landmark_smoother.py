"""
Landmark Smoothing Filter
Applies adaptive Exponential Moving Average (EMA) and jitter deadbands to stabilize hand coordinates.
"""
from typing import List, Optional
import numpy as np
from android.models.gesture_models import LandmarkPoint


class LandmarkSmoother:
    """
    Adaptive Exponential Moving Average (EMA) smoothing for 21 hand landmarks.
    Eliminates camera sensor noise and physiological hand tremor.
    """

    def __init__(self, base_alpha: float = 0.65, jitter_threshold: float = 0.004):
        self.base_alpha = base_alpha
        self.jitter_threshold = jitter_threshold
        self._prev_landmarks: Optional[List[LandmarkPoint]] = None

    def smooth(self, current_landmarks: List[LandmarkPoint]) -> List[LandmarkPoint]:
        """
        Smooth incoming landmarks against previous frame coordinates.
        """
        if not current_landmarks:
            self._prev_landmarks = None
            return []

        if self._prev_landmarks is None or len(self._prev_landmarks) != len(current_landmarks):
            self._prev_landmarks = current_landmarks
            return current_landmarks

        smoothed: List[LandmarkPoint] = []

        for curr, prev in zip(current_landmarks, self._prev_landmarks):
            # Compute movement Euclidean distance
            dx = curr.x - prev.x
            dy = curr.y - prev.y
            dz = curr.z - prev.z
            dist = np.sqrt(dx * dx + dy * dy + dz * dz)

            # Jitter deadband: If motion is negligible, lock to previous coordinate
            if dist < self.jitter_threshold:
                smoothed.append(prev)
                continue

            # Adaptive alpha: fast movements increase alpha (lower latency), slow movements decrease alpha (higher smoothing)
            dynamic_alpha = np.clip(self.base_alpha + dist * 2.0, 0.25, 0.95)

            new_x = prev.x + dynamic_alpha * (curr.x - prev.x)
            new_y = prev.y + dynamic_alpha * (curr.y - prev.y)
            new_z = prev.z + dynamic_alpha * (curr.z - prev.z)

            smoothed.append(
                LandmarkPoint(
                    x=float(new_x),
                    y=float(new_y),
                    z=float(new_z),
                    visibility=curr.visibility
                )
            )

        self._prev_landmarks = smoothed
        return smoothed

    def reset(self) -> None:
        """Reset smoother state."""
        self._prev_landmarks = None

