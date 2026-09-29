"""
Gesture State Machine and Debounce Engine
Enforces lifecycle state transitions, priority states, debounce windows, and hold-time confirmations.
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
        pinch_hold_ms: int = 60,
        fist_hold_ms: int = 0
    ):
        self.default_debounce_ms = default_debounce_ms
        self.pinch_hold_ms = pinch_hold_ms
        self.fist_hold_ms = fist_hold_ms

        self.current_state: GestureStateEnum = GestureStateEnum.IDLE
        self.active_gesture: GestureType = GestureType.NONE
        self.last_action_timestamp: float = 0.0
        self.gesture_start_timestamp: float = 0.0
        self.last_triggered_gesture: GestureType = GestureType.NONE
        self.is_two_finger_scrolling: bool = False
        self.pinch_fired: bool = False

        # Custom per-gesture cooldown overrides (in milliseconds)
        self.cooldown_overrides: Dict[str, int] = {
            GestureType.INDEX_POINT.value: 15,          # Ultra-responsive continuous pointer
            GestureType.TWO_FINGER_TOUCHPAD.value: 15,  # Continuous touchpad cursor
            GestureType.TWO_FINGER_SCROLL.value: 40,    # Continuous touchpad scroll
            GestureType.PINCH_IN.value: 40,             # Continuous zoom out
            GestureType.PINCH_OUT.value: 40,            # Continuous zoom in
            GestureType.AIR_TAP.value: 280,             # Air tap click
            GestureType.PINCH.value: 350,               # Tap debounce
            GestureType.TWO_FINGER_TAP.value: 400,      # Secondary tap
            GestureType.SWIPE_UP.value: 400,
            GestureType.SWIPE_DOWN.value: 400,
            GestureType.SWIPE_LEFT.value: 500,
            GestureType.SWIPE_RIGHT.value: 500,
            GestureType.OPEN_PALM.value: 700,
            GestureType.TWO_FINGERS.value: 500,
            GestureType.THUMBS_UP.value: 600,
            GestureType.THUMBS_DOWN.value: 600,
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
            self.reset()
            return GestureResult(
                gesture=GestureType.NONE.value,
                confidence=0.0,
                action="NONE",
                state=GestureStateEnum.IDLE
            )

        # Reset pinch_fired and pinch hold timer when gesture drops out of PINCH
        if detected_gesture != GestureType.PINCH:
            self.pinch_fired = False
            if self.active_gesture == GestureType.PINCH:
                self.active_gesture = GestureType.NONE
                self.gesture_start_timestamp = 0.0

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

        # =========================================================================
        # 1. CONTINUOUS TOUCHPAD & POINTER MODES
        # =========================================================================
        if detected_gesture == GestureType.TWO_FINGER_TOUCHPAD:
            self.current_state = GestureStateEnum.ACTION_TRIGGERED if mapped_action != "NONE" else GestureStateEnum.TRACKING
            self.last_action_timestamp = now
            self.is_two_finger_scrolling = False
            if mapped_action == "NONE":
                return GestureResult(
                    gesture=detected_gesture.value,
                    confidence=confidence,
                    action="NONE",
                    state=GestureStateEnum.TRACKING,
                    pointer_coords=features.two_finger_center if features else None,
                    metadata={"continuous": True, "touchpad": True, "disabled": True}
                )
            return GestureResult(
                gesture=detected_gesture.value,
                confidence=confidence,
                action=mapped_action,
                state=GestureStateEnum.ACTION_TRIGGERED,
                pointer_coords=features.two_finger_center if features else None,
                metadata={
                    "continuous": True,
                    "touchpad": True,
                    "delta": features.two_finger_delta if features else (0.0, 0.0)
                }
            )

        if detected_gesture == GestureType.TWO_FINGER_SCROLL:
            self.current_state = GestureStateEnum.ACTION_TRIGGERED if mapped_action != "NONE" else GestureStateEnum.TRACKING
            self.last_action_timestamp = now
            self.is_two_finger_scrolling = True
            if mapped_action == "NONE":
                return GestureResult(
                    gesture=detected_gesture.value,
                    confidence=confidence,
                    action="NONE",
                    state=GestureStateEnum.TRACKING,
                    pointer_coords=features.two_finger_center if features else None,
                    metadata={"continuous": True, "disabled": True}
                )
            dy = features.two_finger_delta[1] if features else 0.0
            scroll_action = mapped_action if mapped_action not in ("NONE", "DEFAULT", SafeActionType.SCROLL_UP.value, SafeActionType.SCROLL_DOWN.value) else (
                SafeActionType.SCROLL_UP.value if dy < 0 else SafeActionType.SCROLL_DOWN.value
            )
            return GestureResult(
                gesture=detected_gesture.value,
                confidence=confidence,
                action=scroll_action,
                state=GestureStateEnum.ACTION_TRIGGERED,
                pointer_coords=features.two_finger_center if features else None,
                metadata={
                    "continuous": True,
                    "scroll_delta": dy,
                    "touchpad_scroll": True
                }
            )

        if detected_gesture == GestureType.INDEX_POINT or mapped_action == SafeActionType.POINTER_MOVE.value:
            self.current_state = GestureStateEnum.ACTION_TRIGGERED if mapped_action != "NONE" else GestureStateEnum.TRACKING
            self.last_action_timestamp = now
            self.is_two_finger_scrolling = False
            if mapped_action == "NONE":
                return GestureResult(
                    gesture=detected_gesture.value,
                    confidence=confidence,
                    action="NONE",
                    state=GestureStateEnum.TRACKING,
                    pointer_coords=features.pointer_pos if features else None,
                    metadata={"continuous": True, "disabled": True}
                )
            coords = features.pointer_pos if features else None
            if detected_gesture == GestureType.OPEN_PALM and features:
                coords = features.palm_center
            return GestureResult(
                gesture=detected_gesture.value,
                confidence=confidence,
                action=mapped_action,
                state=GestureStateEnum.ACTION_TRIGGERED,
                pointer_coords=coords,
                metadata={"continuous": True}
            )

        # =========================================================================
        # 2. CONTINUOUS PROPORTIONAL ZOOM (PINCH_IN / PINCH_OUT)
        # =========================================================================
        if detected_gesture in (GestureType.PINCH_IN, GestureType.PINCH_OUT):
            self.current_state = GestureStateEnum.ACTION_TRIGGERED if mapped_action != "NONE" else GestureStateEnum.TRACKING
            self.last_action_timestamp = now
            if mapped_action == "NONE":
                return GestureResult(
                    gesture=detected_gesture.value,
                    confidence=confidence,
                    action="NONE",
                    state=GestureStateEnum.TRACKING,
                    pointer_coords=features.pointer_pos if features else None,
                    metadata={"continuous": True, "disabled": True}
                )
            action = mapped_action if mapped_action not in ("NONE", "DEFAULT", SafeActionType.ZOOM_IN.value, SafeActionType.ZOOM_OUT.value) else (
                SafeActionType.ZOOM_IN.value if detected_gesture == GestureType.PINCH_OUT else SafeActionType.ZOOM_OUT.value
            )
            return GestureResult(
                gesture=detected_gesture.value,
                confidence=confidence,
                action=action,
                state=GestureStateEnum.ACTION_TRIGGERED,
                pointer_coords=features.pointer_pos if features else None,
                metadata={
                    "continuous": True,
                    "pinch_delta": features.pinch_delta if features else 0.0
                }
            )

        # =========================================================================
        # 3. DISCRETE GESTURES: Check Cooldown / Debounce
        # =========================================================================
        # If pinch has already fired a tap during this hold, require release before firing again
        if detected_gesture == GestureType.PINCH and self.pinch_fired:
            return GestureResult(
                gesture=detected_gesture.value,
                confidence=confidence,
                action="NONE",
                state=GestureStateEnum.TRACKING,
                pointer_coords=features.pointer_pos if features else None
            )

        if time_since_last_action_ms < cooldown_ms:
            self.current_state = GestureStateEnum.COOLDOWN
            return GestureResult(
                gesture=detected_gesture.value,
                confidence=confidence,
                action="NONE",  # Suppressed by cooldown
                state=GestureStateEnum.COOLDOWN,
                pointer_coords=features.pointer_pos if features else None
            )

        # Hold-time requirement for PINCH TAP
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

            held_duration_ms = (now - self.gesture_start_timestamp) * 1000.0
            if held_duration_ms < self.pinch_hold_ms:
                return GestureResult(
                    gesture=detected_gesture.value,
                    confidence=confidence,
                    action="NONE",
                    state=GestureStateEnum.GESTURE_DETECTED,
                    pointer_coords=features.pointer_pos if features else None
                )

        # Hold-time requirement for FIST EMERGENCY STOP (prevents accidental instant lockouts)
        if detected_gesture == GestureType.FIST and self.fist_hold_ms > 0:
            if self.active_gesture != GestureType.FIST:
                self.active_gesture = GestureType.FIST
                self.gesture_start_timestamp = now
                return GestureResult(
                    gesture=detected_gesture.value,
                    confidence=confidence,
                    action="NONE",
                    state=GestureStateEnum.GESTURE_DETECTED,
                    pointer_coords=features.pointer_pos if features else None
                )

            held_duration_ms = (now - self.gesture_start_timestamp) * 1000.0
            if held_duration_ms < self.fist_hold_ms:
                return GestureResult(
                    gesture=detected_gesture.value,
                    confidence=confidence,
                    action="NONE",
                    state=GestureStateEnum.GESTURE_DETECTED,
                    pointer_coords=features.pointer_pos if features else None
                )

        # Avoid triggering two-finger tap while scrolling
        if detected_gesture == GestureType.TWO_FINGER_TAP and self.is_two_finger_scrolling:
            return GestureResult(
                gesture=detected_gesture.value,
                confidence=confidence,
                action="NONE",
                state=GestureStateEnum.TRACKING
            )

        # =========================================================================
        # 4. Trigger Discrete Action Transition
        # =========================================================================
        if mapped_action == "NONE":
            self.current_state = GestureStateEnum.TRACKING
            return GestureResult(
                gesture=detected_gesture.value,
                confidence=confidence,
                action="NONE",
                state=GestureStateEnum.TRACKING,
                pointer_coords=features.pointer_pos if features else None
            )

        self.current_state = GestureStateEnum.ACTION_TRIGGERED
        self.active_gesture = detected_gesture
        self.last_action_timestamp = now
        self.last_triggered_gesture = detected_gesture
        self.is_two_finger_scrolling = False
        if detected_gesture == GestureType.PINCH:
            self.pinch_fired = True

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
        self.is_two_finger_scrolling = False
        self.pinch_fired = False
