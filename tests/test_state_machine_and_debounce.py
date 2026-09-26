"""
Unit Tests for State Machine and Debounce Engine
"""
import time
import pytest
from android.config.constants import GestureType, SafeActionType
from android.gestures.state_machine import GestureStateMachine
from android.gestures.feature_extractor import HandFeatures
from android.models.gesture_models import GestureStateEnum


def test_state_machine_idle_transition():
    """Verify transition to IDLE when no hand is present."""
    sm = GestureStateMachine()
    result = sm.process_frame(
        hand_detected=False,
        detected_gesture=GestureType.NONE,
        confidence=0.0,
        features=None
    )
    assert result.state == GestureStateEnum.IDLE
    assert result.action == "NONE"


def test_state_machine_debounce_cooldown():
    """Verify that discrete actions enter cooldown and prevent repeated firings."""
    sm = GestureStateMachine(default_debounce_ms=400, palm_hold_ms=0)
    features = HandFeatures(extended_count=5)

    # Frame 1: Trigger OPEN_PALM
    res1 = sm.process_frame(
        hand_detected=True,
        detected_gesture=GestureType.OPEN_PALM,
        confidence=0.90,
        features=features,
        mapped_action=SafeActionType.PAUSE_GESTURES.value
    )
    assert res1.state == GestureStateEnum.ACTION_TRIGGERED
    assert res1.action == SafeActionType.PAUSE_GESTURES.value

    # Frame 2: Immediately afterwards (10ms later) -> should be suppressed in COOLDOWN
    res2 = sm.process_frame(
        hand_detected=True,
        detected_gesture=GestureType.OPEN_PALM,
        confidence=0.90,
        features=features,
        mapped_action=SafeActionType.PAUSE_GESTURES.value
    )
    assert res2.state == GestureStateEnum.COOLDOWN
    assert res2.action == "NONE"


def test_continuous_pointer_movement_not_blocked():
    """Verify that continuous index pointing generates continuous pointer actions."""
    sm = GestureStateMachine()
    features = HandFeatures(pointer_pos=(0.42, 0.58), index_extended=True)

    res1 = sm.process_frame(
        hand_detected=True,
        detected_gesture=GestureType.INDEX_POINT,
        confidence=0.85,
        features=features,
        mapped_action=SafeActionType.POINTER_MOVE.value
    )
    assert res1.state == GestureStateEnum.ACTION_TRIGGERED
    assert res1.action == SafeActionType.POINTER_MOVE.value
    assert res1.pointer_coords == (0.42, 0.58)

    # Immediate next frame should still dispatch pointer move
    features.pointer_pos = (0.44, 0.60)
    res2 = sm.process_frame(
        hand_detected=True,
        detected_gesture=GestureType.INDEX_POINT,
        confidence=0.85,
        features=features,
        mapped_action=SafeActionType.POINTER_MOVE.value
    )
    assert res2.state == GestureStateEnum.ACTION_TRIGGERED
    assert res2.action == SafeActionType.POINTER_MOVE.value
    assert res2.pointer_coords == (0.44, 0.60)


def test_pinch_hold_time_requirement():
    """Verify that pinch requires minimum hold time before triggering tap."""
    sm = GestureStateMachine(pinch_hold_ms=60)
    features = HandFeatures(pinch_distance_norm=0.20)

    # Frame 1: Pinch first detected -> state should be GESTURE_DETECTED, action NONE
    res1 = sm.process_frame(
        hand_detected=True,
        detected_gesture=GestureType.PINCH,
        confidence=0.85,
        features=features,
        mapped_action=SafeActionType.TAP.value
    )
    assert res1.state == GestureStateEnum.GESTURE_DETECTED
    assert res1.action == "NONE"

    # Wait for hold duration to elapse
    time.sleep(0.08)

    # Frame 2: Pinch held long enough -> should trigger ACTION_TRIGGERED
    res2 = sm.process_frame(
        hand_detected=True,
        detected_gesture=GestureType.PINCH,
        confidence=0.85,
        features=features,
        mapped_action=SafeActionType.TAP.value
    )
    assert res2.state == GestureStateEnum.ACTION_TRIGGERED
    assert res2.action == SafeActionType.TAP.value


