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
    sm = GestureStateMachine(default_debounce_ms=400)
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

