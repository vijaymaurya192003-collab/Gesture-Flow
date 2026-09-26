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
from android.actions.action_registry import ActionRegistry
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
    assert classifier.classify(hand)[0] == GestureType.NONE
    assert classifier.classify(hand)[0] == GestureType.NONE
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



@pytest.mark.parametrize("depth", [-0.06, 0.06])
def test_smoother_preserves_depth_only_motion(depth):
    from android.vision.landmark_smoother import LandmarkSmoother

    smoother = LandmarkSmoother()
    rest = smoother.smooth(create_hand_skeleton())
    moved = smoother.smooth(create_hand_skeleton(index_z=depth))
    assert moved[8].x == rest[8].x
    assert moved[8].y == rest[8].y
    assert 0 < abs(moved[8].z) < abs(depth)
    assert moved[8].z * depth > 0


def test_air_tap_survives_smoothing():
    from android.vision.landmark_smoother import LandmarkSmoother

    smoother = LandmarkSmoother()
    classifier = GestureClassifier()
    classifier.classify(smoother.smooth(create_hand_skeleton()))
    gesture, _, _ = classifier.classify(
        smoother.smooth(create_hand_skeleton(index_z=-0.06))
    )
    assert gesture == GestureType.AIR_TAP


def test_smoother_deadband_and_tracking_reset():
    from android.vision.landmark_smoother import LandmarkSmoother

    smoother = LandmarkSmoother()
    rest = smoother.smooth(create_hand_skeleton())
    jitter = smoother.smooth(create_hand_skeleton(index_z=0.001))
    assert jitter[8] == rest[8]
    assert smoother.smooth([]) == []
    assert smoother.smooth(create_hand_skeleton(index_z=-0.06))[8].z == -0.06


@pytest.mark.parametrize("threshold, confidence, enabled, expected", [
    (0.80, 0.79, True, "NONE"),
    (0.80, 0.80, True, "EMERGENCY_STOP"),
    (0.95, 0.92, True, "NONE"),
    (0.80, 0.95, False, "NONE"),
    (None, 0.95, True, "NONE"),
])
def test_worker_applies_mapping_confidence(threshold, confidence, enabled, expected):
    import threading
    from unittest.mock import MagicMock, patch
    from android.main import AsyncVisionWorker
    from android.actions.action_dispatcher import ActionDispatcher
    from android.models.gesture_models import HandFrameData, GestureMappingItem

    # Run the actual worker loop once without a camera, detector, or OS input.
    worker = AsyncVisionWorker.__new__(AsyncVisionWorker)
    worker.camera = MagicMock()
    worker.camera.read_frame.return_value = (True, object())
    worker.camera.get_fps.return_value = 30.0
    worker.detector = MagicMock()
    worker.detector.detect_hands.return_value = HandFrameData(
        hand_detected=True, landmarks=create_hand_skeleton(index_extended=False)
    )
    worker.smoother = MagicMock()
    worker.classifier = MagicMock()
    worker.classifier.classify.return_value = (GestureType.FIST, confidence, HandFeatures())
    worker.state_machine = MagicMock(wraps=GestureStateMachine())
    with patch.object(ActionDispatcher, "_init_executors"):
        worker.dispatcher = ActionDispatcher()
    worker.dispatcher.set_mappings({} if threshold is None else {
        "FIST": GestureMappingItem(gesture="FIST", action="EMERGENCY_STOP",
                                   confidence_threshold=threshold, enabled=enabled)
    })
    worker._lock = threading.Lock()
    worker._running = True
    worker._frame_count = 0
    worker.debug_latency = False
    with patch("android.main.time.sleep", side_effect=lambda _: setattr(worker, "_running", False)):
        worker._worker_loop()
    assert worker.state_machine.process_frame.call_args.kwargs["min_confidence"] == (
        threshold if threshold is not None else 0.60
    )
    assert worker.latest_result.action == expected
    assert worker.dispatcher.emergency_stopped == (expected == "EMERGENCY_STOP")


