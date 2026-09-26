"""
Rule-Based Geometric Hand Gesture Classifier
Deterministic classifier implementing strict gesture priority:
CLEAR SAFETY/THUMBS -> PINCH -> CONFIRMED TWO-FINGER -> AIR TAP -> SWIPE -> STATIC
"""
from typing import List, Tuple, Optional, Deque
from collections import deque
import time
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
        self._two_finger_frames = 0
        self.two_finger_confirmation_frames = 3
        self._reset_two_finger_tap()

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

        # Pinch onset is a click candidate, not a spurious zoom from the open hand.
        was_pinching = self._prev_pinch_distance is not None and self._prev_pinch_distance < self.pinch_threshold
        pinching = features.pinch_distance_norm < self.pinch_threshold
        if features.is_two_finger_touchpad and not pinching:
            self._two_finger_frames = min(self.two_finger_confirmation_frames, self._two_finger_frames + 1)
        else:
            self._two_finger_frames = 0
            self._reset_two_finger_tap()

        # Update historical trackers
        self._palm_history.append(features.palm_center)
        self._prev_pinch_distance = features.pinch_distance_norm
        self._prev_two_finger_center = features.two_finger_center
        self._prev_index_z = landmarks[8].z

        detected_gesture = GestureType.NONE

        # =========================================================================
        # PRIORITY 1: PINCH (Pinch Zoom & Tap)
        # =========================================================================
        # Clear closed-hand poses take precedence over incidental thumb/index contact
        # and motion. They cannot be inferred merely from "not extended" fingers.
        if features.is_fist:
            detected_gesture = GestureType.FIST
        elif features.is_thumbs_up:
            detected_gesture = GestureType.THUMBS_UP
        elif features.is_thumbs_down:
            detected_gesture = GestureType.THUMBS_DOWN
        elif pinching:
            # Check for continuous proportional zoom: expanding vs contracting distance
            if was_pinching and abs(features.pinch_delta) > 0.012:
                if features.pinch_delta > 0:
                    detected_gesture = GestureType.PINCH_OUT  # Expanding -> Zoom In
                else:
                    detected_gesture = GestureType.PINCH_IN   # Contracting -> Zoom Out
            else:
                detected_gesture = GestureType.PINCH

        # =========================================================================
        # PRIORITY 2: TWO-FINGER TOUCHPAD MODE (Cursor, Scroll & Secondary Tap)
        # =========================================================================
        elif features.is_two_finger_touchpad and self._two_finger_frames < self.two_finger_confirmation_frames:
            # Do not leak an unconfirmed touchpad pose into swipe/media branches.
            detected_gesture = GestureType.NONE

        elif features.is_two_finger_touchpad:
            dx, dy = features.two_finger_delta
            speed_2f = np.sqrt(dx * dx + dy * dy)

            # A completed depth pulse wins over navigation for this frame.
            if self._detect_two_finger_tap(features, landmarks):
                detected_gesture = GestureType.TWO_FINGER_TAP
            # If vertical motion dominates and speed exceeds threshold -> scroll
            elif speed_2f > 0.02 and abs(dy) > abs(dx) * 1.3:
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
        elif (features.index_extended and not features.middle_extended or features.extended_count >= 4) and np.hypot(*features.velocity) > self.swipe_velocity_threshold:
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
        elif features.is_peace_sign:
            detected_gesture = GestureType.TWO_FINGERS

        elif features.extended_count >= 4:
            detected_gesture = GestureType.OPEN_PALM

        else:
            detected_gesture = GestureType.NONE

        conf = ConfidenceEngine.calculate_confidence(detected_gesture, features, self.pinch_threshold)
        return detected_gesture, conf, features

    def _reset_two_finger_tap(self) -> None:
        self._tap_rest_since: Optional[float] = None
        self._tap_pulse_since: Optional[float] = None
        self._tap_origin: Optional[Tuple[float, float]] = None
        self._tap_depths: Optional[Tuple[float, float]] = None

    def _detect_two_finger_tap(self, features: HandFeatures, landmarks: List[LandmarkPoint]) -> bool:
        """Still hold (100 ms), both tips forward, then return within 300 ms.

        Emit once on release, not while resting or pressing. XY motion, loss of
        the strict pose, a slow depth drift, or a long press cancels the attempt.
        Palm-relative depths reject a translation of the entire hand in Z.
        """
        now = time.monotonic()
        center = features.two_finger_center
        palm_z = sum(landmarks[i].z for i in (0, 5, 9, 17)) / 4.0
        depths = (landmarks[8].z - palm_z, landmarks[12].z - palm_z)
        if np.hypot(*features.two_finger_delta) > 0.008:
            self._reset_two_finger_tap()
            return False
        if self._tap_origin is not None and np.hypot(
            center[0] - self._tap_origin[0], center[1] - self._tap_origin[1]
        ) > 0.015:
            self._reset_two_finger_tap()
            return False

        if self._tap_rest_since is None:
            self._tap_rest_since = now
            self._tap_origin = center
            self._tap_depths = depths
            return False

        offsets = tuple(current - rest for current, rest in zip(depths, self._tap_depths))
        if self._tap_pulse_since is not None:
            if now - self._tap_pulse_since > 0.30:
                self._reset_two_finger_tap()
            elif all(offset > -0.010 for offset in offsets):
                self._reset_two_finger_tap()
                return True
            return False

        if now - self._tap_rest_since >= 0.10 and all(offset < -0.025 for offset in offsets):
            self._tap_pulse_since = now
        elif any(abs(offset) > 0.012 for offset in offsets):
            # Re-establish a still baseline rather than accumulate depth drift.
            self._reset_two_finger_tap()
        return False

    def reset(self) -> None:
        """Reset historical tracking state."""
        self._palm_history.clear()
        self._prev_pinch_distance = None
        self._prev_two_finger_center = None
        self._prev_index_z = None
        self._two_finger_frames = 0
        self._reset_two_finger_tap()
