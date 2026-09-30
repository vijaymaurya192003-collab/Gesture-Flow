"""
Gesture Control Pipeline
========================
Modular OpenCV & MediaPipe touchless PC control pipeline.

Controls & Mappings:
1. Cursor Movement: Driven continuously by the position of the Index Finger tip (Landmark 8).
2. Click / Enter Action: Pinching or closing the index finger toward the thumb (or a clear,
   deliberate index tap) triggers a mouse click / Enter action immediately.
3. Navigation (Swipes):
   - Left Slide (Swipe Left): Trigger Back navigation (Alt + Left / Browser Back).
   - Right Slide (Swipe Right): Trigger Forward navigation (Alt + Right / Browser Forward).
4. Scrolling (Two Fingers):
   - Two Fingers Up (Index + Middle extended together, moving up): Scroll Up.
   - Two Fingers Down (Index + Middle extended together, moving down): Scroll Down.
5. State Management & Resets:
   - NO PAUSE SYSTEM: Gesture tracking remains active continuously (no pause/freeze states).
   - Fist / Closed Palm Reset: Closing the hand into a fist or closed palm instantly resets
     all motion tracking baselines, smoothing buffers, gesture states, and swipe trajectories.
"""

from dataclasses import dataclass, field
from enum import Enum
import math
import platform
import time
from typing import Deque, List, Optional, Tuple
from collections import deque

import cv2
import numpy as np

# Windows native acceleration (optional, fallback to pyautogui)
try:
    import ctypes
    HAS_WIN32 = platform.system() == "Windows"
    if HAS_WIN32:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor DPI aware
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
except Exception:
    HAS_WIN32 = False

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.0001
    HAS_PYAUTOGUI = True
except Exception:
    HAS_PYAUTOGUI = False


# =============================================================================
# 1. ENUMS & DATA STRUCTURES
# =============================================================================

class Gesture(str, Enum):
    NONE = "NONE"
    CURSOR_MOVE = "CURSOR_MOVE"
    CLICK = "CLICK"
    SCROLL_UP = "SCROLL_UP"
    SCROLL_DOWN = "SCROLL_DOWN"
    SWIPE_LEFT = "SWIPE_LEFT"      # Back
    SWIPE_RIGHT = "SWIPE_RIGHT"    # Forward
    RESET = "RESET"                # Fist / Closed palm


@dataclass
class Point3D:
    x: float
    y: float
    z: float = 0.0


@dataclass
class ExtractedFeatures:
    """Geometric metrics extracted from hand landmarks."""
    landmarks: List[Point3D]
    hand_scale: float
    index_tip: Point3D
    thumb_tip: Point3D
    middle_tip: Point3D
    pinch_dist_norm: float
    index_extended: bool
    middle_extended: bool
    ring_extended: bool
    pinky_extended: bool
    thumb_extended: bool
    extended_count: int
    is_fist_or_closed_palm: bool
    is_two_finger_mode: bool
    two_finger_center: Tuple[float, float]
    velocity_xy: Tuple[float, float]


# =============================================================================
# 2. LANDMARK EXTRACTION & GEOMETRIC FEATURE ANALYSIS
# =============================================================================

