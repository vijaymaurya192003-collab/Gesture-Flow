"""
Unit Tests for Extended Gestures, Priority Hierarchy & Touchpad Mode
Verifies:
1. Strict priority hierarchy (PINCH > TWO_FINGER_TOUCHPAD > AIR_TAP > SWIPE > INDEX_POINT > OTHER).
2. Continuous Pinch Zoom delta calculations.
3. Two-Finger Touchpad cursor navigation and scroll isolation.
4. Thumbs Up / Down geometry.
5. Air Tap forward pulse detection.
6. Safe Action Registry whitelist compliance.
"""
import pytest
from typing import List
from android.models.gesture_models import LandmarkPoint
from android.config.constants import GestureType, SafeActionType, TouchpadSensitivity, TOUCHPAD_SENSITIVITY_MULTIPLIERS
from android.gestures.feature_extractor import extract_hand_features, HandFeatures
from android.gestures.gesture_classifier import GestureClassifier
from android.gestures.state_machine import GestureStateMachine
from android.vision.landmark_smoother import LandmarkSmoother
from android.actions.action_registry import ActionRegistry
from android.actions.action_dispatcher import ActionDispatcher
from android.actions.desktop_executor import DesktopActionExecutor


def create_hand_skeleton(
    thumb_pos: str = "curled",    # "up", "down", "extended", "curled"
    index_extended: bool = True,
    middle_extended: bool = False,
    ring_extended: bool = False,
    pinky_extended: bool = False,
    pinch: bool = False,
    two_finger_close: bool = False,
    index_z: float = 0.0
) -> List[LandmarkPoint]:
    """Helper generating 21 MediaPipe hand landmarks for any test posture."""
    landmarks = [LandmarkPoint(x=0.5, y=0.8, z=0.0)] * 21  # 0: Wrist

    # Thumb CMC, MCP, IP
    if thumb_pos == "up":
        landmarks[1] = LandmarkPoint(x=0.46, y=0.70, z=0.0)
        landmarks[2] = LandmarkPoint(x=0.44, y=0.55, z=0.0)
        landmarks[3] = LandmarkPoint(x=0.44, y=0.40, z=0.0)
        landmarks[4] = LandmarkPoint(x=0.44, y=0.25, z=0.0)  # High up
    elif thumb_pos == "down":
        landmarks[1] = LandmarkPoint(x=0.46, y=0.75, z=0.0)
        landmarks[2] = LandmarkPoint(x=0.44, y=0.82, z=0.0)
        landmarks[3] = LandmarkPoint(x=0.44, y=0.88, z=0.0)
        landmarks[4] = LandmarkPoint(x=0.44, y=0.95, z=0.0)  # Down low
    elif thumb_pos == "extended":
        landmarks[1] = LandmarkPoint(x=0.45, y=0.75, z=0.0)
        landmarks[2] = LandmarkPoint(x=0.40, y=0.70, z=0.0)
        landmarks[3] = LandmarkPoint(x=0.35, y=0.65, z=0.0)
        landmarks[4] = LandmarkPoint(x=0.28, y=0.60, z=0.0)
    else:  # curled
        landmarks[1] = LandmarkPoint(x=0.45, y=0.75, z=0.0)
        landmarks[2] = LandmarkPoint(x=0.42, y=0.70, z=0.0)
        landmarks[3] = LandmarkPoint(x=0.40, y=0.66, z=0.0)
        landmarks[4] = LandmarkPoint(x=0.42, y=0.64, z=0.0)

    # Index finger
    landmarks[5] = LandmarkPoint(x=0.45, y=0.60, z=0.0)
    landmarks[6] = LandmarkPoint(x=0.45, y=0.50, z=0.0)
    landmarks[7] = LandmarkPoint(x=0.45, y=0.40, z=index_z)
    landmarks[8] = LandmarkPoint(x=0.45, y=0.30 if index_extended else 0.62, z=index_z)

    # Middle finger
    mid_x = 0.47 if two_finger_close else 0.52
    landmarks[9] = LandmarkPoint(x=0.50, y=0.58, z=0.0)
    landmarks[10] = LandmarkPoint(x=mid_x, y=0.48, z=0.0)
    landmarks[11] = LandmarkPoint(x=mid_x, y=0.38, z=0.0)
    landmarks[12] = LandmarkPoint(x=mid_x, y=0.30 if middle_extended else 0.62, z=0.0)

    # Ring finger
    landmarks[13] = LandmarkPoint(x=0.55, y=0.60, z=0.0)
    landmarks[14] = LandmarkPoint(x=0.55, y=0.50, z=0.0)
    landmarks[15] = LandmarkPoint(x=0.55, y=0.40, z=0.0)
    landmarks[16] = LandmarkPoint(x=0.55, y=0.32 if ring_extended else 0.62, z=0.0)

    # Pinky finger
    landmarks[17] = LandmarkPoint(x=0.60, y=0.63, z=0.0)
    landmarks[18] = LandmarkPoint(x=0.60, y=0.55, z=0.0)
    landmarks[19] = LandmarkPoint(x=0.60, y=0.47, z=0.0)
    landmarks[20] = LandmarkPoint(x=0.60, y=0.38 if pinky_extended else 0.64, z=0.0)

    if pinch:
        landmarks[4] = LandmarkPoint(x=0.44, y=0.31, z=0.0)
        landmarks[8] = LandmarkPoint(x=0.45, y=0.30, z=0.0)

    return landmarks


