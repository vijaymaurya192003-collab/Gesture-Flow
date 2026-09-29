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
        pinch_threshold: float = 0.35,
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
        self._prev_two_finger_z: Optional[float] = None

        # Temporal confirmation & hysteresis tracking
        self._two_finger_consecutive_frames: int = 0
        self._last_detected_gesture: GestureType = GestureType.NONE

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
            prev_index_z=self._prev_index_z,
            prev_two_finger_z=self._prev_two_finger_z
        )
        if features is None:
            return GestureType.NONE, 0.0, None

        # Update historical trackers
        self._palm_history.append(features.palm_center)
        self._prev_pinch_distance = features.pinch_distance_norm
        self._prev_two_finger_center = features.two_finger_center
        self._prev_index_z = landmarks[8].z
        self._prev_two_finger_z = float((landmarks[8].z + landmarks[12].z) / 2.0)

        # Track consecutive two-finger frames for temporal confirmation
        if features.is_two_finger_touchpad:
            self._two_finger_consecutive_frames += 1
        else:
            self._two_finger_consecutive_frames = 0

        # Temporal confirmation guard:
        # If user is currently holding a single-finger pointer, pinch, or static gesture,
        # require at least 2 consecutive frames of two-finger posture before committing to two-finger mode.
        # This prevents 1-frame tracking noise/wobble from hijacking classification away from the active gesture.
        # If starting from NONE (hand raised/idle) or already in two-finger mode, allow immediately.
        is_already_two_finger = self._last_detected_gesture in (
            GestureType.TWO_FINGER_TOUCHPAD,
            GestureType.TWO_FINGER_SCROLL,
            GestureType.TWO_FINGER_TAP
        )
        is_from_idle = (self._last_detected_gesture == GestureType.NONE)
        allow_two_finger = is_already_two_finger or is_from_idle or (self._two_finger_consecutive_frames >= 2)

        detected_gesture = GestureType.NONE

        all_four_fingers_curled = (
            not features.index_extended
            and not features.middle_extended
            and not features.ring_extended
            and not features.pinky_extended
        )

        # Resolve effective pinch threshold regardless of whether threshold is given in
        # frame-normalized units (<0.15, e.g. 0.055) or hand-scale normalized units (>=0.15, e.g. 0.35-0.45)
        effective_pinch_thresh = (
            self.pinch_threshold / max(0.05, features.hand_scale)
            if self.pinch_threshold < 0.15
            else self.pinch_threshold
        )

        # =========================================================================
        # PRIORITY 1: PINCH (Pinch Zoom & Tap)
        # Requires index to not be locked in a closed fist posture and not thumbs-up
        # =========================================================================
        if not all_four_fingers_curled and not features.is_thumbs_up and features.pinch_distance_norm < effective_pinch_thresh:
            # Continuous proportional zoom: expanding vs contracting distance
            if abs(features.pinch_delta) > 0.015:
                if features.pinch_delta > 0:
                    detected_gesture = GestureType.PINCH_OUT  # Expanding -> Zoom In
                else:
                    detected_gesture = GestureType.PINCH_IN   # Contracting -> Zoom Out
            else:
                detected_gesture = GestureType.PINCH

        # =========================================================================
        # PRIORITY 2: TWO-FINGER TOUCHPAD MODE (Tap, Scroll & Touchpad Cursor)
        # =========================================================================
        elif allow_two_finger and features.is_two_finger_touchpad:
            dx, dy = features.two_finger_delta
            speed_2f = np.sqrt(dx * dx + dy * dy)

            # 2a. TWO-FINGER TAP (Right-Click Context Action)
            # High-priority sub-branch: forward Z pulse while stationary in XY
            if features.is_two_finger_tap:
                detected_gesture = GestureType.TWO_FINGER_TAP

            # 2b. TWO-FINGER SCROLL (Vertical Motion Dominates)
            elif speed_2f > 0.02 and abs(dy) > abs(dx) * 1.3:
                detected_gesture = GestureType.TWO_FINGER_SCROLL

            # 2c. TWO-FINGER TOUCHPAD (Relative Cursor Movement)
            else:
                detected_gesture = GestureType.TWO_FINGER_TOUCHPAD

        # =========================================================================
        # PRIORITY 3: AIR TAP (Z-Axis Forward Depth Pulse)
        # =========================================================================
        elif features.is_air_tap:
            detected_gesture = GestureType.AIR_TAP

        # =========================================================================
        # PRIORITY 4: MULTI-FINGER SWIPE (High Velocity Directional Motion)
        # Only when multiple fingers are open; never hijack single-finger pointer aiming
        # =========================================================================
        elif (
            features.extended_count >= 2
            and not (features.index_extended and not features.middle_extended and not features.ring_extended and not features.pinky_extended)
            and np.sqrt(features.velocity[0] ** 2 + features.velocity[1] ** 2) > self.swipe_velocity_threshold
        ):
            vx, vy = features.velocity
            if abs(vx) > abs(vy):
                detected_gesture = GestureType.SWIPE_RIGHT if vx > 0 else GestureType.SWIPE_LEFT
            else:
                detected_gesture = GestureType.SWIPE_DOWN if vy > 0 else GestureType.SWIPE_UP

        # =========================================================================
        # PRIORITY 5: INDEX POINT (Standard Single-Finger Cursor Pointer)
        # If user was previously in INDEX_POINT and an unconfirmed 1-frame middle-finger
        # wobble occurred, maintain continuity instead of dropping to NONE.
        # =========================================================================
        elif features.index_extended and not features.ring_extended and not features.pinky_extended and (
            not features.middle_extended or (self._last_detected_gesture == GestureType.INDEX_POINT and not allow_two_finger)
        ):
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

        elif all_four_fingers_curled or features.extended_count == 0 or (features.extended_count == 1 and features.thumb_extended):
            detected_gesture = GestureType.FIST

        elif features.extended_count >= 4:
            detected_gesture = GestureType.OPEN_PALM

        else:
            detected_gesture = GestureType.NONE

        self._last_detected_gesture = detected_gesture
        conf = ConfidenceEngine.calculate_confidence(detected_gesture, features, effective_pinch_thresh)
        return detected_gesture, conf, features

    def reset(self) -> None:
        """Reset historical tracking state."""
        self._palm_history.clear()
        self._prev_pinch_distance = None
        self._prev_two_finger_center = None
        self._prev_index_z = None
        self._prev_two_finger_z = None
        self._two_finger_consecutive_frames = 0
        self._last_detected_gesture = GestureType.NONE