class LandmarkExtractor:
    """Extracts 21 3D hand landmarks and geometric features from camera frames."""

    INDEX_TIP = 8
    INDEX_PIP = 6
    INDEX_MCP = 5

    THUMB_TIP = 4
    THUMB_IP = 3
    THUMB_MCP = 2

    MIDDLE_TIP = 12
    MIDDLE_PIP = 10
    MIDDLE_MCP = 9

    RING_TIP = 16
    RING_PIP = 14
    RING_MCP = 13

    PINKY_TIP = 20
    PINKY_PIP = 18
    PINKY_MCP = 17

    WRIST = 0

    @staticmethod
    def _dist_2d(p1: Point3D, p2: Point3D) -> float:
        return float(math.hypot(p1.x - p2.x, p1.y - p2.y))

    @staticmethod
    def _dist_3d(p1: Point3D, p2: Point3D) -> float:
        return float(math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2))

    @staticmethod
    def _joint_angle(p_mcp: Point3D, p_pip: Point3D, p_tip: Point3D) -> float:
        """Computes the 3D angle (in degrees) at the PIP joint."""
        v1 = np.array([p_mcp.x - p_pip.x, p_mcp.y - p_pip.y, p_mcp.z - p_pip.z], dtype=float)
        v2 = np.array([p_tip.x - p_pip.x, p_tip.y - p_pip.y, p_tip.z - p_pip.z], dtype=float)
        n1 = float(np.linalg.norm(v1))
        n2 = float(np.linalg.norm(v2))
        if n1 < 1e-6 or n2 < 1e-6:
            return 0.0
        cos_theta = float(np.dot(v1, v2) / (n1 * n2))
        cos_theta = max(-1.0, min(1.0, cos_theta))
        return float(np.degrees(np.arccos(cos_theta)))

    @classmethod
    def _is_finger_straight(
        cls,
        wrist: Point3D,
        mcp: Point3D,
        pip: Point3D,
        tip: Point3D,
        dist_ratio: float = 1.10,
        min_angle: float = 140.0
    ) -> bool:
        """Determines finger extension by joint straightness and wrist-to-tip distance."""
        d_wrist_pip = cls._dist_2d(wrist, pip)
        d_wrist_tip = cls._dist_2d(wrist, tip)
        if d_wrist_pip < 1e-5:
            return False
        dist_ok = (d_wrist_tip / d_wrist_pip) > dist_ratio
        angle = cls._joint_angle(mcp, pip, tip)
        angle_ok = angle >= min_angle
        return bool(dist_ok and angle_ok)

    def extract(
        self,
        raw_landmarks: List[any],
        prev_palm_positions: Optional[List[Tuple[float, float]]] = None
    ) -> Optional[ExtractedFeatures]:
        """
        Parses raw MediaPipe landmarks into an ExtractedFeatures object.
        Compatible with both MediaPipe landmark objects and (x, y, z) tuples.
        """
        if not raw_landmarks or len(raw_landmarks) < 21:
            return None

        # Standardize coordinates into Point3D
        points: List[Point3D] = []
        for lm in raw_landmarks:
            if hasattr(lm, "x") and hasattr(lm, "y"):
                z = getattr(lm, "z", 0.0)
                points.append(Point3D(float(lm.x), float(lm.y), float(z)))
            elif isinstance(lm, (list, tuple)) and len(lm) >= 2:
                z = float(lm[2]) if len(lm) > 2 else 0.0
                points.append(Point3D(float(lm[0]), float(lm[1]), z))
            else:
                return None

        wrist = points[self.WRIST]
        middle_mcp = points[self.MIDDLE_MCP]

        # Hand scale reference (wrist to middle MCP)
        hand_scale = max(0.04, self._dist_2d(wrist, middle_mcp))

        # Finger extensions
        index_ext = self._is_finger_straight(
            wrist, points[self.INDEX_MCP], points[self.INDEX_PIP], points[self.INDEX_TIP], 1.10, 140.0
        )
        middle_ext = self._is_finger_straight(
            wrist, points[self.MIDDLE_MCP], points[self.MIDDLE_PIP], points[self.MIDDLE_TIP], 1.12, 142.0
        )
        ring_ext = self._is_finger_straight(
            wrist, points[self.RING_MCP], points[self.RING_PIP], points[self.RING_TIP], 1.12, 142.0
        )
        pinky_ext = self._is_finger_straight(
            wrist, points[self.PINKY_MCP], points[self.PINKY_PIP], points[self.PINKY_TIP], 1.10, 138.0
        )

        # Thumb extension: tip distance to pinky base & joint angle
        thumb_tip = points[self.THUMB_TIP]
        thumb_ip = points[self.THUMB_IP]
        thumb_mcp = points[self.THUMB_MCP]
        pinky_mcp = points[self.PINKY_MCP]
        thumb_dist_ok = self._dist_2d(pinky_mcp, thumb_tip) > (self._dist_2d(pinky_mcp, thumb_ip) * 1.15)
        thumb_angle = self._joint_angle(thumb_mcp, thumb_ip, thumb_tip)
        thumb_ext = bool(thumb_dist_ok and thumb_angle > 125.0)

        extended_count = sum([index_ext, middle_ext, ring_ext, pinky_ext, thumb_ext])

        # Fist or closed palm detection (all four main fingers curled)
        all_four_curled = (not index_ext and not middle_ext and not ring_ext and not pinky_ext)
        is_fist_or_closed_palm = all_four_curled or (extended_count == 0)

        # Normalized pinch distance (Thumb tip to Index tip / hand_scale)
        index_tip = points[self.INDEX_TIP]
        raw_pinch_dist = self._dist_3d(thumb_tip, index_tip)
        pinch_dist_norm = raw_pinch_dist / hand_scale

        # Two-finger mode: Index & Middle extended, Ring & Pinky curled
        is_two_finger_mode = False
        two_finger_center = (index_tip.x, index_tip.y)
        if index_ext and middle_ext and not ring_ext and not pinky_ext:
            middle_tip = points[self.MIDDLE_TIP]
            sep_norm = self._dist_2d(index_tip, middle_tip) / hand_scale
            # Held close together (not wide peace sign)
            if sep_norm < 0.48:
                is_two_finger_mode = True
                two_finger_center = (
                    float((index_tip.x + middle_tip.x) / 2.0),
                    float((index_tip.y + middle_tip.y) / 2.0)
                )

        # Palm center & velocity calculation
        palm_x = (wrist.x + points[self.INDEX_MCP].x + middle_mcp.x + pinky_mcp.x) / 4.0
        palm_y = (wrist.y + points[self.INDEX_MCP].y + middle_mcp.y + pinky_mcp.y) / 4.0
        vx, vy = 0.0, 0.0
        if prev_palm_positions and len(prev_palm_positions) >= 1:
            oldest = prev_palm_positions[0]
            n = len(prev_palm_positions)
            vx = (palm_x - oldest[0]) / max(1, n)
            vy = (palm_y - oldest[1]) / max(1, n)

        return ExtractedFeatures(
            landmarks=points,
            hand_scale=hand_scale,
            index_tip=index_tip,
            thumb_tip=thumb_tip,
            middle_tip=points[self.MIDDLE_TIP],
            pinch_dist_norm=pinch_dist_norm,
            index_extended=index_ext,
            middle_extended=middle_ext,
            ring_extended=ring_ext,
            pinky_extended=pinky_ext,
            thumb_extended=thumb_ext,
            extended_count=extended_count,
            is_fist_or_closed_palm=is_fist_or_closed_palm,
            is_two_finger_mode=is_two_finger_mode,
            two_finger_center=two_finger_center,
            velocity_xy=(float(vx), float(vy))
        )