def test_pinch_hold_fires_exactly_once_and_requires_release_regression():
    """Regression test #9c: Holding pinch fires only one TAP, requiring release before firing again."""
    sm = GestureStateMachine(pinch_hold_ms=30)
    features = HandFeatures(pinch_distance_norm=0.15)

    # 1. Start pinch
    sm.process_frame(True, GestureType.PINCH, 0.90, features, mapped_action=SafeActionType.TAP.value)
    time.sleep(0.04)

    # 2. Hold satisfied -> fires TAP
    res1 = sm.process_frame(True, GestureType.PINCH, 0.90, features, mapped_action=SafeActionType.TAP.value)
    assert res1.action == SafeActionType.TAP.value

    # 3. Keep holding pinch even past cooldown window (e.g. 400ms later)
    # Simulate time jump or sleep past 350ms cooldown
    time.sleep(0.36)
    res_held = sm.process_frame(True, GestureType.PINCH, 0.90, features, mapped_action=SafeActionType.TAP.value)
    # Must NOT fire another tap!
    assert res_held.action == "NONE"

    # 4. Release pinch (gesture drops out to NONE or another gesture)
    sm.process_frame(True, GestureType.OPEN_PALM, 0.90, HandFeatures(extended_count=5), mapped_action="NONE")

    # 5. Now pinch again
    sm.process_frame(True, GestureType.PINCH, 0.90, features, mapped_action=SafeActionType.TAP.value)
    time.sleep(0.04)
    res2 = sm.process_frame(True, GestureType.PINCH, 0.90, features, mapped_action=SafeActionType.TAP.value)
    assert res2.action == SafeActionType.TAP.value


def test_disabled_mapping_disables_continuous_gestures_regression():
    """Regression test #9d: Continuous gestures return action='NONE' when mapped_action == 'NONE'."""
    sm = GestureStateMachine()
    feats = HandFeatures(pointer_pos=(0.5, 0.5), two_finger_center=(0.5, 0.5), two_finger_delta=(0.0, -0.05), pinch_delta=0.03)

    # 1. TWO_FINGER_TOUCHPAD with mapped_action="NONE"
    res_pad = sm.process_frame(True, GestureType.TWO_FINGER_TOUCHPAD, 0.85, feats, mapped_action="NONE")
    assert res_pad.action == "NONE"

    # 2. TWO_FINGER_SCROLL with mapped_action="NONE"
    res_scroll = sm.process_frame(True, GestureType.TWO_FINGER_SCROLL, 0.85, feats, mapped_action="NONE")
    assert res_scroll.action == "NONE"

    # 3. INDEX_POINT with mapped_action="NONE"
    res_point = sm.process_frame(True, GestureType.INDEX_POINT, 0.85, feats, mapped_action="NONE")
    assert res_point.action == "NONE"

    # 4. PINCH_OUT (zoom in) with mapped_action="NONE"
    res_pinch_out = sm.process_frame(True, GestureType.PINCH_OUT, 0.85, feats, mapped_action="NONE")
    assert res_pinch_out.action == "NONE"

    # 5. PINCH_IN (zoom out) with mapped_action="NONE"
    feats.pinch_delta = -0.03
    res_pinch_in = sm.process_frame(True, GestureType.PINCH_IN, 0.85, feats, mapped_action="NONE")
    assert res_pinch_in.action == "NONE"




