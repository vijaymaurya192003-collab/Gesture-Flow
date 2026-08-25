"""
Constants and Enums for Gesture Flow
Defines all supported gesture types, safe action types, and landmark mappings.
"""
from enum import Enum


class GestureType(str, Enum):
    """Supported gesture classifications in Gesture Flow."""
    NONE = "NONE"
    INDEX_POINT = "INDEX_POINT"
    PINCH = "PINCH"
    SWIPE_UP = "SWIPE_UP"
    SWIPE_DOWN = "SWIPE_DOWN"
    SWIPE_LEFT = "SWIPE_LEFT"
    SWIPE_RIGHT = "SWIPE_RIGHT"
    OPEN_PALM = "OPEN_PALM"
    TWO_FINGERS = "TWO_FINGERS"
    FIST = "FIST"


class SafeActionType(str, Enum):
    """
    Explicit whitelist of safe actions.
    No arbitrary shell commands are permitted.
    """
    NONE = "NONE"
    POINTER_MOVE = "POINTER_MOVE"
    TAP = "TAP"
    SCROLL_UP = "SCROLL_UP"
    SCROLL_DOWN = "SCROLL_DOWN"
    BACK = "BACK"
    HOME = "HOME"
    RECENTS = "RECENTS"
    VOLUME_UP = "VOLUME_UP"
    VOLUME_DOWN = "VOLUME_DOWN"
    MEDIA_PLAY_PAUSE = "MEDIA_PLAY_PAUSE"
    PAUSE_GESTURES = "PAUSE_GESTURES"
    EMERGENCY_STOP = "EMERGENCY_STOP"


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
        "confidence_threshold": 0.70,
        "cooldown_ms": 30,  # fast continuous movement
        "enabled": True,
        "description": "Moves pointer / cursor on screen"
    },
    GestureType.PINCH.value: {
        "action": SafeActionType.TAP.value,
        "sensitivity": 1.0,
        "confidence_threshold": 0.75,
        "cooldown_ms": 400,
        "enabled": True,
        "description": "Performs tap / click at pointer position"
    },
    GestureType.SWIPE_UP.value: {
        "action": SafeActionType.SCROLL_UP.value,
        "sensitivity": 1.0,
        "confidence_threshold": 0.70,
        "cooldown_ms": 500,
        "enabled": True,
        "description": "Scrolls content upward"
    },
    GestureType.SWIPE_DOWN.value: {
        "action": SafeActionType.SCROLL_DOWN.value,
        "sensitivity": 1.0,
        "confidence_threshold": 0.70,
        "cooldown_ms": 500,
        "enabled": True,
        "description": "Scrolls content downward"
    },
    GestureType.SWIPE_LEFT.value: {
        "action": SafeActionType.BACK.value,
        "sensitivity": 1.0,
        "confidence_threshold": 0.75,
        "cooldown_ms": 600,
        "enabled": True,
        "description": "Performs system back navigation"
    },
    GestureType.SWIPE_RIGHT.value: {
        "action": SafeActionType.HOME.value,
        "sensitivity": 1.0,
        "confidence_threshold": 0.75,
        "cooldown_ms": 600,
        "enabled": True,
        "description": "Navigates to home screen"
    },
    GestureType.OPEN_PALM.value: {
        "action": SafeActionType.PAUSE_GESTURES.value,
        "sensitivity": 1.0,
        "confidence_threshold": 0.80,
        "cooldown_ms": 800,
        "enabled": True,
        "description": "Pauses / Resumes gesture tracking"
    },
    GestureType.TWO_FINGERS.value: {
        "action": SafeActionType.MEDIA_PLAY_PAUSE.value,
        "sensitivity": 1.0,
        "confidence_threshold": 0.75,
        "cooldown_ms": 600,
        "enabled": True,
        "description": "Toggles media playback"
    },
    GestureType.FIST.value: {
        "action": SafeActionType.EMERGENCY_STOP.value,
        "sensitivity": 1.0,
        "confidence_threshold": 0.85,
        "cooldown_ms": 1000,
        "enabled": True,
        "description": "Immediate emergency safety lockout"
    }
}

