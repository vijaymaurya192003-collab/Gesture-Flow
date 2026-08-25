"""
Master Action Dispatcher
Enforces mapping rules, whitelist verification, emergency stops, pause states, and delegates execution.
"""
from typing import Dict, Optional, Tuple, Callable
from android.config.constants import GestureType, SafeActionType, DEFAULT_GESTURE_MAPPINGS
from android.actions.action_registry import ActionRegistry
from android.actions.desktop_executor import DesktopActionExecutor
from android.actions.android_executor import AndroidActionExecutor
from android.android.jni_bridge import JNIBridge
from android.models.gesture_models import GestureResult, GestureMappingItem


class ActionDispatcher:
    """
    Central dispatcher for Gesture Flow actions.
    Ensures safe, authorized, and responsive execution.
    """

    def __init__(self):
        self._mappings: Dict[str, GestureMappingItem] = {}
        self._load_default_mappings()

        # Safety & State flags
        self.emergency_stopped = False
        self.gestures_paused = False

        # Platform executors
        self._desktop_executor = DesktopActionExecutor()
        self._android_executor = AndroidActionExecutor()

        # UI listener callbacks
        self.on_action_dispatched: Optional[Callable[[str, str], None]] = None

    def _load_default_mappings(self) -> None:
        """Load default initial mappings."""
        for g_name, data in DEFAULT_GESTURE_MAPPINGS.items():
            self._mappings[g_name] = GestureMappingItem(
                gesture=g_name,
                action=data["action"],
                sensitivity=data["sensitivity"],
                confidence_threshold=data["confidence_threshold"],
                cooldown_ms=data["cooldown_ms"],
                enabled=data["enabled"],
                description=data.get("description", "")
            )

    def set_mappings(self, new_mappings: Dict[str, GestureMappingItem]) -> None:
        """Update active gesture mappings."""
        self._mappings = new_mappings

    def get_mapped_action_name(self, gesture: GestureType) -> str:
        """Get the configured safe action name for a gesture."""
        item = self._mappings.get(gesture.value)
        if item and item.enabled:
            return item.action
        return SafeActionType.NONE.value

    def get_mapping_item(self, gesture: GestureType) -> Optional[GestureMappingItem]:
        """Get the full mapping item for a gesture."""
        return self._mappings.get(gesture.value)

    def dispatch(self, result: GestureResult) -> bool:
        """
        Dispatches an action safely.
        """
        if not result or result.action == SafeActionType.NONE.value:
            return False

        action_name = result.action

        # 1. Whitelist Verification
        if not ActionRegistry.is_safe(action_name):
            print(f"[ActionDispatcher] Security Warning: Rejected unverified action '{action_name}'")
            return False

        action_enum = SafeActionType(action_name)

        # 2. Emergency Stop Handling
        if action_enum == SafeActionType.EMERGENCY_STOP:
            self.emergency_stopped = True
            print("[ActionDispatcher] !!! EMERGENCY STOP TRIGGERED - Actions Locked !!!")
            if self.on_action_dispatched:
                self.on_action_dispatched(result.gesture, "EMERGENCY_STOP")
            return True

        if self.emergency_stopped:
            # Drop all actions while emergency stop is engaged
            return False

        # 3. Pause / Resume Toggle
        if action_enum == SafeActionType.PAUSE_GESTURES:
            self.gestures_paused = not self.gestures_paused
            status = "PAUSED" if self.gestures_paused else "RESUMED"
            print(f"[ActionDispatcher] Gestures {status}")
            if self.on_action_dispatched:
                self.on_action_dispatched(result.gesture, f"GESTURES_{status}")
            return True

        if self.gestures_paused:
            return False

        # 4. Delegate to Platform Executor
        success = False
        if JNIBridge.is_android():
            success = self._android_executor.execute(
                action=action_enum,
                pointer_coords=result.pointer_coords,
                metadata=result.metadata
            )
        else:
            success = self._desktop_executor.execute(
                action=action_enum,
                pointer_coords=result.pointer_coords,
                metadata=result.metadata
            )

        if success and self.on_action_dispatched and action_enum != SafeActionType.POINTER_MOVE:
            self.on_action_dispatched(result.gesture, action_name)

        return success

    def reset_emergency_stop(self) -> None:
        """Clear emergency stop safety lock."""
        self.emergency_stopped = False
        print("[ActionDispatcher] Emergency Stop reset. Actions resumed.")

