"""
Visual Overlay Renderer
Draws hand skeleton, fingertip tracking nodes, bounding boxes, two-finger touchpad cursors, and HUD metrics onto camera frames.
Optimized with direct ROI-blending to eliminate full-frame copy overhead.
"""
from typing import List, Tuple, Optional
import cv2
import numpy as np
from android.models.gesture_models import LandmarkPoint, HandFrameData, GestureResult, PipelineMetrics

# Hand connections (pairs of landmark indices)
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),        # Index
    (5, 9), (9, 10), (10, 11), (11, 12),    # Middle
    (9, 13), (13, 14), (14, 15), (15, 16),  # Ring
    (13, 17), (17, 18), (18, 19), (19, 20), # Pinky
    (0, 17)                                # Palm base
]


class OverlayRenderer:
    """Renders high-contrast, modern UI visual overlays onto OpenCV video frames."""

    # Colors (BGR format matching palette: Green, Cyan, Yellow, Teal)
    COLOR_SKELETON = (219, 191, 50)       # #32BFDB Cyan / Sky
    COLOR_JOINT = (255, 255, 255)         # #FFFFFF Pure White
    COLOR_INDEX_TIP = (219, 191, 50)      # #32BFDB Cyan
    COLOR_MIDDLE_TIP = (169, 155, 83)     # #539BA9 Teal
    COLOR_PINCH = (35, 195, 253)          # #FDC323 Yellow / Amber
    COLOR_BBOX = (93, 120, 0)             # #00785D Dark Green
    COLOR_HUD_BG = (23, 15, 11)           # #0B0F17 Deep Obsidian
    COLOR_TEXT = (255, 255, 255)          # #FFFFFF Crisp White
    COLOR_ACCENT = (219, 191, 50)         # #32BFDB Cyan Accent

    @classmethod
    def draw_hand_overlay(
        cls,
        frame: np.ndarray,
        hand_data: HandFrameData,
        gesture_result: Optional[GestureResult] = None,
        fps: float = 0.0,
        show_hud: bool = True,
        metrics: Optional[PipelineMetrics] = None
    ) -> np.ndarray:
        """
        Draws hand skeleton, tracking nodes, touchpad cursors, HUD, and real-time diagnostics onto the frame.
        """
        if frame is None:
            return frame

        h, w, _ = frame.shape

        if hand_data.hand_detected and hand_data.landmarks:
            landmarks = hand_data.landmarks

            # 1. Draw Bounding Box
            if hand_data.bounding_box:
                bx1, by1, bx2, by2 = hand_data.bounding_box
                cv2.rectangle(frame, (bx1, by1), (bx2, by2), cls.COLOR_BBOX, 1, cv2.LINE_AA)

            # 2. Draw Skeleton Connections
            for start_idx, end_idx in HAND_CONNECTIONS:
                if start_idx < len(landmarks) and end_idx < len(landmarks):
                    p1 = (int(landmarks[start_idx].x * w), int(landmarks[start_idx].y * h))
                    p2 = (int(landmarks[end_idx].x * w), int(landmarks[end_idx].y * h))
                    cv2.line(frame, p1, p2, cls.COLOR_SKELETON, 2, cv2.LINE_AA)

            # 3. Draw Joint Circles
            for idx, lm in enumerate(landmarks):
                cx, cy = int(lm.x * w), int(lm.y * h)

                if idx == 8:
                    # Index Tip
                    cv2.circle(frame, (cx, cy), 8, cls.COLOR_INDEX_TIP, -1, cv2.LINE_AA)
                    cv2.circle(frame, (cx, cy), 11, (255, 255, 255), 1, cv2.LINE_AA)
                elif idx == 4:
                    # Thumb Tip
                    cv2.circle(frame, (cx, cy), 7, cls.COLOR_PINCH, -1, cv2.LINE_AA)
                elif idx == 12:
                    # Middle Tip
                    cv2.circle(frame, (cx, cy), 7, cls.COLOR_MIDDLE_TIP, -1, cv2.LINE_AA)
                else:
                    cv2.circle(frame, (cx, cy), 4, cls.COLOR_JOINT, -1, cv2.LINE_AA)

            # 4. Mode-Specific Visual Highlights
            g_name = gesture_result.gesture if gesture_result else "NONE"

            # A. Two-Finger Touchpad Mode Visualizer
            if "TWO_FINGER" in g_name:
                p_index = (int(landmarks[8].x * w), int(landmarks[8].y * h))
                p_middle = (int(landmarks[12].x * w), int(landmarks[12].y * h))
                mid_x = (p_index[0] + p_middle[0]) // 2
                mid_y = (p_index[1] + p_middle[1]) // 2
                cv2.line(frame, p_index, p_middle, cls.COLOR_ACCENT, 2, cv2.LINE_AA)
                cv2.circle(frame, (mid_x, mid_y), 12, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.circle(frame, (mid_x, mid_y), 6, cls.COLOR_ACCENT, -1, cv2.LINE_AA)

            # B. Pinch & Zoom Visualizer
            elif g_name in ("PINCH", "PINCH_IN", "PINCH_OUT"):
                p_thumb = (int(landmarks[4].x * w), int(landmarks[4].y * h))
                p_index = (int(landmarks[8].x * w), int(landmarks[8].y * h))
                cv2.line(frame, p_thumb, p_index, cls.COLOR_PINCH, 3, cv2.LINE_AA)
                pinch_mid = ((p_thumb[0] + p_index[0]) // 2, (p_thumb[1] + p_index[1]) // 2)
                radius = 16 if g_name == "PINCH_OUT" else (8 if g_name == "PINCH_IN" else 12)
                cv2.circle(frame, pinch_mid, radius, cls.COLOR_PINCH, 2, cv2.LINE_AA)

            # C. Air Tap Ripple Visualizer
            elif g_name == "AIR_TAP":
                p_index = (int(landmarks[8].x * w), int(landmarks[8].y * h))
                cv2.circle(frame, p_index, 20, (120, 255, 120), 3, cv2.LINE_AA)
                cv2.circle(frame, p_index, 28, (120, 255, 120), 1, cv2.LINE_AA)

        # 5. Draw HUD Dashboard (Top bar)
        if show_hud:
            cls._draw_hud_dashboard(frame, gesture_result, fps, hand_data.hand_detected, metrics)

        return frame

    @classmethod
    def _draw_hud_dashboard(
        cls,
        frame: np.ndarray,
        gesture_result: Optional[GestureResult],
        fps: float,
        hand_detected: bool,
        metrics: Optional[PipelineMetrics] = None
    ) -> None:
        """Renders top info bar with FPS, Gesture name, Confidence, and timing metrics using fast ROI blending."""
        h, w, _ = frame.shape

        # Fast ROI alpha blending for top HUD (avoiding full-frame copy)
        hud_h = min(55, h)
        hud_roi = frame[0:hud_h, 0:w]
        overlay_box = np.full_like(hud_roi, cls.COLOR_HUD_BG)
        cv2.addWeighted(overlay_box, 0.80, hud_roi, 0.20, 0, hud_roi)

        # Bottom accent line
        cv2.line(frame, (0, hud_h), (w, hud_h), (80, 80, 90), 1)

        # FPS indicator
        fps_text = f"FPS: {fps:.1f}"
        cv2.putText(frame, fps_text, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 255, 120), 2, cv2.LINE_AA)

        # Hand Status indicator
        status_color = (0, 255, 0) if hand_detected else (150, 150, 150)
        status_text = "HAND: TRACKING" if hand_detected else "HAND: SEARCHING"
        cv2.putText(frame, status_text, (130, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_color, 1, cv2.LINE_AA)

        # Gesture & Action HUD
        if gesture_result and gesture_result.gesture != "NONE":
            g_name = gesture_result.gesture
            act_name = gesture_result.action
            conf = int(gesture_result.confidence * 100)

            hud_text = f"{g_name} -> {act_name} ({conf}%)"
            (tw, th), _ = cv2.getTextSize(hud_text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.putText(frame, hud_text, (max(320, w - tw - 15), 35), cv2.FONT_HERSHEY_SIMPLEX, 0.55, cls.COLOR_ACCENT, 2, cv2.LINE_AA)

        # Bottom Latency Diagnostics Bar (if metrics provided)
        active_metrics = metrics or (gesture_result.metrics if gesture_result else None)
        if active_metrics and active_metrics.total_pipeline_ms > 0:
            bar_y = max(0, h - 28)
            lat_roi = frame[bar_y:h, 0:w]
            lat_box = np.full_like(lat_roi, (15, 18, 24))
            cv2.addWeighted(lat_box, 0.85, lat_roi, 0.15, 0, lat_roi)

            lat_text = f"Latency: {active_metrics.total_pipeline_ms:.1f}ms [Vision: {active_metrics.vision_ms:.1f}ms | Smooth: {active_metrics.smoothing_ms:.1f}ms | Class: {active_metrics.classification_ms:.1f}ms]"
            cv2.putText(frame, lat_text, (10, h - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (180, 220, 255), 1, cv2.LINE_AA)
