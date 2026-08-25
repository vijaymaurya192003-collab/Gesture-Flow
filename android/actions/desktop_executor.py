"""
Desktop Action Simulator
Executes safe simulated actions on PC (Windows/macOS/Linux) for local testing, development, and presentation.
Uses native Windows Win32 API (ctypes) for ultra-low latency hardware cursor control and PyAutoGUI fallback.
"""
from typing import Optional, Tuple
import platform
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
        self._init_desktop_hooks()

    def _init_desktop_hooks(self) -> None:
        """Initialize desktop screen resolution and automation libraries safely."""
        if self._has_windows_api:
            try:
                # Get true system metrics on Windows
                self._screen_w = ctypes.windll.user32.GetSystemMetrics(0)
                self._screen_h = ctypes.windll.user32.GetSystemMetrics(1)
                print(f"[DesktopActionExecutor] Windows Native Input Hook Active (Screen: {self._screen_w}x{self._screen_h})")
            except Exception as e:
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

    def execute(self, action: SafeActionType, pointer_coords: Optional[Tuple[float, float]] = None, metadata: Optional[dict] = None) -> bool:
        """
        Execute safe desktop simulated action.
        """
        try:
            # 1. POINTER MOVEMENT (Instant Native Win32 SetCursorPos)
            if action == SafeActionType.POINTER_MOVE and pointer_coords:
                norm_x, norm_y = pointer_coords

                # Active Tracking Box Scaling: map [0.12, 0.88] to [0.0, 1.0] for effortless reach
                margin = 0.12
                cx = max(0.0, min(1.0, (norm_x - margin) / (1.0 - 2 * margin)))
                cy = max(0.0, min(1.0, (norm_y - margin) / (1.0 - 2 * margin)))

                target_x = int(cx * self._screen_w)
                target_y = int(cy * self._screen_h)

                if self._has_windows_api:
                    ctypes.windll.user32.SetCursorPos(target_x, target_y)
                    return True
                elif self._pyautogui:
                    self._pyautogui.moveTo(target_x, target_y, _pause=False)
                    return True
                return True

            # 2. CLICK / TAP
            elif action == SafeActionType.TAP:
                if self._has_windows_api:
                    # MOUSEEVENTF_LEFTDOWN = 0x0002, MOUSEEVENTF_LEFTUP = 0x0004
                    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
                    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
                elif self._pyautogui:
                    self._pyautogui.click()
                print("[DesktopAction] Simulated Click / Tap")
                return True

            # 3. SCROLL UP
            elif action == SafeActionType.SCROLL_UP:
                if self._has_windows_api:
                    # MOUSEEVENTF_WHEEL = 0x0800, wheel delta = 120
                    ctypes.windll.user32.mouse_event(0x0800, 0, 0, 240, 0)
                elif self._pyautogui:
                    self._pyautogui.scroll(300)
                print("[DesktopAction] Simulated Scroll Up")
                return True

            # 4. SCROLL DOWN
            elif action == SafeActionType.SCROLL_DOWN:
                if self._has_windows_api:
                    ctypes.windll.user32.mouse_event(0x0800, 0, 0, -240, 0)
                elif self._pyautogui:
                    self._pyautogui.scroll(-300)
                print("[DesktopAction] Simulated Scroll Down")
                return True

            # 5. BACK (Alt + Left)
            elif action == SafeActionType.BACK:
                if self._pyautogui:
                    self._pyautogui.hotkey('alt', 'left')
                print("[DesktopAction] Simulated Back (Alt+Left)")
                return True

            # 6. HOME (Win + D)
            elif action == SafeActionType.HOME:
                if self._pyautogui:
                    self._pyautogui.hotkey('win', 'd')
                print("[DesktopAction] Simulated Home (Show Desktop)")
                return True

            # 7. RECENTS (Alt + Tab)
            elif action == SafeActionType.RECENTS:
                if self._pyautogui:
                    self._pyautogui.hotkey('alt', 'tab')
                print("[DesktopAction] Simulated Recents (Alt+Tab)")
                return True

            # 8. VOLUME UP / DOWN / MEDIA
            elif action == SafeActionType.VOLUME_UP:
                if self._pyautogui:
                    self._pyautogui.press('volumeup')
                print("[DesktopAction] Simulated Volume Up")
                return True

            elif action == SafeActionType.VOLUME_DOWN:
                if self._pyautogui:
                    self._pyautogui.press('volumedown')
                print("[DesktopAction] Simulated Volume Down")
                return True

            elif action == SafeActionType.MEDIA_PLAY_PAUSE:
                if self._pyautogui:
                    self._pyautogui.press('playpause')
                print("[DesktopAction] Simulated Play/Pause")
                return True

            return False

        except Exception as e:
            print(f"[DesktopActionExecutor] Execution error: {e}")
            return False
