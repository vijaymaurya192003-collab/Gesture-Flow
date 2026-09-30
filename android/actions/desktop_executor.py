"""
Desktop Action Simulator
Executes safe simulated actions on PC (Windows/macOS/Linux) for local testing, development, and presentation.
Uses native Windows Win32 API (ctypes) for ultra-low latency hardware cursor control and PyAutoGUI fallback.
Supports two-finger touchpad cursor movement, continuous proportional zooming, and secondary context clicks.
"""
from typing import Optional, Tuple
import platform
import numpy as np
from android.config.constants import SafeActionType

try:
    import ctypes
    HAS_WINDOWS_API = platform.system() == "Windows"
except Exception:
    HAS_WINDOWS_API = False


class DesktopActionExecutor:
    """Simulates system actions on desktop operating systems with native Win32 acceleration."""

    def __init__(self):
        self._pyautogui = None
        self._screen_w = 1920
        self._screen_h = 1080
        self._has_windows_api = HAS_WINDOWS_API
        self._last_cursor_x = 960
        self._last_cursor_y = 540
        self._touchpad_sensitivity = 1.25
        self._deadzone = 0.003
        self._init_desktop_hooks()

    def _init_desktop_hooks(self) -> None:
        """Initialize desktop screen resolution and automation libraries safely."""
        if self._has_windows_api:
            try:
                # Enable Per-Monitor DPI awareness on Windows to prevent coordinate mapping and clipping bugs
                try:
                    ctypes.windll.shcore.SetProcessDpiAwareness(2)
                except Exception:
                    try:
                        ctypes.windll.user32.SetProcessDPIAware()
                    except Exception:
                        pass

                # Get true system metrics on Windows
                self._screen_w = ctypes.windll.user32.GetSystemMetrics(0)
                self._screen_h = ctypes.windll.user32.GetSystemMetrics(1)
                self._last_cursor_x = self._screen_w // 2
                self._last_cursor_y = self._screen_h // 2
                print(f"[DesktopActionExecutor] Windows Native Input Hook Active (Screen: {self._screen_w}x{self._screen_h})")
            except Exception:
                self._has_windows_api = False

        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            pyautogui.PAUSE = 0.0001
            self._pyautogui = pyautogui
            if not self._has_windows_api:
                self._screen_w, self._screen_h = pyautogui.size()
            print(f"[DesktopActionExecutor] PyAutoGUI initialized ({self._screen_w}x{self._screen_h})")
        except Exception:
            pass

    def set_touchpad_sensitivity(self, multiplier: float) -> None:
        """Configure touchpad sensitivity multiplier."""
        self._touchpad_sensitivity = max(0.5, min(3.0, multiplier))

    def execute(self, action: SafeActionType, pointer_coords: Optional[Tuple[float, float]] = None, metadata: Optional[dict] = None) -> bool:
        """
        Execute safe desktop simulated action.
        """
        try:
            # 1. POINTER MOVEMENT (Instant Native Win32 SetCursorPos / Touchpad Mode)
            if action == SafeActionType.POINTER_MOVE and pointer_coords:
                norm_x, norm_y = pointer_coords

                if metadata and metadata.get("touchpad") and "delta" in metadata:
                    # Two-Finger Laptop-Touchpad Relative Movement
                    dx, dy = metadata["delta"]
                    # Apply deadzone to filter hand tremor
                    if abs(dx) < self._deadzone:
                        dx = 0.0
                    if abs(dy) < self._deadzone:
                        dy = 0.0

                    target_x = int(self._last_cursor_x + (dx * self._screen_w * self._touchpad_sensitivity))
                    target_y = int(self._last_cursor_y + (dy * self._screen_h * self._touchpad_sensitivity))
                else:
                    # Standard Single-Finger Absolute Tracking Box with Margins
                    margin_x = 0.12
                    margin_y = 0.12
                    cx = max(0.0, min(1.0, (norm_x - margin_x) / (1.0 - 2 * margin_x)))
                    cy = max(0.0, min(1.0, (norm_y - margin_y) / (1.0 - 2 * margin_y)))
                    raw_target_x = int(cx * self._screen_w)
                    raw_target_y = int(cy * self._screen_h)

                    # Dynamic Exponential Moving Average smoothing
                    dx_curr = raw_target_x - self._last_cursor_x
                    dy_curr = raw_target_y - self._last_cursor_y
                    dist = float(np.hypot(dx_curr, dy_curr))

                    if dist < 3.0:
                        target_x = self._last_cursor_x
                        target_y = self._last_cursor_y
                    elif dist < 35.0:
                        alpha = 0.45
                        target_x = int(self._last_cursor_x + alpha * dx_curr)
                        target_y = int(self._last_cursor_y + alpha * dy_curr)
                    elif dist < 120.0:
                        alpha = 0.75
                        target_x = int(self._last_cursor_x + alpha * dx_curr)
                        target_y = int(self._last_cursor_y + alpha * dy_curr)
                    else:
                        target_x = raw_target_x
                        target_y = raw_target_y

                # Clamp to screen bounds
                target_x = max(0, min(self._screen_w - 1, target_x))
                target_y = max(0, min(self._screen_h - 1, target_y))

                self._last_cursor_x = target_x
                self._last_cursor_y = target_y

                if self._has_windows_api:
                    ctypes.windll.user32.SetCursorPos(target_x, target_y)
                    return True
                elif self._pyautogui:
                    self._pyautogui.moveTo(target_x, target_y, _pause=False)
                    return True
                return True

            # 2. CLICK / TAP
            elif action == SafeActionType.TAP:
                if pointer_coords and not (metadata and metadata.get("touchpad")):
                    norm_x, norm_y = pointer_coords
                    margin_x = 0.12
                    margin_y = 0.12
                    cx = max(0.0, min(1.0, (norm_x - margin_x) / (1.0 - 2 * margin_x)))
                    cy = max(0.0, min(1.0, (norm_y - margin_y) / (1.0 - 2 * margin_y)))
                    target_x = max(0, min(self._screen_w - 1, int(cx * self._screen_w)))
                    target_y = max(0, min(self._screen_h - 1, int(cy * self._screen_h)))
                    self._last_cursor_x = target_x
                    self._last_cursor_y = target_y
                    if self._has_windows_api:
                        ctypes.windll.user32.SetCursorPos(target_x, target_y)
                    elif self._pyautogui:
                        self._pyautogui.moveTo(target_x, target_y, _pause=False)

                if self._has_windows_api:
                    # MOUSEEVENTF_LEFTDOWN = 0x0002, MOUSEEVENTF_LEFTUP = 0x0004
                    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
                    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
                elif self._pyautogui:
                    self._pyautogui.click()
                return True

            # 3. SECONDARY TAP (Context / Right Click)
            elif action == SafeActionType.SECONDARY_TAP:
                if pointer_coords and not (metadata and metadata.get("touchpad")):
                    norm_x, norm_y = pointer_coords
                    margin_x = 0.12
                    margin_y = 0.12
                    cx = max(0.0, min(1.0, (norm_x - margin_x) / (1.0 - 2 * margin_x)))
                    cy = max(0.0, min(1.0, (norm_y - margin_y) / (1.0 - 2 * margin_y)))
                    target_x = max(0, min(self._screen_w - 1, int(cx * self._screen_w)))
                    target_y = max(0, min(self._screen_h - 1, int(cy * self._screen_h)))
                    self._last_cursor_x = target_x
                    self._last_cursor_y = target_y
                    if self._has_windows_api:
                        ctypes.windll.user32.SetCursorPos(target_x, target_y)
                    elif self._pyautogui:
                        self._pyautogui.moveTo(target_x, target_y, _pause=False)

                if self._has_windows_api:
                    # MOUSEEVENTF_RIGHTDOWN = 0x0008, MOUSEEVENTF_RIGHTUP = 0x0010
                    ctypes.windll.user32.mouse_event(0x0008, 0, 0, 0, 0)
                    ctypes.windll.user32.mouse_event(0x0010, 0, 0, 0, 0)
                elif self._pyautogui:
                    self._pyautogui.rightClick()
                return True

            # 4. SCROLL UP / DOWN (Touchpad Continuous or Discrete Swipe)
            elif action in (SafeActionType.SCROLL_UP, SafeActionType.SCROLL_DOWN):
                delta = 120 if action == SafeActionType.SCROLL_UP else -120
                if metadata and "scroll_delta" in metadata:
                    # Scale delta proportionally to two-finger velocity
                    scale_mult = min(3.0, max(0.5, abs(metadata["scroll_delta"]) * 50.0))
                    delta = int(delta * scale_mult)

                if self._has_windows_api:
                    # MOUSEEVENTF_WHEEL = 0x0800
                    ctypes.windll.user32.mouse_event(0x0800, 0, 0, delta, 0)
                elif self._pyautogui:
                    self._pyautogui.scroll(delta)
                return True

            # 5. CONTINUOUS PROPORTIONAL ZOOM (PINCH_IN / PINCH_OUT)
            elif action in (SafeActionType.ZOOM_IN, SafeActionType.ZOOM_OUT):
                wheel_delta = 120 if action == SafeActionType.ZOOM_IN else -120
                if self._has_windows_api:
                    # Simulate Ctrl + Mouse Wheel for proportional zoom with guaranteed release
                    VK_CONTROL = 0x11
                    try:
                        ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
                        ctypes.windll.user32.mouse_event(0x0800, 0, 0, wheel_delta, 0)
                    finally:
                        ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 2, 0)
                elif self._pyautogui:
                    try:
                        self._pyautogui.keyDown('ctrl')
                        self._pyautogui.scroll(wheel_delta)
                    finally:
                        self._pyautogui.keyUp('ctrl')
                return True

            # 6. CONFIRM (Enter Key) / REJECT (Escape Key)
            elif action == SafeActionType.CONFIRM:
                if self._pyautogui:
                    self._pyautogui.press('enter')
                return True

            elif action == SafeActionType.REJECT:
                if self._pyautogui:
                    self._pyautogui.press('esc')
                return True

            # 7. BACK (Alt + Left) / FORWARD (Alt + Right) / HOME (Win + D) / RECENTS (Alt + Tab)
            elif action == SafeActionType.BACK:
                if self._has_windows_api:
                    VK_MENU = 0x12
                    VK_LEFT = 0x25
                    ctypes.windll.user32.keybd_event(VK_MENU, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(VK_LEFT, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(VK_LEFT, 0, 2, 0)
                    ctypes.windll.user32.keybd_event(VK_MENU, 0, 2, 0)
                elif self._pyautogui:
                    self._pyautogui.hotkey('alt', 'left')
                return True

            elif action == SafeActionType.FORWARD:
                if self._has_windows_api:
                    VK_MENU = 0x12
                    VK_RIGHT = 0x27
                    ctypes.windll.user32.keybd_event(VK_MENU, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(VK_RIGHT, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(VK_RIGHT, 0, 2, 0)
                    ctypes.windll.user32.keybd_event(VK_MENU, 0, 2, 0)
                elif self._pyautogui:
                    self._pyautogui.hotkey('alt', 'right')
                return True

            elif action == SafeActionType.RESET_STATE:
                self._last_cursor_x = self._screen_w // 2
                self._last_cursor_y = self._screen_h // 2
                return True

            elif action == SafeActionType.HOME:
                if self._pyautogui:
                    self._pyautogui.hotkey('win', 'd')
                return True

            elif action == SafeActionType.RECENTS:
                if self._pyautogui:
                    self._pyautogui.hotkey('alt', 'tab')
                return True

            # 8. VOLUME UP / DOWN / MEDIA
            elif action == SafeActionType.VOLUME_UP:
                if self._pyautogui:
                    self._pyautogui.press('volumeup')
                return True

            elif action == SafeActionType.VOLUME_DOWN:
                if self._pyautogui:
                    self._pyautogui.press('volumedown')
                return True

            elif action == SafeActionType.MEDIA_PLAY_PAUSE:
                if self._pyautogui:
                    self._pyautogui.press('playpause')
                return True

            return False

        except Exception as e:
            print(f"[DesktopActionExecutor] Execution error: {e}")
            return False
