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
    def calculate_confidence(gesture: GestureType, features: HandFeatures, pinch_threshold: float = 0.35) -> float:
        """
        Calculates a confidence metric between 0.0 and 1.0.
        """
        if gesture == GestureType.NONE or features is None:
            return 0.0

        if gesture == GestureType.PINCH:
            # Distance margin below pinch threshold
            ratio = features.pinch_distance_norm / max(0.01, pinch_threshold)
            conf = 1.0 - (ratio * 0.5)
            return float(np.clip(conf, 0.50, 0.98))

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
            # Index and Middle extended, Ring and Pinky curled
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

