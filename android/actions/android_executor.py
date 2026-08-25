"""
Android Action Executor
Executes safe system actions natively on Android via AccessibilityService and JNI.
"""
from typing import Optional, Tuple
from android.config.constants import SafeActionType
from android.android.jni_bridge import JNIBridge
from android.android.accessibility import AndroidAccessibilityBridge


class AndroidActionExecutor:
    """Dispatches native actions on Android OS."""

    def __init__(self, screen_w: int = 1080, screen_h: int = 2400):
        self.screen_w = screen_w
        self.screen_h = screen_h

    def execute(
        self,
        action: SafeActionType,
        pointer_coords: Optional[Tuple[float, float]] = None,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Executes safe Android system action.
        """
        if not JNIBridge.is_android():
            return False

        try:
            # Haptic vibration feedback for discrete actions
            if action != SafeActionType.POINTER_MOVE:
                JNIBridge.vibrate(35)

            if action == SafeActionType.TAP and pointer_coords:
                nx, ny = pointer_coords
                sx, sy = nx * self.screen_w, ny * self.screen_h
                return AndroidAccessibilityBridge.dispatch_tap(sx, sy)

            elif action == SafeActionType.SCROLL_UP:
                cx = self.screen_w / 2.0
                return AndroidAccessibilityBridge.dispatch_scroll(
                    start_x=cx, start_y=self.screen_h * 0.4,
                    end_x=cx, end_y=self.screen_h * 0.8,
                    duration_ms=250
                )

            elif action == SafeActionType.SCROLL_DOWN:
                cx = self.screen_w / 2.0
                return AndroidAccessibilityBridge.dispatch_scroll(
                    start_x=cx, start_y=self.screen_h * 0.8,
                    end_x=cx, end_y=self.screen_h * 0.4,
                    duration_ms=250
                )

            elif action == SafeActionType.BACK:
                return AndroidAccessibilityBridge.perform_global_action(
                    AndroidAccessibilityBridge.GLOBAL_ACTION_BACK
                )

            elif action == SafeActionType.HOME:
                return AndroidAccessibilityBridge.perform_global_action(
                    AndroidAccessibilityBridge.GLOBAL_ACTION_HOME
                )

            elif action == SafeActionType.RECENTS:
                return AndroidAccessibilityBridge.perform_global_action(
                    AndroidAccessibilityBridge.GLOBAL_ACTION_RECENTS
                )

            elif action == SafeActionType.VOLUME_UP:
                return JNIBridge.adjust_volume(+1)

            elif action == SafeActionType.VOLUME_DOWN:
                return JNIBridge.adjust_volume(-1)

            elif action == SafeActionType.POINTER_MOVE:
                # Pointer coordinates are updated for UI overlay
                return True

            return False

        except Exception as e:
            print(f"[AndroidActionExecutor] Action execution error: {e}")
            return False