def test_thumbs_up_detection():
    """Test Thumbs Up recognition."""
    classifier = GestureClassifier()
    hand = create_hand_skeleton(thumb_pos="up", index_extended=False, middle_extended=False, ring_extended=False, pinky_extended=False)
    g, conf, feats = classifier.classify(hand)
    assert g == GestureType.THUMBS_UP
    assert feats.is_thumbs_up is True
    assert conf >= 0.70


def test_thumbs_down_detection():
    """Test Thumbs Down recognition."""
    classifier = GestureClassifier()
    hand = create_hand_skeleton(thumb_pos="down", index_extended=False, middle_extended=False, ring_extended=False, pinky_extended=False)
    g, conf, feats = classifier.classify(hand)
    assert g == GestureType.THUMBS_DOWN
    assert feats.is_thumbs_down is True
    assert conf >= 0.70


def test_two_finger_touchpad_mode():
    """Test Two-Finger Touchpad Mode classification."""
    classifier = GestureClassifier()
    # Index & Middle extended close together (< 0.55 separation)
    hand = create_hand_skeleton(index_extended=True, middle_extended=True, ring_extended=False, pinky_extended=False, two_finger_close=True)
    g, conf, feats = classifier.classify(hand)
    assert g == GestureType.TWO_FINGER_TOUCHPAD
    assert feats.is_two_finger_touchpad is True
    assert feats.two_finger_separation_norm < 0.55


def test_priority_pinch_over_touchpad():
    """Priority Rule 1: PINCH takes precedence over touchpad posture."""
    classifier = GestureClassifier()
    # Both pinch contact and two fingers extended
    hand = create_hand_skeleton(index_extended=True, middle_extended=True, ring_extended=False, pinky_extended=False, pinch=True, two_finger_close=True)
    g, conf, _ = classifier.classify(hand)
    assert g in (GestureType.PINCH, GestureType.PINCH_IN, GestureType.PINCH_OUT)


