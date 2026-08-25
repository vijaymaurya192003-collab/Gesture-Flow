"""
Android AccessibilityService Bridge
Dispatches system-wide touch gestures and global navigation actions (Back, Home, Recents, Scroll).
"""
from typing import Optional, Tuple
from android.android.jni_bridge import JNIBridge


class AndroidAccessibilityBridge:
    """
    Interfaces with the Gesture Flow Android AccessibilityService.
    Dispatches safe simulated taps, scrolls, and global system navigation events.
    """

    # Android Global Action Constants
    GLOBAL_ACTION_BACK = 1
    GLOBAL_ACTION_HOME = 2
    GLOBAL_ACTION_RECENTS = 3
    GLOBAL_ACTION_NOTIFICATIONS = 4
    GLOBAL_ACTION_QUICK_SETTINGS = 5

    _service_instance = None

    @classmethod
    def set_service_instance(cls, service_instance) -> None:
        """Called by the native Java AccessibilityService when bound."""
        cls._service_instance = service_instance

    @classmethod
    def is_service_enabled(cls) -> bool:
        """Check if AccessibilityService is active on device."""
        if not JNIBridge.is_android():
            return False
        return cls._service_instance is not None

    @classmethod
    def open_accessibility_settings(cls) -> bool:
        """Open Android Accessibility settings screen so the user can enable Gesture Flow service."""
        if not JNIBridge.is_android():
            return False

        try:
            from jnius import autoclass
            Intent = autoclass('android.content.Intent')
            Settings = autoclass('android.provider.Settings')
            context = JNIBridge.get_android_context()
            if not context:
                return False

            intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
            context.startActivity(intent)
            return True
        except Exception as e:
            print(f"[AccessibilityBridge] Error opening settings: {e}")
            return False

    @classmethod
    def perform_global_action(cls, action_id: int) -> bool:
        """
        Execute an Android Global Action via AccessibilityService.
        """
        if not cls._service_instance:
            print(f"[AccessibilityBridge] Fallback: Global action {action_id} requested (service not bound)")
            return False

        try:
            return bool(cls._service_instance.performGlobalAction(action_id))
        except Exception as e:
            print(f"[AccessibilityBridge] performGlobalAction error: {e}")
            return False

    @classmethod
    def dispatch_tap(cls, screen_x: float, screen_y: float) -> bool:
        """
        Inject a touch tap at screen coordinates using GestureDescription (Android API 24+).
        """
        if not cls._service_instance or not JNIBridge.is_android():
            return False

        try:
            from jnius import autoclass
            Path = autoclass('android.graphics.Path')
            StrokeDescription = autoclass('android.accessibilityservice.GestureDescription$StrokeDescription')
            Builder = autoclass('android.accessibilityservice.GestureDescription$Builder')

            path = Path()
            path.moveTo(float(screen_x), float(screen_y))

            # 50ms tap duration
            stroke = StrokeDescription(path, 0, 50)
            builder = Builder()
            builder.addStroke(stroke)
            gesture = builder.build()

            return bool(cls._service_instance.dispatchGesture(gesture, None, None))
        except Exception as e:
            print(f"[AccessibilityBridge] dispatch_tap error: {e}")
            return False

    @classmethod
    def dispatch_scroll(cls, start_x: float, start_y: float, end_x: float, end_y: float, duration_ms: int = 300) -> bool:
        """
        Inject a scroll gesture swipe between two coordinates.
        """
        if not cls._service_instance or not JNIBridge.is_android():
            return False

        try:
            from jnius import autoclass
            Path = autoclass('android.graphics.Path')
            StrokeDescription = autoclass('android.accessibilityservice.GestureDescription$StrokeDescription')
            Builder = autoclass('android.accessibilityservice.GestureDescription$Builder')

            path = Path()
            path.moveTo(float(start_x), float(start_y))
            path.lineTo(float(end_x), float(end_y))

            stroke = StrokeDescription(path, 0, duration_ms)
            builder = Builder()
            builder.addStroke(stroke)
            gesture = builder.build()

            return bool(cls._service_instance.dispatchGesture(gesture, None, None))
        except Exception as e:
            print(f"[AccessibilityBridge] dispatch_scroll error: {e}")
            return False