# =============================================================================
# 3. COORDINATE TRANSFORMATION & SCREEN BOUNDARY MAPPING
# =============================================================================

class CoordinateTransformer:
    """
    Maps normalized webcam coordinates [0.0, 1.0] to physical screen pixel coordinates [0, screen_w].
    Applies calibrated boundary margins so the cursor can effortlessly reach all four screen corners.
    """

    def __init__(self, margin_x: float = 0.15, margin_y: float = 0.15):
        self.margin_x = margin_x
        self.margin_y = margin_y
        self.screen_w, self.screen_h = self._get_screen_dimensions()

    def _get_screen_dimensions(self) -> Tuple[int, int]:
        """Detects true physical screen resolution with DPI awareness."""
        if HAS_WIN32:
            try:
                w = int(ctypes.windll.user32.GetSystemMetrics(0))
                h = int(ctypes.windll.user32.GetSystemMetrics(1))
                if w > 0 and h > 0:
                    return w, h
            except Exception:
                pass

        if HAS_PYAUTOGUI:
            try:
                w, h = pyautogui.size()
                return int(w), int(h)
            except Exception:
                pass

        return 1920, 1080

    def transform(self, norm_x: float, norm_y: float) -> Tuple[int, int]:
        """
        Linearly projects normalized coordinates onto the screen surface with margin compensation.
        Clamps coordinates to guarantee cursor stays within [0, screen_w - 1] and [0, screen_h - 1].
        """
        # Active normalized tracking box [margin, 1.0 - margin]
        denom_x = max(0.01, 1.0 - 2.0 * self.margin_x)
        denom_y = max(0.01, 1.0 - 2.0 * self.margin_y)

        scaled_x = (norm_x - self.margin_x) / denom_x
        scaled_y = (norm_y - self.margin_y) / denom_y

        clamped_x = max(0.0, min(1.0, scaled_x))
        clamped_y = max(0.0, min(1.0, scaled_y))

        pixel_x = int(round(clamped_x * (self.screen_w - 1)))
        pixel_y = int(round(clamped_y * (self.screen_h - 1)))

        return pixel_x, pixel_y