@pytest.mark.parametrize("gesture, action", [
    (GestureType.AIR_TAP, SafeActionType.TAP),
    (GestureType.TWO_FINGER_TAP, SafeActionType.SECONDARY_TAP),
    (GestureType.THUMBS_UP, SafeActionType.CONFIRM),
    (GestureType.THUMBS_DOWN, SafeActionType.REJECT),
    (GestureType.SWIPE_LEFT, SafeActionType.BACK),
    (GestureType.FIST, SafeActionType.EMERGENCY_STOP),
])
def test_pointer_updates_do_not_starve_discrete_actions(monkeypatch, gesture, action):
    now = [100.0]
    monkeypatch.setattr("android.gestures.state_machine.time.time", lambda: now[0])
    sm = GestureStateMachine()
    for _ in range(10):
        sm.process_frame(True, GestureType.INDEX_POINT, 0.95, HandFeatures(), "POINTER_MOVE")
        now[0] += 0.016
    result = sm.process_frame(True, gesture, 0.95, HandFeatures(), action.value)
    assert result.action == action.value
    # Movement must not reset the previous discrete action's cooldown either.
    sm.process_frame(True, GestureType.INDEX_POINT, 0.95, HandFeatures(), "POINTER_MOVE")
    result = sm.process_frame(True, gesture, 0.95, HandFeatures(), action.value)
    if action != SafeActionType.EMERGENCY_STOP:
        assert result.action == "NONE"


def test_pointer_to_pinch_only_waits_for_hold(monkeypatch):
    now = [100.0]
    monkeypatch.setattr("android.gestures.state_machine.time.time", lambda: now[0])
    sm = GestureStateMachine()
    sm.process_frame(True, GestureType.INDEX_POINT, 0.95, HandFeatures(), "POINTER_MOVE")
    assert sm.process_frame(True, GestureType.PINCH, 0.95, HandFeatures(), "TAP").action == "NONE"
    now[0] += 0.08
    assert sm.process_frame(True, GestureType.PINCH, 0.95, HandFeatures(), "TAP").action == "TAP"


def test_palm_hold_latches_until_deliberate_release(monkeypatch):
    from unittest.mock import patch
    from android.actions.action_dispatcher import ActionDispatcher

    now = [100.0]
    monkeypatch.setattr("android.gestures.state_machine.time.time", lambda: now[0])
    sm = GestureStateMachine()
    with patch.object(ActionDispatcher, "_init_executors"):
        dispatcher = ActionDispatcher()

    def palm():
        result = sm.process_frame(True, GestureType.OPEN_PALM, 0.95, HandFeatures(), "PAUSE_GESTURES")
        dispatcher.dispatch(result)
        return result

    assert palm().action == "NONE"
    now[0] += 0.16
    assert palm().action == "PAUSE_GESTURES"
    assert dispatcher.gestures_paused
    for _ in range(5):
        now[0] += 1.0
        assert palm().action == "NONE"
    sm.process_frame(True, GestureType.NONE, 0.0, None)
    assert palm().action == "NONE"  # One noisy frame cannot rearm.
    for _ in range(3):
        sm.process_frame(True, GestureType.INDEX_POINT, 0.95, HandFeatures(), "POINTER_MOVE")
    assert palm().action == "NONE"
    now[0] += 0.16
    assert palm().action == "PAUSE_GESTURES"
    assert not dispatcher.gestures_paused


def test_emergency_stop_interrupts_discrete_cooldown():
    sm = GestureStateMachine()
    sm.process_frame(True, GestureType.THUMBS_UP, 0.95, HandFeatures(), "CONFIRM")
    result = sm.process_frame(True, GestureType.FIST, 0.95, HandFeatures(), "EMERGENCY_STOP", 0.80)
    assert result.action == "EMERGENCY_STOP"


def test_tap_is_blocked_during_scroll_but_recovers_after_rest():
    sm = GestureStateMachine()
    sm.process_frame(True, GestureType.TWO_FINGER_SCROLL, 0.95, HandFeatures(), "SCROLL_UP")
    assert sm.process_frame(True, GestureType.TWO_FINGER_TAP, 0.95, HandFeatures(), "SECONDARY_TAP").action == "NONE"
    sm.process_frame(True, GestureType.TWO_FINGER_TOUCHPAD, 0.95, HandFeatures(), "POINTER_MOVE")
    assert sm.process_frame(True, GestureType.TWO_FINGER_TAP, 0.95, HandFeatures(), "SECONDARY_TAP").action == "SECONDARY_TAP"