def test_continuous_pinch_zoom_deltas():
    """Test Continuous Pinch In and Out zoom classifications based on distance differential."""
    classifier = GestureClassifier()

    # Frame 1: Normal pinch distance
    hand1 = create_hand_skeleton(pinch=True)
    hand1[4] = LandmarkPoint(x=0.43, y=0.32, z=0.0)
    hand1[8] = LandmarkPoint(x=0.45, y=0.30, z=0.0)
    g1, _, _ = classifier.classify(hand1)

    # Frame 2: Expanding pinch (fingers moving apart -> PINCH_OUT / Zoom In)
    hand2 = create_hand_skeleton(pinch=True)
    hand2[4] = LandmarkPoint(x=0.41, y=0.33, z=0.0)
    hand2[8] = LandmarkPoint(x=0.47, y=0.30, z=0.0)
    g2, _, feats2 = classifier.classify(hand2)
    assert g2 == GestureType.PINCH_OUT
    assert feats2.pinch_delta > 0

    # Frame 3: Contracting pinch (fingers moving together -> PINCH_IN / Zoom Out)
    hand3 = create_hand_skeleton(pinch=True)
    hand3[4] = LandmarkPoint(x=0.44, y=0.31, z=0.0)
    hand3[8] = LandmarkPoint(x=0.45, y=0.30, z=0.0)
    g3, _, feats3 = classifier.classify(hand3)
    assert g3 == GestureType.PINCH_IN
    assert feats3.pinch_delta < 0


def test_air_tap_detection():
    """Test Air Tap detection from z-depth forward velocity pulse."""
    classifier = GestureClassifier()

    # Frame 1: Index pointing at rest (z = 0.0)
    hand1 = create_hand_skeleton(index_extended=True, middle_extended=False, index_z=0.0)
    g1, _, _ = classifier.classify(hand1)
    assert g1 == GestureType.INDEX_POINT

    # Frame 2: Rapid forward push towards camera (z = -0.06)
    hand2 = create_hand_skeleton(index_extended=True, middle_extended=False, index_z=-0.06)
    g2, conf, feats = classifier.classify(hand2)
    assert g2 == GestureType.AIR_TAP
    assert feats.is_air_tap is True


def test_touchpad_sensitivity_presets():
    """Verify touchpad sensitivity multiplier mappings."""
    assert TOUCHPAD_SENSITIVITY_MULTIPLIERS[TouchpadSensitivity.LOW.value] == 0.75
    assert TOUCHPAD_SENSITIVITY_MULTIPLIERS[TouchpadSensitivity.MEDIUM.value] == 1.25
    assert TOUCHPAD_SENSITIVITY_MULTIPLIERS[TouchpadSensitivity.HIGH.value] == 2.0


def test_safe_action_whitelist():
    """Verify all actions in SafeActionType are explicitly registered in ActionRegistry."""
    for action in SafeActionType:
        if action == SafeActionType.NONE:
            continue
        assert ActionRegistry.is_safe(action.value), f"Action '{action.value}' not in ActionRegistry whitelist!"


def test_two_finger_tap_detection():
    """Test Two-Finger Tap detection from forward Z pulse while in touchpad posture."""
    classifier = GestureClassifier()

    # Frame 1: Two fingers held together in touchpad posture at rest (z = 0.0)
    hand1 = create_hand_skeleton(index_extended=True, middle_extended=True, ring_extended=False, pinky_extended=False, two_finger_close=True, index_z=0.0)
    hand1[12] = LandmarkPoint(x=hand1[12].x, y=hand1[12].y, z=0.0)
    g1, _, _ = classifier.classify(hand1)
    assert g1 == GestureType.TWO_FINGER_TOUCHPAD

    # Frame 2: Rapid forward poke with both fingers toward camera (z = -0.06)
    hand2 = create_hand_skeleton(index_extended=True, middle_extended=True, ring_extended=False, pinky_extended=False, two_finger_close=True, index_z=-0.06)
    hand2[12] = LandmarkPoint(x=hand2[12].x, y=hand2[12].y, z=-0.06)
    g2, conf, feats = classifier.classify(hand2)
    assert g2 == GestureType.TWO_FINGER_TAP
    assert feats.is_two_finger_tap is True
    assert conf >= 0.70