# =============================================================================
# 4. ADAPTIVE CURSOR SMOOTHING (EXPONENTIAL MOVING AVERAGE)
# =============================================================================

class CursorSmoother:
    """
    Adaptive Exponential Moving Average (EMA) cursor smoother.
    - Suppresses micro-jitter and tremor via a deadband.
    - Smooths moderate movement for precise clicking.
    - Bypasses lag during rapid movements for high responsiveness.
    """

    def __init__(
        self,
        deadband_px: float = 3.0,
        slow_threshold_px: float = 40.0,
        fast_threshold_px: float = 120.0,
        alpha_slow: float = 0.45,
        alpha_fast: float = 0.80
    ):
        self.deadband_px = deadband_px
        self.slow_threshold_px = slow_threshold_px
        self.fast_threshold_px = fast_threshold_px
        self.alpha_slow = alpha_slow
        self.alpha_fast = alpha_fast

        self.last_x: Optional[float] = None
        self.last_y: Optional[float] = None

    def smooth(self, target_x: int, target_y: int) -> Tuple[int, int]:
        """Filters target pixel coordinates to remove hand jitter."""
        if self.last_x is None or self.last_y is None:
            self.last_x = float(target_x)
            self.last_y = float(target_y)
            return target_x, target_y

        dx = target_x - self.last_x
        dy = target_y - self.last_y
        dist = math.hypot(dx, dy)

        # 1. Micro-jitter deadband: lock position if hand is steady
        if dist < self.deadband_px:
            return int(round(self.last_x)), int(round(self.last_y))

        # 2. Adaptive alpha based on speed
        if dist < self.slow_threshold_px:
            alpha = self.alpha_slow
        elif dist < self.fast_threshold_px:
            alpha = self.alpha_fast
        else:
            alpha = 1.0  # Instant jump for fast motion, zero lag

        smoothed_x = self.last_x + alpha * dx
        smoothed_y = self.last_y + alpha * dy

        self.last_x = smoothed_x
        self.last_y = smoothed_y

        return int(round(smoothed_x)), int(round(smoothed_y))

    def reset(self) -> None:
        """Clear filter baseline on hand loss or reset."""
        self.last_x = None
        self.last_y = None


# =============================================================================
# 5. OS & HARDWARE ACTION EXECUTOR
# =============================================================================

