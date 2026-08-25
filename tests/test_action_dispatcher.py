"""
Unit Tests for Action Dispatcher & Safety Whitelist
"""
import pytest
from android.config.constants import SafeActionType, GestureType
from android.actions.action_registry import ActionRegistry
from android.actions.action_dispatcher import ActionDispatcher
from android.models.gesture_models import GestureResult, GestureStateEnum


def test_action_registry_whitelist():
    """Verify that only safe actions are in the whitelist."""
    assert ActionRegistry.is_safe("TAP") is True
    assert ActionRegistry.is_safe("SCROLL_UP") is True
    assert ActionRegistry.is_safe("BACK") is True
    assert ActionRegistry.is_safe("HOME") is True
    assert ActionRegistry.is_safe("EMERGENCY_STOP") is True

    # Dangerous or arbitrary commands must be rejected
    assert ActionRegistry.is_safe("rm -rf /") is False
    assert ActionRegistry.is_safe("EXECUTE_SHELL") is False
    assert ActionRegistry.is_safe("SYSTEM_REBOOT") is False


def test_dispatcher_rejects_unauthorized_actions():
    """Verify dispatcher refuses to execute actions not in whitelist."""
    dispatcher = ActionDispatcher()
    fake_result = GestureResult(
        gesture="CUSTOM_GESTURE",
        confidence=0.99,
        action="UNAUTHORIZED_COMMAND",
        state=GestureStateEnum.ACTION_TRIGGERED
    )
    success = dispatcher.dispatch(fake_result)
    assert success is False


def test_dispatcher_emergency_stop_lockout():
    """Verify emergency stop locks dispatcher and drops all subsequent actions."""
    dispatcher = ActionDispatcher()

    # Trigger emergency stop
    stop_result = GestureResult(
        gesture=GestureType.FIST.value,
        confidence=0.95,
        action=SafeActionType.EMERGENCY_STOP.value,
        state=GestureStateEnum.ACTION_TRIGGERED
    )
    assert dispatcher.dispatch(stop_result) is True
    assert dispatcher.emergency_stopped is True

    # Subsequent tap must be dropped
    tap_result = GestureResult(
        gesture=GestureType.PINCH.value,
        confidence=0.90,
        action=SafeActionType.TAP.value,
        state=GestureStateEnum.ACTION_TRIGGERED,
        pointer_coords=(0.5, 0.5)
    )
    assert dispatcher.dispatch(tap_result) is False

    # Reset emergency stop
    dispatcher.reset_emergency_stop()
    assert dispatcher.emergency_stopped is False

    # Actions now allowed again
    assert dispatcher.dispatch(tap_result) is True

