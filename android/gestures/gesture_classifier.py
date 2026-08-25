"""
Rule-Based Geometric Hand Gesture Classifier
Deterministic classifier implementing strict gesture priority:
PINCH -> TWO-FINGER TOUCHPAD -> AIR TAP -> ONE-FINGER SWIPE -> INDEX POINT -> OTHER GESTURES
"""
from typing import List, Tuple, Optional, Deque
from collections import deque
import numpy as np
from android.config.constants import GestureType
from android.models.gesture_models import LandmarkPoint
from android.gestures.feature_extractor import extract_hand_features, HandFeatures
from android.gestures.confidence_engine import ConfidenceEngine


class GestureClassifier:
    """Classifies hand gestures using deterministic 3D geometric heuristics and strict priority."""

    def __init__(
        self,
        pinch_threshold: float = 0.45,
        swipe_velocity_threshold: float = 0.045,
        history_len: int = 5
    ):
        self.pinch_threshold = pinch_threshold
        self.swipe_velocity_threshold = swipe_velocity_threshold
        self._palm_history: Deque[Tuple[float, float]] = deque(maxlen=history_len)

        # Temporal tracking references for continuous pinch, touchpad, and air tap
        self._prev_pinch_distance: Optional[float] = None
        self._prev_two_finger_center: Optional[Tuple[float, float]] = None
        self._prev_index_z: Optional[float] = None

    def set_pinch_threshold(self, threshold: float) -> None:
        """Update calibration pinch sensitivity threshold."""
        self.pinch_threshold = max(0.01, min(1.0, threshold))

    def classify(self, landmarks: List[LandmarkPoint]) -> Tuple[GestureType, float, Optional[HandFeatures]]:
        """
        Classifies current hand landmarks into a GestureType based on strict priority hierarchy.
        Returns: (GestureType, confidence_score [0.0 - 1.0], HandFeatures)
        """
        if not landmarks or len(landmarks) < 21:
            self.reset()
            return GestureType.NONE, 0.0, None

        # Extract features with temporal differential metrics
        features = extract_hand_features(
            landmarks=landmarks,
            history_palm_centers=list(self._palm_history),
            prev_pinch_distance=self._prev_pinch_distance,
            prev_two_finger_center=self._prev_two_finger_center,
            prev_index_z=self._prev_index_z
        )
        if features is None:
            return GestureType.NONE, 0.0, None

        # Update historical trackers
        self._palm_history.append(features.palm_center)
        self._prev_pinch_distance = features.pinch_distance_norm
        self._prev_two_finger_center = features.two_finger_center
        self._prev_index_z = landmarks[8].z

        detected_gesture = GestureType.NONE

        # =========================================================================
        # PRIORITY 1: PINCH (Pinch Zoom & Tap)
        # =========================================================================
        if features.pinch_distance_norm < self.pinch_threshold:
            # Check for continuous proportional zoom: expanding vs contracting distance
            if abs(features.pinch_delta) > 0.012:
                if features.pinch_delta > 0:
                    detected_gesture = GestureType.PINCH_OUT  # Expanding -> Zoom In
                else:
                    detected_gesture = GestureType.PINCH_IN   # Contracting -> Zoom Out
            else:
                detected_gesture = GestureType.PINCH

        # =========================================================================
        # PRIORITY 2: TWO-FINGER TOUCHPAD MODE (Cursor, Scroll & Secondary Tap)
        # =========================================================================
        elif features.is_two_finger_touchpad:
            dx, dy = features.two_finger_delta
            speed_2f = np.sqrt(dx * dx + dy * dy)

            # If vertical motion dominates and speed exceeds threshold -> Two-finger vertical scroll
            if speed_2f > 0.02 and abs(dy) > abs(dx) * 1.3:
                detected_gesture = GestureType.TWO_FINGER_SCROLL
            else:
                # Standard two-finger touchpad navigation
                detected_gesture = GestureType.TWO_FINGER_TOUCHPAD

        # =========================================================================
        # PRIORITY 3: AIR TAP (Z-Axis Forward Depth Pulse)
        # =========================================================================
        elif features.is_air_tap:
            detected_gesture = GestureType.AIR_TAP

        # =========================================================================
        # PRIORITY 4: ONE-FINGER SWIPE (High Velocity Directional Motion)
        # =========================================================================
        elif np.sqrt(features.velocity[0] ** 2 + features.velocity[1] ** 2) > self.swipe_velocity_threshold:
            vx, vy = features.velocity
            if abs(vx) > abs(vy):
                detected_gesture = GestureType.SWIPE_RIGHT if vx > 0 else GestureType.SWIPE_LEFT
            else:
                detected_gesture = GestureType.SWIPE_DOWN if vy > 0 else GestureType.SWIPE_UP

        # =========================================================================
        # PRIORITY 5: INDEX POINT (Standard Single-Finger Cursor Pointer)
        # =========================================================================
        elif features.index_extended and not features.middle_extended and not features.ring_extended and not features.pinky_extended:
            detected_gesture = GestureType.INDEX_POINT

        # =========================================================================
        # PRIORITY 6: OTHER STATIC GESTURES (Thumbs, Peace, Palm, Fist)
        # =========================================================================
        elif features.is_thumbs_up:
            detected_gesture = GestureType.THUMBS_UP

        elif features.is_thumbs_down:
            detected_gesture = GestureType.THUMBS_DOWN

        elif features.is_peace_sign:
            detected_gesture = GestureType.TWO_FINGERS

        elif features.extended_count == 0 or (features.extended_count == 1 and features.thumb_extended):
            detected_gesture = GestureType.FIST

        elif features.extended_count >= 4:
            detected_gesture = GestureType.OPEN_PALM

        else:
            detected_gesture = GestureType.NONE

        conf = ConfidenceEngine.calculate_confidence(detected_gesture, features, self.pinch_threshold)
        return detected_gesture, conf, features

    def reset(self) -> None:
        """Reset historical tracking state."""
        self._palm_history.clear()
        self._prev_pinch_distance = None
        self._prev_two_finger_center = None
        self._prev_index_z = None