@pytest.mark.parametrize("rotation", [0.0, 0.5, 1.0])
def test_geometry_rejects_partly_curled_middle_under_rotation(rotation):
    import math
    hand = create_hand_skeleton()
    # Old wrist ratio > 1.08, but sharply bent at PIP: never a second finger.
    hand[12] = LandmarkPoint(x=0.64, y=0.44, z=0.0)
    for lm in hand:
        y, z = lm.y - 0.8, lm.z
        lm.y = 0.8 + y * math.cos(rotation) - z * math.sin(rotation)
        lm.z = y * math.sin(rotation) + z * math.cos(rotation)
    features = extract_hand_features(hand)
    assert features.index_extended
    assert not features.middle_extended
    assert not features.is_two_finger_touchpad


def test_dip_hook_is_not_extended():
    hand = create_hand_skeleton()
    hand[8] = LandmarkPoint(x=0.45, y=0.43, z=0.0)
    assert not extract_hand_features(hand).index_extended


def test_relaxed_hand_is_not_fist_or_pinch():
    hand = create_hand_skeleton(index_extended=False, thumb_pos="extended")
    for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18)):
        hand[tip] = LandmarkPoint(x=hand[pip].x + 0.06, y=hand[pip].y - 0.02, z=0.0)
    gesture, _, features = GestureClassifier().classify(hand)
    assert not features.is_fist
    assert gesture == GestureType.NONE


def test_compact_fist_wins_over_incidental_pinch_contact():
    hand = create_hand_skeleton(index_extended=False)
    gesture, confidence, features = GestureClassifier().classify(hand)
    assert features.pinch_distance_norm < 0.45
    assert gesture == GestureType.FIST
    assert confidence >= 0.80


def test_two_finger_confirmation_resets_on_noise_and_hand_loss():
    classifier = GestureClassifier()
    pointing = create_hand_skeleton()
    touchpad = create_hand_skeleton(middle_extended=True, two_finger_close=True)
    for _ in range(5):
        assert classifier.classify(pointing)[0] == GestureType.INDEX_POINT
        assert classifier.classify(touchpad)[0] == GestureType.NONE
    classifier.classify([])
    for _ in range(2):
        assert classifier.classify(touchpad)[0] == GestureType.NONE
    assert classifier.classify(touchpad)[0] == GestureType.TWO_FINGER_TOUCHPAD
    assert classifier.classify(pointing)[0] == GestureType.INDEX_POINT


@pytest.mark.parametrize("dx, dy, expected", [
    (0.03, 0.0, GestureType.TWO_FINGER_TOUCHPAD),
    (0.0, -0.03, GestureType.TWO_FINGER_SCROLL),
    (0.0, 0.03, GestureType.TWO_FINGER_SCROLL),
])
def test_confirmed_touchpad_and_scroll_still_work(dx, dy, expected):
    classifier = GestureClassifier()
    for _ in range(3):
        classifier.classify(create_hand_skeleton(middle_extended=True, two_finger_close=True))
    hand = create_hand_skeleton(middle_extended=True, two_finger_close=True)
    hand = [LandmarkPoint(x=p.x + dx, y=p.y + dy, z=p.z) for p in hand]
    assert classifier.classify(hand)[0] == expected


def test_pinch_onset_from_pointer_is_not_zoom():
    classifier = GestureClassifier()
    classifier.classify(create_hand_skeleton())
    assert classifier.classify(create_hand_skeleton(pinch=True))[0] == GestureType.PINCH