def test_smoother_preserves_z_air_tap():
    """Verify LandmarkSmoother preserves intentional Z forward motion even when XY is stationary."""
    smoother = LandmarkSmoother(jitter_threshold=0.005, z_jitter_threshold=0.003)

    # Frame 1: Hand at rest
    lm1 = [LandmarkPoint(x=0.5, y=0.5, z=0.0, visibility=1.0) for _ in range(21)]
    smoothed1 = smoother.smooth(lm1)
    assert smoothed1[8].z == 0.0

    # Frame 2: Index fingertip moves forward in Z by -0.05, XY is stationary (0.0 movement)
    lm2 = [LandmarkPoint(x=0.5, y=0.5, z=0.0, visibility=1.0) for _ in range(21)]
    lm2[8] = LandmarkPoint(x=0.5, y=0.5, z=-0.05, visibility=1.0)
    smoothed2 = smoother.smooth(lm2)

    # XY must remain locked to prev (zero cursor drift!)
    assert smoothed2[8].x == 0.5
    assert smoothed2[8].y == 0.5
    # Z must NOT be locked to prev; it must update smoothly towards -0.05
    assert smoothed2[8].z < -0.02


def test_temporal_confirmation_prevents_pointer_hijack():
    """Verify temporal confirmation prevents 1-frame tracking noise from hijacking index pointer."""
    classifier = GestureClassifier()

    # Frame 1: User index pointing
    hand_point = create_hand_skeleton(index_extended=True, middle_extended=False)
    g1, _, _ = classifier.classify(hand_point)
    assert g1 == GestureType.INDEX_POINT

    # Frame 2: 1-frame noise causes middle finger to be briefly detected close to index
    hand_noise = create_hand_skeleton(index_extended=True, middle_extended=True, two_finger_close=True)
    g2, _, _ = classifier.classify(hand_noise)
    # Must NOT hijack away to TWO_FINGER_TOUCHPAD on 1 frame of noise!
    assert g2 == GestureType.INDEX_POINT

    # Frame 3: Deliberate transition - user continues holding two fingers for 2nd frame
    g3, _, _ = classifier.classify(hand_noise)
    assert g3 == GestureType.TWO_FINGER_TOUCHPAD


def test_finger_extension_geometry_curled_rejection():
    """Verify joint angle geometry rejects partially curled fingers from being classified as extended."""
    # Index finger extended straight, middle finger bent at PIP (angle ~90°)
    hand = create_hand_skeleton(index_extended=True, middle_extended=False)
    hand[9] = LandmarkPoint(x=0.50, y=0.58, z=0.0)   # MCP
    hand[10] = LandmarkPoint(x=0.50, y=0.48, z=0.0)  # PIP
    hand[12] = LandmarkPoint(x=0.60, y=0.48, z=0.0)  # TIP bent at 90 degrees
    features = extract_hand_features(hand)
    assert features is not None
    assert features.index_extended is True
    assert features.middle_extended is False

    classifier = GestureClassifier()
    g, conf, _ = classifier.classify(hand)
    assert g == GestureType.INDEX_POINT


def test_confidence_threshold_plumbing():
    """Verify per-gesture confidence thresholds gate actions through state machine."""
    dispatcher = ActionDispatcher()
    sm = GestureStateMachine()

    fist_mapping = dispatcher.get_mapping_item(GestureType.FIST)
    assert fist_mapping.confidence_threshold == 0.80

    # 1. Confidence below 0.80 (e.g. 0.75) must be suppressed to TRACKING
    res_low = sm.process_frame(
        hand_detected=True,
        detected_gesture=GestureType.FIST,
        confidence=0.75,
        features=None,
        mapped_action=SafeActionType.EMERGENCY_STOP.value,
        min_confidence=fist_mapping.confidence_threshold
    )
    assert res_low.action == "NONE"
    assert res_low.state.value == "TRACKING"

    # 2. Confidence meeting 0.80+ triggers action
    res_high = sm.process_frame(
        hand_detected=True,
        detected_gesture=GestureType.FIST,
        confidence=0.92,
        features=None,
        mapped_action=SafeActionType.EMERGENCY_STOP.value,
        min_confidence=fist_mapping.confidence_threshold
    )
    assert res_high.action == SafeActionType.EMERGENCY_STOP.value
    assert res_high.state.value == "ACTION_TRIGGERED"

