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

    def __init__(
        self,
        base_alpha: float = 0.65,
        jitter_threshold: float = 0.004,
        z_jitter_threshold: float = 0.003
    ):
        self.base_alpha = base_alpha
        self.jitter_threshold = jitter_threshold
        self.z_jitter_threshold = z_jitter_threshold
        self._prev_landmarks: Optional[List[LandmarkPoint]] = None

    def smooth(self, current_landmarks: List[LandmarkPoint]) -> List[LandmarkPoint]:
        """
        Smooth incoming landmarks against previous frame coordinates.
        Uses independent 3D deadbands to preserve intentional Z-axis depth motion
        (such as air taps) while suppressing hand tremor in X/Y.
        """
        if not current_landmarks:
            self._prev_landmarks = None
            return []

        if self._prev_landmarks is None or len(self._prev_landmarks) != len(current_landmarks):
            self._prev_landmarks = current_landmarks
            return current_landmarks

        smoothed: List[LandmarkPoint] = []

        for curr, prev in zip(current_landmarks, self._prev_landmarks):
            dx = curr.x - prev.x
            dy = curr.y - prev.y
            dz = curr.z - prev.z

            dist_xy = float(np.sqrt(dx * dx + dy * dy))
            dist_z = float(abs(dz))

            # 3D Jitter deadband: If motion across all dimensions is negligible, lock coordinate
            if dist_xy < self.jitter_threshold and dist_z < self.z_jitter_threshold:
                smoothed.append(prev)
                continue

            # Independent X/Y smoothing with deadband: prevents pointer drift during Z-tap
            if dist_xy < self.jitter_threshold:
                new_x = prev.x
                new_y = prev.y
            else:
                dynamic_alpha_xy = float(np.clip(self.base_alpha + dist_xy * 2.0, 0.25, 0.95))
                new_x = prev.x + dynamic_alpha_xy * dx
                new_y = prev.y + dynamic_alpha_xy * dy

            # Independent Z smoothing with deadband: preserves forward air-tap poke
            if dist_z < self.z_jitter_threshold:
                new_z = prev.z
            else:
                dynamic_alpha_z = float(np.clip(self.base_alpha + dist_z * 2.0, 0.25, 0.95))
                new_z = prev.z + dynamic_alpha_z * dz

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

