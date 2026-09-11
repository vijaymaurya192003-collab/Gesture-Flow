"""
Confidence Engine
Calculates robust confidence scores for gesture classifications based on geometric margins.
"""
import numpy as np
from android.config.constants import GestureType
from android.gestures.feature_extractor import HandFeatures


class ConfidenceEngine:
    """Computes confidence percentages for classified gestures."""

    @staticmethod
    def calculate_confidence(gesture: GestureType, features: HandFeatures, pinch_threshold: float = 0.45) -> float:
        """
        Calculates a confidence metric between 0.0 and 1.0.
        """
        if gesture == GestureType.NONE or features is None:
            return 0.0

        if gesture in (GestureType.PINCH, GestureType.PINCH_IN, GestureType.PINCH_OUT):
            # Distance margin below or around pinch threshold
            ratio = features.pinch_distance_norm / max(0.01, pinch_threshold)
            conf = 1.0 - min(0.5, ratio * 0.4)
            if gesture in (GestureType.PINCH_IN, GestureType.PINCH_OUT) and abs(features.pinch_delta) > 0.01:
                conf += 0.1
            return float(np.clip(conf, 0.55, 0.98))

        elif gesture == GestureType.AIR_TAP:
            # High confidence based on index z-velocity pulse
            speed = abs(features.index_z_velocity)
            conf = 0.75 + min(0.20, speed * 4.0)
            return float(np.clip(conf, 0.65, 0.96))

        elif gesture in (GestureType.TWO_FINGER_TOUCHPAD, GestureType.TWO_FINGER_SCROLL, GestureType.TWO_FINGER_TAP):
            # Proximity between index and middle fingertip
            sep_margin = max(0.0, 0.55 - features.two_finger_separation_norm)
            conf = 0.75 + (sep_margin * 0.3)
            return float(np.clip(conf, 0.65, 0.95))

        elif gesture == GestureType.THUMBS_UP or gesture == GestureType.THUMBS_DOWN:
            return 0.92

        elif gesture == GestureType.INDEX_POINT:
            # High confidence if index is extended and other 3 fingers are clearly curled
            curled_bonus = 0.15 if not features.middle_extended and not features.ring_extended and not features.pinky_extended else -0.2
            conf = 0.80 + curled_bonus
            return float(np.clip(conf, 0.55, 0.95))

        elif gesture == GestureType.OPEN_PALM:
            # High confidence when all 5 fingers are fully extended
            ext_ratio = features.extended_count / 5.0
            conf = ext_ratio * 0.95
            return float(np.clip(conf, 0.60, 0.99))

        elif gesture == GestureType.TWO_FINGERS:
            # Index and Middle extended with wider separation (Peace / V-sign)
            if features.index_extended and features.middle_extended and not features.ring_extended and not features.pinky_extended:
                return 0.90
            return 0.70

        elif gesture == GestureType.FIST:
            # All fingers curled tightly
            if features.extended_count <= 1 and not features.index_extended and not features.middle_extended:
                return 0.92
            return 0.65

        elif gesture in (GestureType.SWIPE_UP, GestureType.SWIPE_DOWN, GestureType.SWIPE_LEFT, GestureType.SWIPE_RIGHT):
            speed = np.sqrt(features.velocity[0] ** 2 + features.velocity[1] ** 2)
            conf = 0.70 + min(0.25, speed * 2.0)
            return float(np.clip(conf, 0.65, 0.95))

        return 0.70
