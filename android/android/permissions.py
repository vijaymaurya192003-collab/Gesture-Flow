"""
Android Runtime Permissions Helper
Handles requesting and checking necessary Android runtime permissions.
"""
from typing import List, Callable, Optional
from android.android.jni_bridge import JNIBridge


class AndroidPermissionsHelper:
    """Helper to request Android runtime permissions gracefully."""

    @classmethod
    def request_camera_permission(cls, callback: Optional[Callable[[bool], None]] = None) -> None:
        """Request CAMERA permission at runtime."""
        if not JNIBridge.is_android():
            if callback:
                callback(True)
            return

        try:
            from android.permissions import request_permissions, Permission, check_permission
            
            def _perm_callback(permissions, grant_results):
                granted = all(grant_results)
                print(f"[AndroidPermissions] Camera permission result: {granted}")
                if callback:
                    callback(granted)

            if check_permission(Permission.CAMERA):
                if callback:
                    callback(True)
            else:
                request_permissions([Permission.CAMERA, Permission.VIBRATE], _perm_callback)

        except Exception as e:
            print(f"[AndroidPermissions] Permission request error: {e}")
            if callback:
                callback(False)