class TwoFingerSequence:
    """Deterministic camera-free frames through the real gesture pipeline."""

    def __init__(self, monkeypatch, fps=30, smooth=False):
        from unittest.mock import MagicMock, patch
        from android.actions.action_dispatcher import ActionDispatcher
        from android.vision.landmark_smoother import LandmarkSmoother
        self.now = 100.0
        self.dt = 1.0 / fps
        monkeypatch.setattr("android.gestures.gesture_classifier.time.monotonic", lambda: self.now)
        monkeypatch.setattr("android.gestures.state_machine.time.time", lambda: self.now)
        self.classifier = GestureClassifier()
        self.smoother = LandmarkSmoother() if smooth else None
        self.machine = GestureStateMachine()
        with patch.object(ActionDispatcher, "_init_executors"):
            self.dispatcher = ActionDispatcher()
        self.executor = MagicMock()
        self.dispatcher._desktop_executor = self.executor
        self.gestures = []
        self.actions = []

    def frame(self, depth=0.0, middle_depth=None, dx=0.0, dy=0.0, whole_hand_z=0.0, hand_lost=False):
        hand = create_hand_skeleton(middle_extended=True, two_finger_close=True)
        for base, z in ((5, depth), (9, depth if middle_depth is None else middle_depth)):
            for offset in (1, 2, 3):
                hand[base + offset].z = z * offset / 3.0
        hand = [LandmarkPoint(x=p.x + dx, y=p.y + dy, z=p.z + whole_hand_z) for p in hand]
        if hand_lost:
            hand = []
        if self.smoother:
            hand = self.smoother.smooth(hand)
        gesture, confidence, features = self.classifier.classify(hand)
        mapping = self.dispatcher.get_mapping_item(gesture)
        result = self.machine.process_frame(
            bool(hand), gesture, confidence, features,
            self.dispatcher.get_mapped_action_name(gesture),
            mapping.confidence_threshold if mapping else 0.60
        )
        self.dispatcher.dispatch(result)
        self.gestures.append(gesture)
        self.actions.append(result.action)
        self.now += self.dt
        return gesture

    def rest(self, seconds=0.35, **kwargs):
        import math
        for _ in range(math.ceil(seconds / self.dt)):
            self.frame(**kwargs)


@pytest.mark.parametrize("fps", [15, 30, 60])
@pytest.mark.parametrize("smooth", [False, True])
def test_two_finger_tap_reaches_executor_once_on_release(monkeypatch, fps, smooth):
    sequence = TwoFingerSequence(monkeypatch, fps, smooth)
    sequence.rest()
    sequence.rest(0.08, depth=-0.06)
    assert GestureType.TWO_FINGER_TAP not in sequence.gestures  # Not on press.
    sequence.rest()
    assert sequence.gestures.count(GestureType.TWO_FINGER_TAP) == 1
    assert sequence.actions.count("SECONDARY_TAP") == 1
    right_clicks = [call for call in sequence.executor.execute.call_args_list
                    if call.kwargs["action"] == SafeActionType.SECONDARY_TAP]
    assert len(right_clicks) == 1
    sequence.rest(0.5)
    sequence.rest(0.08, depth=-0.06)
    sequence.rest()
    assert sequence.actions.count("SECONDARY_TAP") == 2


@pytest.mark.parametrize("case", ["stationary", "one_tip", "unarmed", "slow_drift", "long_press", "lost", "scroll", "whole_hand"])
def test_two_finger_tap_rejects_non_taps(monkeypatch, case):
    sequence = TwoFingerSequence(monkeypatch)
    if case != "unarmed":
        sequence.rest()
    if case == "stationary":
        sequence.rest(1.0)
    elif case == "one_tip":
        sequence.frame(depth=-0.06, middle_depth=0.0)
    elif case == "unarmed":
        sequence.frame(depth=-0.06)
    elif case == "slow_drift":
        for step in range(1, 13):
            sequence.frame(depth=-0.005 * step)
    elif case == "long_press":
        sequence.rest(0.5, depth=-0.06)
    elif case == "lost":
        sequence.frame(depth=-0.06)
        sequence.frame(hand_lost=True)
    elif case == "scroll":
        sequence.frame(depth=-0.06, dy=-0.04)
        assert sequence.gestures[-1] == GestureType.TWO_FINGER_SCROLL
    elif case == "whole_hand":
        sequence.frame(whole_hand_z=-0.06)
    sequence.rest()
    assert GestureType.TWO_FINGER_TAP not in sequence.gestures
    assert "SECONDARY_TAP" not in sequence.actions


def test_scroll_then_rest_allows_new_two_finger_tap(monkeypatch):
    sequence = TwoFingerSequence(monkeypatch)
    sequence.rest()
    sequence.frame(dy=-0.04)
    assert sequence.gestures[-1] == GestureType.TWO_FINGER_SCROLL
    sequence.rest(dy=-0.04)
    sequence.rest(0.08, depth=-0.06, dy=-0.04)
    sequence.rest(dy=-0.04)
    assert sequence.actions.count("SECONDARY_TAP") == 1