class ActionExecutor:
    """Executes mouse cursor, click, scroll, and browser navigation commands."""

    def __init__(self):
        self.has_win32 = HAS_WIN32
        self.has_pyautogui = HAS_PYAUTOGUI

    def move_cursor(self, screen_x: int, screen_y: int) -> None:
        """Instant cursor movement."""
        if self.has_win32:
            ctypes.windll.user32.SetCursorPos(screen_x, screen_y)
        elif self.has_pyautogui:
            pyautogui.moveTo(screen_x, screen_y, _pause=False)

    def click(self, screen_x: Optional[int] = None, screen_y: Optional[int] = None) -> None:
        """Dispatches an immediate mouse click / Enter action."""
        if screen_x is not None and screen_y is not None:
            self.move_cursor(screen_x, screen_y)

        if self.has_win32:
            # MOUSEEVENTF_LEFTDOWN = 0x0002, MOUSEEVENTF_LEFTUP = 0x0004
            ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
            ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
        elif self.has_pyautogui:
            pyautogui.click()

    def scroll(self, steps: int) -> None:
        """
        Scroll wheel movement.
        Positive steps = Scroll Up, Negative steps = Scroll Down.
        """
        if self.has_win32:
            # MOUSEEVENTF_WHEEL = 0x0800, wheel delta typically 120 per notch
            wheel_delta = steps * 120
            ctypes.windll.user32.mouse_event(0x0800, 0, 0, wheel_delta, 0)
        elif self.has_pyautogui:
            pyautogui.scroll(steps * 100)

    def navigate_back(self) -> None:
        """Triggers browser / system Back action (Alt + Left)."""
        if self.has_win32:
            VK_MENU = 0x12  # Alt
            VK_LEFT = 0x25
            ctypes.windll.user32.keybd_event(VK_MENU, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_LEFT, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_LEFT, 0, 2, 0)
            ctypes.windll.user32.keybd_event(VK_MENU, 0, 2, 0)
        elif self.has_pyautogui:
            pyautogui.hotkey("alt", "left")

    def navigate_forward(self) -> None:
        """Triggers browser / system Forward action (Alt + Right)."""
        if self.has_win32:
            VK_MENU = 0x12  # Alt
            VK_RIGHT = 0x27
            ctypes.windll.user32.keybd_event(VK_MENU, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_RIGHT, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_RIGHT, 0, 2, 0)
            ctypes.windll.user32.keybd_event(VK_MENU, 0, 2, 0)
        elif self.has_pyautogui:
            pyautogui.hotkey("alt", "right")


# =============================================================================
# 6. GESTURE RECOGNIZER & TEMPORAL DEBOUNCE ENGINE
# =============================================================================

