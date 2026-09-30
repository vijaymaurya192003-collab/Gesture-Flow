"""
Constants and Enums for Gesture Flow
Defines all supported gesture types, safe action types, touchpad configurations, and landmark mappings.
"""
from enum import Enum


class GestureType(str, Enum):
    """Supported gesture classifications in Gesture Flow."""
    NONE = "NONE"
    INDEX_POINT = "INDEX_POINT"
    AIR_TAP = "AIR_TAP"
    PINCH = "PINCH"
    PINCH_IN = "PINCH_IN"      # Continuous Proportional Zoom Out
    PINCH_OUT = "PINCH_OUT"    # Continuous Proportional Zoom In
    TWO_FINGERS = "TWO_FINGERS"  # Peace / V-Sign (Media or configurable)
    TWO_FINGER_TOUCHPAD = "TWO_FINGER_TOUCHPAD"  # Two-finger laptop touchpad pointer tracking
    TWO_FINGER_SCROLL = "TWO_FINGER_SCROLL"      # Continuous two-finger vertical/horizontal scrolling
    TWO_FINGER_TAP = "TWO_FINGER_TAP"            # Secondary action / context menu
    SWIPE_UP = "SWIPE_UP"
    SWIPE_DOWN = "SWIPE_DOWN"
    SWIPE_LEFT = "SWIPE_LEFT"
    SWIPE_RIGHT = "SWIPE_RIGHT"
    OPEN_PALM = "OPEN_PALM"
    FIST = "FIST"
    THUMBS_UP = "THUMBS_UP"
    THUMBS_DOWN = "THUMBS_DOWN"


class SafeActionType(str, Enum):
    """
    Explicit whitelist of safe actions.
    No arbitrary shell commands are permitted.
    """
    NONE = "NONE"
    POINTER_MOVE = "POINTER_MOVE"
    TAP = "TAP"
    SECONDARY_TAP = "SECONDARY_TAP"
    SCROLL_UP = "SCROLL_UP"
    SCROLL_DOWN = "SCROLL_DOWN"
    ZOOM_IN = "ZOOM_IN"
    ZOOM_OUT = "ZOOM_OUT"
    BACK = "BACK"
    FORWARD = "FORWARD"
    HOME = "HOME"
    RECENTS = "RECENTS"
    CONFIRM = "CONFIRM"
    REJECT = "REJECT"
    VOLUME_UP = "VOLUME_UP"
    VOLUME_DOWN = "VOLUME_DOWN"
    MEDIA_PLAY_PAUSE = "MEDIA_PLAY_PAUSE"
    PAUSE_GESTURES = "PAUSE_GESTURES"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    RESET_STATE = "RESET_STATE"


