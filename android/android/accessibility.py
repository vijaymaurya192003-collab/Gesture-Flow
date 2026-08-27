"""
Android AccessibilityService Bridge
Dispatches system-wide touch gestures and global navigation actions (Back, Home, Recents, Scroll).
Interfaces with native Java org.gestureflow.GestureAccessibilityService via PyJNIus.
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

    _mock_enabled_for_testing: bool = False
    _mock_action_log: list = []

    @classmethod
    def get_native_service(cls):
        """Retrieve active Java AccessibilityService instance via PyJNIus."""
        if not JNIBridge.is_android():
            return None

        try:
            from jnius import autoclass
            GestureAccessibilityService = autoclass('org.gestureflow.GestureAccessibilityService')
            if GestureAccessibilityService.isServiceRunning():
                return GestureAccessibilityService.getInstance()
        except Exception as e:
            print(f"[AccessibilityBridge] JNI access exception: {e}")
        return None

    @classmethod
    def is_service_enabled(cls) -> bool:
        """
        Check if AccessibilityService is actively running and bound.
        AccessibilityService CANNOT be activated silently by code; the user must explicitly
        toggle it ON in Android Settings.
        """
        if cls._mock_enabled_for_testing:
            return True

        if not JNIBridge.is_android():
            return False

        try:
            from jnius import autoclass
            GestureAccessibilityService = autoclass('org.gestureflow.GestureAccessibilityService')
            return bool(GestureAccessibilityService.isServiceRunning())
        except Exception:
            return False

    @classmethod
    def get_service_status_text(cls) -> str:
        """Human-readable status of the AccessibilityService."""
        if cls.is_service_enabled():
            return "Active & Bound"
        if JNIBridge.is_android():
            return "Disabled (Enable in Android Accessibility Settings)"
        return "Desktop Simulation Mode"

    @classmethod
    def open_accessibility_settings(cls) -> bool:
        """
        Open Android Accessibility settings screen so the user can enable Gesture Flow service.
        """
        if not JNIBridge.is_android():
            print("[AccessibilityBridge] Notice: open_accessibility_settings called on desktop.")
            return False

        try:
            from jnius import autoclass
            GestureAccessibilityService = autoclass('org.gestureflow.GestureAccessibilityService')
            context = JNIBridge.get_android_context()
            if context and hasattr(GestureAccessibilityService, 'openAccessibilitySettings'):
                return bool(GestureAccessibilityService.openAccessibilitySettings(context))

            # Fallback using Intent directly
            Intent = autoclass('android.content.Intent')
            Settings = autoclass('android.provider.Settings')
            if context:
                intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
                return True
        except Exception as e:
            print(f"[AccessibilityBridge] Error opening settings: {e}")
        return False

    @classmethod
    def perform_global_action(cls, action_id: int) -> bool:
        """
        Execute an Android Global Action (Back, Home, Recents) via AccessibilityService.
        """
        if cls._mock_enabled_for_testing:
            cls._mock_action_log.append(("GLOBAL", action_id))
            return True

        service = cls.get_native_service()
        if service is not None:
            try:
                return bool(service.performGlobalActionSafe(action_id))
            except Exception as e:
                print(f"[AccessibilityBridge] performGlobalAction error: {e}")
                return False

        print(f"[AccessibilityBridge] Global action {action_id} not executed (AccessibilityService is not enabled).")
        return False

    @classmethod
    def dispatch_tap(cls, screen_x: float, screen_y: float) -> bool:
        """
        Inject a touch tap at screen coordinates using native GestureDescription (Android API 24+).
        """
        if cls._mock_enabled_for_testing:
            cls._mock_action_log.append(("TAP", screen_x, screen_y))
            return True

        service = cls.get_native_service()
        if service is not None:
            try:
                return bool(service.dispatchTap(float(screen_x), float(screen_y)))
            except Exception as e:
                print(f"[AccessibilityBridge] dispatchTap error: {e}")
                return False

        print(f"[AccessibilityBridge] Tap at ({screen_x}, {screen_y}) suppressed (AccessibilityService is not enabled).")
        return False

    @classmethod
    def dispatch_scroll(cls, start_x: float, start_y: float, end_x: float, end_y: float, duration_ms: int = 250) -> bool:
        """
        Inject a scroll gesture swipe between two screen coordinates.
        """
        if cls._mock_enabled_for_testing:
            cls._mock_action_log.append(("SCROLL", start_x, start_y, end_x, end_y, duration_ms))
            return True

        service = cls.get_native_service()
        if service is not None:
            try:
                return bool(service.dispatchScroll(
                    float(start_x), float(start_y),
                    float(end_x), float(end_y),
                    int(duration_ms)
                ))
            except Exception as e:
                print(f"[AccessibilityBridge] dispatchScroll error: {e}")
                return False

        print(f"[AccessibilityBridge] Scroll suppressed (AccessibilityService is not enabled).")
        return False