class GestureRecognizer:
    """
    Classifies gestures and handles temporal debounce logic.
    Mappings:
      - Fist / Closed Palm: Instant RESET of all tracking & buffers.
      - Pinch / Air Tap: Immediate Click / Enter action.
      - Two-Finger Up / Down: Continuous Scroll Up / Down.
      - Swipe Left: Back navigation (Alt + Left).
      - Swipe Right: Forward navigation (Alt + Right).
      - Index Finger Extended: Cursor movement driven by Landmark 8.
    """

    def __init__(
        self,
        pinch_threshold: float = 0.38,
        swipe_velocity_threshold: float = 0.045,
        scroll_threshold: float = 0.015,
        click_cooldown_frames: int = 10,
        swipe_cooldown_frames: int = 16
    ):
        self.pinch_threshold = pinch_threshold
        self.swipe_velocity_threshold = swipe_velocity_threshold
        self.scroll_threshold = scroll_threshold

        self.click_cooldown_frames = click_cooldown_frames
        self.swipe_cooldown_frames = swipe_cooldown_frames

        # Debounce and state tracking
        self.click_cooldown_counter: int = 0
        self.swipe_cooldown_counter: int = 0
        self.pinch_is_engaged: bool = False

        self.prev_two_finger_y: Optional[float] = None
        self.prev_index_z: Optional[float] = None
        self.palm_history: Deque[Tuple[float, float]] = deque(maxlen=6)

    def reset_state(self) -> None:
        """
        Instant reset of motion baselines, trajectory buffers, and gesture states.
        Triggered when a fist or closed palm is detected.
        """
        self.click_cooldown_counter = 0
        self.swipe_cooldown_counter = 0
        self.pinch_is_engaged = False
        self.prev_two_finger_y = None
        self.prev_index_z = None
        self.palm_history.clear()

    def process_frame(self, features: ExtractedFeatures) -> Tuple[Gesture, Optional[int]]:
        """
        Processes extracted features for a frame.
        Returns (Gesture, scroll_step_or_none).
        """
        # Decrement cooldown counters
        if self.click_cooldown_counter > 0:
            self.click_cooldown_counter -= 1
        if self.swipe_cooldown_counter > 0:
            self.swipe_cooldown_counter -= 1

        # ---------------------------------------------------------------------
        # 1. PRIORITY 1: FIST / CLOSED PALM RESET
        # ---------------------------------------------------------------------
        if features.is_fist_or_closed_palm:
            self.reset_state()
            return Gesture.RESET, None

        # ---------------------------------------------------------------------
        # 2. PRIORITY 2: PINCH / CLICK (Index towards thumb or forward tap)
        # ---------------------------------------------------------------------
        is_pinching = features.pinch_dist_norm < self.pinch_threshold
        # Check forward z-axis pulse (air tap) if index tip moved sharply towards camera
        z_tap = False
        if self.prev_index_z is not None and features.index_extended and not features.middle_extended:
            z_velocity = features.index_tip.z - self.prev_index_z
            if z_velocity < -0.040:
                z_tap = True
        self.prev_index_z = features.index_tip.z

        if is_pinching or z_tap:
            # Trigger click immediately on first frame of pinch/tap engagement
            if not self.pinch_is_engaged and self.click_cooldown_counter == 0:
                self.pinch_is_engaged = True
                self.click_cooldown_counter = self.click_cooldown_frames
                return Gesture.CLICK, None
            elif is_pinching:
                # Still holding pinch, maintain engagement without re-triggering click
                return Gesture.NONE, None
        else:
            # Pinch released, ready for next click
            self.pinch_is_engaged = False

        # ---------------------------------------------------------------------
        # 3. PRIORITY 3: TWO-FINGER SCROLLING (Index + Middle extended together)
        # ---------------------------------------------------------------------
        if features.is_two_finger_mode:
            current_y = features.two_finger_center[1]
            scroll_dir: Optional[Gesture] = None
            steps = 0

            if self.prev_two_finger_y is not None:
                dy = current_y - self.prev_two_finger_y
                if abs(dy) > self.scroll_threshold:
                    # In screen coordinates, moving up means smaller y -> dy < 0
                    if dy < 0:
                        scroll_dir = Gesture.SCROLL_UP
                        steps = 1
                    else:
                        scroll_dir = Gesture.SCROLL_DOWN
                        steps = -1

            self.prev_two_finger_y = current_y
            if scroll_dir:
                return scroll_dir, steps
            return Gesture.NONE, None
        else:
            self.prev_two_finger_y = None

        # ---------------------------------------------------------------------
        # 4. PRIORITY 4: NAVIGATION SWIPES (Swipe Left / Swipe Right)
        # ---------------------------------------------------------------------
        vx, vy = features.velocity_xy
        lateral_speed = abs(vx)

        # Multi-finger open hand or broad gesture moving rapidly horizontally
        if (
            self.swipe_cooldown_counter == 0
            and features.extended_count >= 2
            and lateral_speed > self.swipe_velocity_threshold
            and abs(vx) > abs(vy) * 1.3
        ):
            self.swipe_cooldown_counter = self.swipe_cooldown_frames
            if vx < 0:
                return Gesture.SWIPE_LEFT, None   # Left slide -> Back
            else:
                return Gesture.SWIPE_RIGHT, None  # Right slide -> Forward

        # ---------------------------------------------------------------------
        # 5. PRIORITY 5: CONTINUOUS CURSOR MOVEMENT
        # ---------------------------------------------------------------------
        if features.index_extended:
            return Gesture.CURSOR_MOVE, None

        return Gesture.NONE, None


# =============================================================================
# 7. MASTER GESTURE CONTROL PIPELINE
# =============================================================================

