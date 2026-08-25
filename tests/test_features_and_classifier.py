"""
Unit Tests for Feature Extraction and Gesture Classifier
Tests synthetic 21-landmark coordinates against geometric classification rules.
"""
import pytest
from typing import List
from android.models.gesture_models import LandmarkPoint
from android.config.constants import GestureType
from android.gestures.feature_extractor import extract_hand_features, HandFeatures
from android.gestures.gesture_classifier import GestureClassifier


def create_synthetic_hand(
    index_extended: bool = True,
    middle_extended: bool = True,
    ring_extended: bool = True,
    pinky_extended: bool = True,
    thumb_extended: bool = True,
    pinch: bool = False
) -> List[LandmarkPoint]:
    """Helper to generate synthetic 21 MediaPipe hand landmarks."""
    landmarks = [LandmarkPoint(x=0.5, y=0.8, z=0.0)] * 21  # 0: Wrist

    # Knuckles (MCPs)
    landmarks[1] = LandmarkPoint(x=0.45, y=0.75, z=0.0) # Thumb CMC
    landmarks[2] = LandmarkPoint(x=0.40, y=0.70, z=0.0) # Thumb MCP
    landmarks[3] = LandmarkPoint(x=0.35, y=0.65, z=0.0) # Thumb IP
    landmarks[4] = LandmarkPoint(x=0.30 if thumb_extended else 0.42, y=0.60 if thumb_extended else 0.72, z=0.0) # Thumb Tip

    landmarks[5] = LandmarkPoint(x=0.45, y=0.60, z=0.0) # Index MCP
    landmarks[6] = LandmarkPoint(x=0.45, y=0.50, z=0.0) # Index PIP
    landmarks[7] = LandmarkPoint(x=0.45, y=0.40, z=0.0) # Index DIP
    landmarks[8] = LandmarkPoint(x=0.45, y=0.30 if index_extended else 0.62, z=0.0) # Index Tip

    landmarks[9] = LandmarkPoint(x=0.50, y=0.58, z=0.0)  # Middle MCP
    landmarks[10] = LandmarkPoint(x=0.50, y=0.48, z=0.0) # Middle PIP
    landmarks[11] = LandmarkPoint(x=0.50, y=0.38, z=0.0) # Middle DIP
    landmarks[12] = LandmarkPoint(x=0.50, y=0.28 if middle_extended else 0.62, z=0.0) # Middle Tip

    landmarks[13] = LandmarkPoint(x=0.55, y=0.60, z=0.0) # Ring MCP
    landmarks[14] = LandmarkPoint(x=0.55, y=0.50, z=0.0) # Ring PIP
    landmarks[15] = LandmarkPoint(x=0.55, y=0.40, z=0.0) # Ring DIP
    landmarks[16] = LandmarkPoint(x=0.55, y=0.32 if ring_extended else 0.62, z=0.0) # Ring Tip

    landmarks[17] = LandmarkPoint(x=0.60, y=0.63, z=0.0) # Pinky MCP
    landmarks[18] = LandmarkPoint(x=0.60, y=0.55, z=0.0) # Pinky PIP
    landmarks[19] = LandmarkPoint(x=0.60, y=0.47, z=0.0) # Pinky DIP
    landmarks[20] = LandmarkPoint(x=0.60, y=0.38 if pinky_extended else 0.64, z=0.0) # Pinky Tip

    if pinch:
        # Move thumb tip close to index tip
        landmarks[4] = LandmarkPoint(x=0.44, y=0.31, z=0.0)
        landmarks[8] = LandmarkPoint(x=0.45, y=0.30, z=0.0)

    return landmarks


def test_feature_extraction_open_palm():
    """Test feature extraction on an open palm posture."""
    open_hand = create_synthetic_hand(index_extended=True, middle_extended=True, ring_extended=True, pinky_extended=True, thumb_extended=True)
    features = extract_hand_features(open_hand)
    assert features is not None
    assert features.index_extended is True
    assert features.middle_extended is True
    assert features.ring_extended is True
    assert features.pinky_extended is True
    assert features.extended_count >= 4


def test_classify_open_palm():
    """Test classifying open palm gesture."""
    classifier = GestureClassifier()
    open_hand = create_synthetic_hand(index_extended=True, middle_extended=True, ring_extended=True, pinky_extended=True, thumb_extended=True)
    gesture, conf, _ = classifier.classify(open_hand)
    assert gesture == GestureType.OPEN_PALM
    assert conf >= 0.70


def test_classify_index_point():
    """Test classifying index pointing gesture."""
    classifier = GestureClassifier()
    point_hand = create_synthetic_hand(index_extended=True, middle_extended=False, ring_extended=False, pinky_extended=False, thumb_extended=False)
    gesture, conf, _ = classifier.classify(point_hand)
    assert gesture == GestureType.INDEX_POINT
    assert conf >= 0.70


def test_classify_pinch():
    """Test classifying pinch gesture."""
    classifier = GestureClassifier()
    pinch_hand = create_synthetic_hand(index_extended=True, middle_extended=False, ring_extended=False, pinky_extended=False, pinch=True)
    gesture, conf, features = classifier.classify(pinch_hand)
    assert gesture == GestureType.PINCH
    assert conf >= 0.70
    assert features.pinch_distance_norm < classifier.pinch_threshold


def test_classify_two_fingers():
    """Test classifying two fingers (peace / V-sign) gesture."""
    classifier = GestureClassifier()
    peace_hand = create_synthetic_hand(index_extended=True, middle_extended=True, ring_extended=False, pinky_extended=False, thumb_extended=False)
    gesture, conf, _ = classifier.classify(peace_hand)
    assert gesture == GestureType.TWO_FINGERS
    assert conf >= 0.70


def test_classify_fist():
    """Test classifying closed fist gesture."""
    classifier = GestureClassifier()
    fist_hand = create_synthetic_hand(index_extended=False, middle_extended=False, ring_extended=False, pinky_extended=False, thumb_extended=False)
    gesture, conf, _ = classifier.classify(fist_hand)
    assert gesture == GestureType.FIST
    assert conf >= 0.70


def test_classify_swipe_direction():
    """Test swipe velocity detection."""
    classifier = GestureClassifier(swipe_velocity_threshold=0.02)
    # Simulate movement from left to right
    hand = create_synthetic_hand(index_extended=True, middle_extended=True, ring_extended=True, pinky_extended=True)

    # Frame 1 at x=0.2
    for lm in hand:
        lm.x -= 0.15
    classifier.classify(hand)

    # Frame 2 at x=0.5 (fast rightward movement)
    for lm in hand:
        lm.x += 0.30
    gesture, conf, _ = classifier.classify(hand)

    assert gesture == GestureType.SWIPE_RIGHT
    assert conf >= 0.65

