"""
Gesture State Machine and Debounce Engine
Enforces lifecycle state transitions, debounce windows, and hold-time confirmations.
"""
import time
from typing import Optional, Dict
from android.config.constants import GestureType, SafeActionType
from android.gestures.feature_extractor import HandFeatures
from android.models.gesture_models import GestureStateEnum, GestureResult


class GestureStateMachine:
    """
    Manages gesture state transitions and debounce logic.
    Transitions:
    IDLE -> TRACKING -> GESTURE_DETECTED -> ACTION_TRIGGERED -> COOLDOWN -> TRACKING
    """

    def __init__(
        self,
        default_debounce_ms: int = 400,
        pinch_hold_ms: int = 80
    ):
        self.default_debounce_ms = default_debounce_ms
        self.pinch_hold_ms = pinch_hold_ms

        self.current_state: GestureStateEnum = GestureStateEnum.IDLE
        self.active_gesture: GestureType = GestureType.NONE
        self.last_action_timestamp: float = 0.0
        self.gesture_start_timestamp: float = 0.0
        self.last_triggered_gesture: GestureType = GestureType.NONE

        # Custom per-gesture cooldown overrides (in milliseconds)
        self.cooldown_overrides: Dict[str, int] = {
            GestureType.INDEX_POINT.value: 15,   # Ultra-responsive continuous pointer updates
            GestureType.PINCH.value: 400,        # Tap debounce
            GestureType.SWIPE_UP.value: 450,
            GestureType.SWIPE_DOWN.value: 450,
            GestureType.SWIPE_LEFT.value: 550,
            GestureType.SWIPE_RIGHT.value: 550,
            GestureType.OPEN_PALM.value: 700,
            GestureType.TWO_FINGERS.value: 500,
            GestureType.FIST.value: 800
        }

    def set_cooldown(self, gesture_name: str, cooldown_ms: int) -> None:
        """Configure custom debounce cooldown for a gesture."""
        self.cooldown_overrides[gesture_name] = max(10, cooldown_ms)

    def process_frame(
        self,
        hand_detected: bool,
        detected_gesture: GestureType,
        confidence: float,
        features: Optional[HandFeatures],
        mapped_action: str = "NONE",
        min_confidence: float = 0.60
    ) -> GestureResult:
        """
        Process a classified frame through the state machine.
        Returns a GestureResult indicating whether an action should be triggered.
        """
        now = time.time()
        now_ms = now * 1000.0

        # If no hand detected, transition to IDLE
        if not hand_detected:
            self.current_state = GestureStateEnum.IDLE
            self.active_gesture = GestureType.NONE
            return GestureResult(
                gesture=GestureType.NONE.value,
                confidence=0.0,
                action="NONE",
                state=GestureStateEnum.IDLE
            )

        # Check confidence floor
        if confidence < min_confidence or detected_gesture == GestureType.NONE:
            self.current_state = GestureStateEnum.TRACKING
            self.active_gesture = GestureType.NONE
            return GestureResult(
                gesture=GestureType.NONE.value,
                confidence=confidence,
                action="NONE",
                state=GestureStateEnum.TRACKING,
                pointer_coords=features.pointer_pos if features else None
            )

        cooldown_ms = self.cooldown_overrides.get(detected_gesture.value, self.default_debounce_ms)
        time_since_last_action_ms = now_ms - (self.last_action_timestamp * 1000.0)

        # 1. CONTINUOUS GESTURE: INDEX_POINT (Pointer movement)
        if detected_gesture == GestureType.INDEX_POINT:
            self.current_state = GestureStateEnum.ACTION_TRIGGERED
            self.last_action_timestamp = now
            effective_action = mapped_action if mapped_action != "NONE" else SafeActionType.POINTER_MOVE.value
            return GestureResult(
                gesture=detected_gesture.value,
                confidence=confidence,
                action=effective_action,
                state=GestureStateEnum.ACTION_TRIGGERED,
                pointer_coords=features.pointer_pos if features else None,
                metadata={"continuous": True}
            )

        # 2. DISCRETE GESTURES: Check Cooldown / Debounce
        if time_since_last_action_ms < cooldown_ms:
            self.current_state = GestureStateEnum.COOLDOWN
            return GestureResult(
                gesture=detected_gesture.value,
                confidence=confidence,
                action="NONE",  # Suppressed by cooldown
                state=GestureStateEnum.COOLDOWN,
                pointer_coords=features.pointer_pos if features else None
            )

        # 3. Hold-time requirement for PINCH (prevent accidental brief touch)
        if detected_gesture == GestureType.PINCH:
            if self.active_gesture != GestureType.PINCH:
                self.active_gesture = GestureType.PINCH
                self.gesture_start_timestamp = now
                return GestureResult(
                    gesture=detected_gesture.value,
                    confidence=confidence,
                    action="NONE",  # Still holding
                    state=GestureStateEnum.GESTURE_DETECTED,
                    pointer_coords=features.pointer_pos if features else None
                )

            # Check if held long enough
            held_duration_ms = (now - self.gesture_start_timestamp) * 1000.0
            if held_duration_ms < self.pinch_hold_ms:
                return GestureResult(
                    gesture=detected_gesture.value,
                    confidence=confidence,
                    action="NONE",
                    state=GestureStateEnum.GESTURE_DETECTED,
                    pointer_coords=features.pointer_pos if features else None
                )

        # 4. Trigger Action Transition
        self.current_state = GestureStateEnum.ACTION_TRIGGERED
        self.active_gesture = detected_gesture
        self.last_action_timestamp = now
        self.last_triggered_gesture = detected_gesture

        return GestureResult(
            gesture=detected_gesture.value,
            confidence=confidence,
            action=mapped_action,
            state=GestureStateEnum.ACTION_TRIGGERED,
            pointer_coords=features.pointer_pos if features else None
        )

    def reset(self) -> None:
        """Reset state machine to initial IDLE state."""
        self.current_state = GestureStateEnum.IDLE
        self.active_gesture = GestureType.NONE
        self.last_action_timestamp = 0.0
        self.gesture_start_timestamp = 0.0