class GestureControlPipeline:
    """
    Unified, modular gesture control system.
    Orchestrates landmark extraction, coordinate transformation, smoothing,
    gesture classification, and hardware action execution.
    """

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.extractor = LandmarkExtractor()
        self.transformer = CoordinateTransformer(margin_x=0.15, margin_y=0.15)
        self.smoother = CursorSmoother()
        self.recognizer = GestureRecognizer()
        self.executor = ActionExecutor()

        self.last_action_desc: str = "Ready"
        self.last_action_time: float = 0.0

    def process_frame_landmarks(
        self,
        raw_landmarks: List[any]
    ) -> Tuple[Gesture, Tuple[int, int], ExtractedFeatures]:
        """
        Process hand landmarks through the full gesture pipeline.
        Returns: (detected_gesture, (cursor_x, cursor_y), extracted_features)
        """
        if not raw_landmarks:
            self.smoother.reset()
            self.recognizer.reset_state()
            return Gesture.NONE, (0, 0), None

        # 1. Landmark & Feature Extraction
        features = self.extractor.extract(
            raw_landmarks=raw_landmarks,
            prev_palm_positions=list(self.recognizer.palm_history)
        )
        if not features:
            return Gesture.NONE, (0, 0), None

        # Update palm trajectory
        palm_center = (
            (features.landmarks[0].x + features.landmarks[9].x) / 2.0,
            (features.landmarks[0].y + features.landmarks[9].y) / 2.0
        )
        self.recognizer.palm_history.append(palm_center)

        # 2. Gesture Recognition & State Engine
        gesture, scroll_steps = self.recognizer.process_frame(features)

        # 3. Coordinate Transformation & Cursor Smoothing
        # Landmark 8 (Index tip) continuously drives cursor coordinates
        norm_x = features.index_tip.x
        norm_y = features.index_tip.y
        raw_screen_x, raw_screen_y = self.transformer.transform(norm_x, norm_y)
        cursor_x, cursor_y = self.smoother.smooth(raw_screen_x, raw_screen_y)

        # 4. Action Execution
        now = time.time()
        if gesture == Gesture.RESET:
            self.smoother.reset()
            self.last_action_desc = "RESET (Baselines Cleared)"
            self.last_action_time = now

        elif gesture == Gesture.CLICK:
            self.executor.click(cursor_x, cursor_y)
            self.last_action_desc = "CLICK / ENTER"
            self.last_action_time = now

        elif gesture == Gesture.SCROLL_UP:
            self.executor.scroll(scroll_steps or 1)
            self.last_action_desc = "SCROLL UP"
            self.last_action_time = now

        elif gesture == Gesture.SCROLL_DOWN:
            self.executor.scroll(scroll_steps or -1)
            self.last_action_desc = "SCROLL DOWN"
            self.last_action_time = now

        elif gesture == Gesture.SWIPE_LEFT:
            self.executor.navigate_back()
            self.last_action_desc = "BACK (Alt + Left)"
            self.last_action_time = now

        elif gesture == Gesture.SWIPE_RIGHT:
            self.executor.navigate_forward()
            self.last_action_desc = "FORWARD (Alt + Right)"
            self.last_action_time = now

        elif gesture == Gesture.CURSOR_MOVE:
            self.executor.move_cursor(cursor_x, cursor_y)

        return gesture, (cursor_x, cursor_y), features

    def run_standalone(self) -> None:
        """
        Runs the full gesture pipeline in interactive standalone OpenCV webcam mode.
        Displays real-time mirrored video, landmark skeleton, tracking box, and action HUD.
        """
        print("=" * 68)
        print("           GESTURE FLOW - REAL-TIME GESTURE CONTROLLER           ")
        print("=" * 68)
        print("  Controls:")
        print("    [Index Tip]            : Continuous Cursor Movement")
        print("    [Pinch / Tap]          : Click / Enter Action")
        print("    [Two Fingers Up/Down]  : Smooth Scrolling Up / Down")
        print("    [Swipe Left]           : Browser / System Back (Alt + Left)")
        print("    [Swipe Right]          : Browser / System Forward (Alt + Right)")
        print("    [Fist / Closed Palm]   : Instant Reset (Baselines & Buffers)")
        print("    [ESC / Q]              : Quit Application")
        print("=" * 68)

        # Initialize MediaPipe Hands
        try:
            import mediapipe as mp
            mp_hands = mp.solutions.hands
            hands = mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.55,
                min_tracking_confidence=0.50,
                model_complexity=0
            )
            mp_draw = mp.solutions.drawing_utils
            mp_styles = mp.solutions.drawing_styles
        except Exception as e:
            print(f"[Error] MediaPipe initialization failed: {e}")
            return

        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW if HAS_WIN32 else cv2.CAP_ANY)
        if not cap.isOpened():
            cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            print(f"[Error] Could not open camera at index {self.camera_index}.")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)

        window_name = "Gesture Flow - Live Control HUD"
        cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

        last_time = time.time()
        fps = 30.0

        try:
            while cap.isOpened():
                success, frame = cap.read()
                if not success or frame is None:
                    time.sleep(0.005)
                    continue

                # Flip horizontally for natural intuitive mirror interaction
                frame = cv2.flip(frame, 1)
                h, w, _ = frame.shape

                # Calculate FPS
                now = time.time()
                dt = now - last_time
                if dt > 0:
                    fps = 0.9 * fps + 0.1 * (1.0 / dt)
                last_time = now

                # MediaPipe inference
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                rgb_frame.flags.writeable = False
                results = hands.process(rgb_frame)

                detected_gesture = Gesture.NONE
                features = None
                cursor_pt = (0, 0)

                if results.multi_hand_landmarks:
                    raw_landmarks = results.multi_hand_landmarks[0].landmark
                    detected_gesture, cursor_pt, features = self.process_frame_landmarks(raw_landmarks)

                    # Draw MediaPipe hand skeleton
                    mp_draw.draw_landmarks(
                        frame,
                        results.multi_hand_landmarks[0],
                        mp_hands.HAND_CONNECTIONS,
                        mp_styles.get_default_hand_landmarks_style(),
                        mp_styles.get_default_hand_connections_style()
                    )
                else:
                    self.process_frame_landmarks([])

                # -------------------------------------------------------------
                # RENDER INTERACTIVE HUD OVERLAY
                # -------------------------------------------------------------
                # 1. Draw Active Interaction Bounds (Margins)
                mx = int(self.transformer.margin_x * w)
                my = int(self.transformer.margin_y * h)
                cv2.rectangle(frame, (mx, my), (w - mx, h - my), (80, 80, 80), 1, cv2.LINE_AA)

                # 2. Highlight Landmark 8 (Index Tip pointer)
                if features:
                    ix = int(features.index_tip.x * w)
                    iy = int(features.index_tip.y * h)
                    color = (0, 255, 0) if features.index_extended else (0, 165, 255)
                    cv2.circle(frame, (ix, iy), 8, color, -1)
                    cv2.circle(frame, (ix, iy), 12, (255, 255, 255), 2)

                # 3. Top Status HUD Bar
                cv2.rectangle(frame, (0, 0), (w, 50), (20, 20, 20), -1)
                cv2.putText(frame, f"FPS: {fps:.0f}", (15, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                gesture_text = f"Gesture: {detected_gesture.value}"
                cv2.putText(frame, gesture_text, (130, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                # Action notification banner
                if (now - self.last_action_time) < 1.0:
                    cv2.rectangle(frame, (0, h - 45), (w, h), (0, 120, 255), -1)
                    cv2.putText(frame, f"Action: {self.last_action_desc}", (20, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

                cv2.imshow(window_name, frame)

                # Keyboard controls
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord('q'), ord('Q')):
                    break
                elif key in (ord('r'), ord('R')):
                    self.recognizer.reset_state()
                    self.smoother.reset()

        finally:
            cap.release()
            cv2.destroyAllWindows()
            print("[GestureFlow] Pipeline shut down cleanly.")


# =============================================================================
# 8. DIRECT ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    pipeline = GestureControlPipeline()
    pipeline.run_standalone()
