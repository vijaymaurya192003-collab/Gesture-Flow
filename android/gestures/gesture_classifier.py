"""
Rule-Based Geometric Hand Gesture Classifier
Deterministic classifier based on 3D landmark geometry and flexion angles.
"""
from typing import List, Tuple, Optional, Deque
from collections import deque
import numpy as np
from android.config.constants import GestureType
from android.models.gesture_models import LandmarkPoint
from android.gestures.feature_extractor import extract_hand_features, HandFeatures
from android.gestures.confidence_engine import ConfidenceEngine


class GestureClassifier:
    """Classifies hand gestures using deterministic 3D geometric heuristics."""

    def __init__(
        self,
        pinch_threshold: float = 0.45,
        swipe_velocity_threshold: float = 0.045,
        history_len: int = 5
    ):
        self.pinch_threshold = pinch_threshold
        self.swipe_velocity_threshold = swipe_velocity_threshold
        self._palm_history: Deque[Tuple[float, float]] = deque(maxlen=history_len)

    def set_pinch_threshold(self, threshold: float) -> None:
        """Update calibration pinch sensitivity threshold."""
        self.pinch_threshold = max(0.01, min(1.0, threshold))

    def classify(self, landmarks: List[LandmarkPoint]) -> Tuple[GestureType, float, Optional[HandFeatures]]:
        """
        Classifies current hand landmarks into a GestureType.
        Returns: (GestureType, confidence_score [0.0 - 1.0], HandFeatures)
        """
        if not landmarks or len(landmarks) < 21:
            self._palm_history.clear()
            return GestureType.NONE, 0.0, None

        # Extract features with velocity tracking
        features = extract_hand_features(landmarks, list(self._palm_history))
        if features is None:
            return GestureType.NONE, 0.0, None

        # Append current palm center to history
        self._palm_history.append(features.palm_center)

        detected_gesture = GestureType.NONE

        # 1. Check Dynamic Swipe Gestures first if velocity exceeds threshold
        vx, vy = features.velocity
        speed = np.sqrt(vx * vx + vy * vy)

        if speed > self.swipe_velocity_threshold:
            if features.extended_count >= 1:
                if abs(vx) > abs(vy):
                    detected_gesture = GestureType.SWIPE_RIGHT if vx > 0 else GestureType.SWIPE_LEFT
                else:
                    detected_gesture = GestureType.SWIPE_DOWN if vy > 0 else GestureType.SWIPE_UP

                conf = ConfidenceEngine.calculate_confidence(detected_gesture, features, self.pinch_threshold)
                return detected_gesture, conf, features

        # 2. Check Static Postures in priority order

        # A. PINCH: Thumb tip and Index tip touching/close
        if features.pinch_distance_norm < self.pinch_threshold:
            detected_gesture = GestureType.PINCH

        # B. FIST: All fingers curled
        elif features.extended_count == 0 or (features.extended_count == 1 and features.thumb_extended):
            detected_gesture = GestureType.FIST

        # C. TWO FINGERS (Peace / V-sign): Index & Middle extended, Ring & Pinky curled
        elif features.index_extended and features.middle_extended and not features.ring_extended and not features.pinky_extended:
            detected_gesture = GestureType.TWO_FINGERS

        # D. INDEX POINT: Index finger is extended, Middle/Ring/Pinky curled
        elif features.index_extended and not features.middle_extended and not features.ring_extended and not features.pinky_extended:
            detected_gesture = GestureType.INDEX_POINT

        # E. OPEN PALM: All fingers extended
        elif features.extended_count >= 4:
            detected_gesture = GestureType.OPEN_PALM

        else:
            detected_gesture = GestureType.NONE

        conf = ConfidenceEngine.calculate_confidence(detected_gesture, features, self.pinch_threshold)
        return detected_gesture, conf, features

    def reset(self) -> None:
        """Reset historical tracking state."""
        self._palm_history.clear()