class TouchpadSensitivity(str, Enum):
    """Touchpad mode sensitivity presets."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


TOUCHPAD_SENSITIVITY_MULTIPLIERS = {
    TouchpadSensitivity.LOW.value: 0.75,
    TouchpadSensitivity.MEDIUM.value: 1.25,
    TouchpadSensitivity.HIGH.value: 2.0
}


class HandLandmarkIndex:
    """MediaPipe 21 Hand Landmark indices for reference."""
    WRIST = 0
    THUMB_CMC = 1
    THUMB_MCP = 2
    THUMB_IP = 3
    THUMB_TIP = 4
    INDEX_MCP = 5
    INDEX_PIP = 6
    INDEX_DIP = 7
    INDEX_TIP = 8
    MIDDLE_MCP = 9
    MIDDLE_PIP = 10
    MIDDLE_DIP = 11
    MIDDLE_TIP = 12
    RING_MCP = 13
    RING_PIP = 14
    RING_DIP = 15
    RING_TIP = 16
    PINKY_MCP = 17
    PINKY_PIP = 18
    PINKY_DIP = 19
    PINKY_TIP = 20


# Default initial gesture-to-action mappings
DEFAULT_GESTURE_MAPPINGS = {
    GestureType.INDEX_POINT.value: {
        "action": SafeActionType.POINTER_MOVE.value,
        "sensitivity": 1.2,
        "confidence_threshold": 0.60,
        "cooldown_ms": 20,  # Fast continuous pointer movement
        "enabled": True,
        "description": "Moves pointer / cursor on screen"
    },
    GestureType.AIR_TAP.value: {
        "action": SafeActionType.TAP.value,
        "sensitivity": 1.0,
        "confidence_threshold": 0.65,
        "cooldown_ms": 300,
        "enabled": True,
        "description": "Performs click on element under virtual pointer"
    },
    GestureType.PINCH.value: {
        "action": SafeActionType.TAP.value,
        "sensitivity": 1.0,
        "confidence_threshold": 0.65,
        "cooldown_ms": 350,
        "enabled": True,
        "description": "Performs tap / click at pointer position"
    },
    GestureType.PINCH_IN.value: {
        "action": SafeActionType.ZOOM_OUT.value,
        "sensitivity": 1.0,
        "confidence_threshold": 0.65,
        "cooldown_ms": 40,  # Continuous proportional scaling
        "enabled": True,
        "description": "Smooth continuous zoom out"
    },
    GestureType.PINCH_OUT.value: {
        "action": SafeActionType.ZOOM_IN.value,
        "sensitivity": 1.0,
        "confidence_threshold": 0.65,
        "cooldown_ms": 40,  # Continuous proportional scaling
        "enabled": True,
        "description": "Smooth continuous zoom in"
    },
    GestureType.TWO_FINGER_TOUCHPAD.value: {
        "action": SafeActionType.POINTER_MOVE.value,
        "sensitivity": 1.25,
        "confidence_threshold": 0.65,
        "cooldown_ms": 20,  # Smooth continuous touchpad cursor
        "enabled": True,
        "description": "Two-finger laptop-touchpad cursor movement"
    },
    GestureType.TWO_FINGER_SCROLL.value: {
        "action": SafeActionType.SCROLL_UP.value,
        "sensitivity": 1.0,
        "confidence_threshold": 0.65,
        "cooldown_ms": 50,  # Smooth continuous vertical scrolling
        "enabled": True,
        "description": "Two-finger touchpad vertical scrolling"
    },
    GestureType.TWO_FINGER_TAP.value: {
        "action": SafeActionType.SECONDARY_TAP.value,
        "sensitivity": 1.0,
        "confidence_threshold": 0.70,
        "cooldown_ms": 400,
        "enabled": True,
        "description": "Secondary / context menu action"
    },
    GestureType.SWIPE_UP.value: {
        "action": SafeActionType.SCROLL_UP.value,
        "sensitivity": 1.0,
        "confidence_threshold": 0.65,
        "cooldown_ms": 400,
        "enabled": True,
        "description": "Scrolls content upward"
    },
    GestureType.SWIPE_DOWN.value: {
        "action": SafeActionType.SCROLL_DOWN.value,
        "sensitivity": 1.0,
        "confidence_threshold": 0.65,
        "cooldown_ms": 400,
        "enabled": True,
        "description": "Scrolls content downward"
    },
    GestureType.SWIPE_LEFT.value: {
        "action": SafeActionType.BACK.value,
        "sensitivity": 1.0,
        "confidence_threshold": 0.65,
        "cooldown_ms": 500,
        "enabled": True,
        "description": "Performs system back navigation"
    },
    GestureType.SWIPE_RIGHT.value: {
        "action": SafeActionType.FORWARD.value,
        "sensitivity": 1.0,
        "confidence_threshold": 0.65,
        "cooldown_ms": 500,
        "enabled": True,
        "description": "Navigates forward in browser / apps (Alt + Right)"
    },
    GestureType.OPEN_PALM.value: {
        "action": SafeActionType.NONE.value,
        "sensitivity": 1.0,
        "confidence_threshold": 0.70,
        "cooldown_ms": 700,
        "enabled": True,
        "description": "Continuous open hand tracking"
    },
    GestureType.TWO_FINGERS.value: {
        "action": SafeActionType.MEDIA_PLAY_PAUSE.value,
        "sensitivity": 1.0,
        "confidence_threshold": 0.65,
        "cooldown_ms": 500,
        "enabled": True,
        "description": "Toggles media playback (Peace sign)"
    },
    GestureType.THUMBS_UP.value: {
        "action": SafeActionType.CONFIRM.value,
        "sensitivity": 1.0,
        "confidence_threshold": 0.70,
        "cooldown_ms": 600,
        "enabled": True,
        "description": "Confirm / positive action"
    },
    GestureType.THUMBS_DOWN.value: {
        "action": SafeActionType.REJECT.value,
        "sensitivity": 1.0,
        "confidence_threshold": 0.70,
        "cooldown_ms": 600,
        "enabled": True,
        "description": "Reject / cancel action"
    },
    GestureType.FIST.value: {
        "action": SafeActionType.RESET_STATE.value,
        "sensitivity": 1.0,
        "confidence_threshold": 0.80,
        "cooldown_ms": 300,
        "enabled": True,
        "description": "Instantly resets motion baselines and buffers"
    }
}
