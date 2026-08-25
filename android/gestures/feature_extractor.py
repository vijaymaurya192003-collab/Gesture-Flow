"""
Geometric Feature Extractor
Extracts normalized spatial relationships, finger flexion states, pinch distances,
two-finger touchpad metrics, thumbs orientations, and velocity vectors.
"""
from typing import List, Tuple, Optional, Deque
from dataclasses import dataclass
import numpy as np
from android.models.gesture_models import LandmarkPoint


@dataclass
class HandFeatures:
    """Calculated geometric metrics of a hand."""
    # Finger extended states: True if finger is extended outward, False if curled
    thumb_extended: bool = False
    index_extended: bool = False
    middle_extended: bool = False
    ring_extended: bool = False
    pinky_extended: bool = False

    # Normalized pinch distance between Thumb Tip (#4) and Index Tip (#8)
    pinch_distance_norm: float = 1.0

    # Euclidean distance between Thumb Tip (#4) and Middle Tip (#12)
    middle_pinch_distance_norm: float = 1.0

    # Frame-over-frame pinch distance differential (positive = expanding/pinch out, negative = contracting/pinch in)
    pinch_delta: float = 0.0

    # Palm center normalized coordinate (x, y)
    palm_center: Tuple[float, float] = (0.5, 0.5)

    # Hand scale (distance between Wrist and Middle MCP) used for normalization
    hand_scale: float = 0.2

    # Pointer coordinate (Index Tip normalized coordinate)
    pointer_pos: Tuple[float, float] = (0.5, 0.5)

    # Velocity vector (dx/frame, dy/frame) across rolling window
    velocity: Tuple[float, float] = (0.0, 0.0)

    # Extended finger count
    extended_count: int = 0

    # Thumbs orientation
    is_thumbs_up: bool = False
    is_thumbs_down: bool = False

    # Two-Finger Touchpad Mode Metrics
    two_finger_center: Tuple[float, float] = (0.5, 0.5)
    two_finger_separation_norm: float = 0.5
    two_finger_delta: Tuple[float, float] = (0.0, 0.0)
    is_two_finger_touchpad: bool = False
    is_peace_sign: bool = False

    # Air Tap detection
    is_air_tap: bool = False
    index_z_velocity: float = 0.0


def _distance_2d(p1: LandmarkPoint, p2: LandmarkPoint) -> float:
    """Euclidean distance in 2D normalized space."""
    return float(np.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2))


def _distance_3d(p1: LandmarkPoint, p2: LandmarkPoint) -> float:
    """Euclidean distance in 3D normalized space."""
    return float(np.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2 + (p1.z - p2.z) ** 2))


def extract_hand_features(
    landmarks: List[LandmarkPoint],
    history_palm_centers: Optional[List[Tuple[float, float]]] = None,
    prev_pinch_distance: Optional[float] = None,
    prev_two_finger_center: Optional[Tuple[float, float]] = None,
    prev_index_z: Optional[float] = None
) -> Optional[HandFeatures]:
    """
    Computes all geometric features from 21 MediaPipe hand landmarks.
    """
    if not landmarks or len(landmarks) < 21:
        return None

    wrist = landmarks[0]
    thumb_cmc = landmarks[1]
    thumb_mcp = landmarks[2]
    thumb_ip = landmarks[3]
    thumb_tip = landmarks[4]

    index_mcp = landmarks[5]
    index_pip = landmarks[6]
    index_dip = landmarks[7]
    index_tip = landmarks[8]

    middle_mcp = landmarks[9]
    middle_pip = landmarks[10]
    middle_dip = landmarks[11]
    middle_tip = landmarks[12]

    ring_mcp = landmarks[13]
    ring_pip = landmarks[14]
    ring_dip = landmarks[15]
    ring_tip = landmarks[16]

    pinky_mcp = landmarks[17]
    pinky_pip = landmarks[18]
    pinky_dip = landmarks[19]
    pinky_tip = landmarks[20]

    # Hand Scale Reference: distance from Wrist (0) to Middle MCP (9)
    hand_scale = max(0.05, _distance_2d(wrist, middle_mcp))

    # 1. Finger extension determination (distance from wrist to tip vs PIP)
    index_extended = _distance_2d(wrist, index_tip) > _distance_2d(wrist, index_pip) * 1.05
    middle_extended = _distance_2d(wrist, middle_tip) > _distance_2d(wrist, middle_pip) * 1.08
    ring_extended = _distance_2d(wrist, ring_tip) > _distance_2d(wrist, ring_pip) * 1.08
    pinky_extended = _distance_2d(wrist, pinky_tip) > _distance_2d(wrist, pinky_pip) * 1.08

    # Thumb extension: check distance from thumb tip to pinky MCP
    thumb_extended = _distance_2d(pinky_mcp, thumb_tip) > _distance_2d(pinky_mcp, thumb_ip) * 1.15

    # 2. Normalized Pinch Distance (Thumb Tip to Index Tip divided by Hand Scale)
    raw_pinch_dist = _distance_3d(thumb_tip, index_tip)
    pinch_distance_norm = raw_pinch_dist / hand_scale

    # Pinch differential for continuous zoom tracking
    pinch_delta = 0.0
    if prev_pinch_distance is not None:
        pinch_delta = pinch_distance_norm - prev_pinch_distance

    # Middle Pinch Distance
    raw_mid_pinch = _distance_3d(thumb_tip, middle_tip)
    middle_pinch_distance_norm = raw_mid_pinch / hand_scale

    # 3. Palm Center
    palm_x = (wrist.x + index_mcp.x + middle_mcp.x + pinky_mcp.x) / 4.0
    palm_y = (wrist.y + index_mcp.y + middle_mcp.y + pinky_mcp.y) / 4.0
    palm_center = (float(palm_x), float(palm_y))

    # 4. Calculate Velocity from History against current palm center
    vx, vy = 0.0, 0.0
    if history_palm_centers and len(history_palm_centers) >= 1:
        oldest = history_palm_centers[0]
        n_frames = len(history_palm_centers)
        vx = (palm_center[0] - oldest[0]) / max(1, n_frames)
        vy = (palm_center[1] - oldest[1]) / max(1, n_frames)

    extended_count = sum([index_extended, middle_extended, ring_extended, pinky_extended])
    if thumb_extended:
        extended_count += 1

    # 5. Thumbs Up / Down Geometric Verification
    other_fingers_curled = not index_extended and not middle_extended and not ring_extended and not pinky_extended
    is_thumbs_up = False
    is_thumbs_down = False

    if thumb_extended and other_fingers_curled:
        # Thumbs up: Tip is higher (smaller y) than IP, MCP, and Wrist; vertical alignment
        if thumb_tip.y < thumb_ip.y < thumb_mcp.y < wrist.y:
            dx = abs(thumb_tip.x - thumb_mcp.x)
            dy = abs(thumb_tip.y - thumb_mcp.y)
            if dy > dx * 0.8:
                is_thumbs_up = True

        # Thumbs down: Tip is lower (larger y) than IP, MCP, and Wrist; vertical alignment
        elif thumb_tip.y > thumb_ip.y > thumb_mcp.y > wrist.y:
            dx = abs(thumb_tip.x - thumb_mcp.x)
            dy = abs(thumb_tip.y - thumb_mcp.y)
            if dy > dx * 0.8:
                is_thumbs_down = True

    # 6. Two-Finger Touchpad Mode Metrics
    two_finger_center = (float((index_tip.x + middle_tip.x) / 2.0), float((index_tip.y + middle_tip.y) / 2.0))
    raw_finger_sep = _distance_2d(index_tip, middle_tip)
    two_finger_separation_norm = raw_finger_sep / hand_scale

    two_finger_delta = (0.0, 0.0)
    if prev_two_finger_center is not None:
        two_finger_delta = (
            float(two_finger_center[0] - prev_two_finger_center[0]),
            float(two_finger_center[1] - prev_two_finger_center[1])
        )

    # Touchpad mode is active when Index and Middle are extended, Ring and Pinky are curled,
    # and the two fingers are held closely together (separation < 0.55)
    is_two_finger_touchpad = False
    is_peace_sign = False
    if index_extended and middle_extended and not ring_extended and not pinky_extended:
        if two_finger_separation_norm < 0.55:
            is_two_finger_touchpad = True
        else:
            is_peace_sign = True

    # 7. Air Tap (Z-Axis Forward Motion Pulse)
    is_air_tap = False
    index_z_velocity = 0.0
    if prev_index_z is not None:
        # Negative z in MediaPipe is closer to camera (forward tap)
        index_z_velocity = float(index_tip.z - prev_index_z)
        if index_extended and not middle_extended and not ring_extended and not pinky_extended:
            # Significant forward motion towards camera
            if index_z_velocity < -0.025:
                is_air_tap = True

    return HandFeatures(
        thumb_extended=thumb_extended,
        index_extended=index_extended,
        middle_extended=middle_extended,
        ring_extended=ring_extended,
        pinky_extended=pinky_extended,
        pinch_distance_norm=pinch_distance_norm,
        middle_pinch_distance_norm=middle_pinch_distance_norm,
        pinch_delta=pinch_delta,
        palm_center=palm_center,
        hand_scale=hand_scale,
        pointer_pos=(float(index_tip.x), float(index_tip.y)),
        velocity=(vx, vy),
        extended_count=extended_count,
        is_thumbs_up=is_thumbs_up,
        is_thumbs_down=is_thumbs_down,
        two_finger_center=two_finger_center,
        two_finger_separation_norm=two_finger_separation_norm,
        two_finger_delta=two_finger_delta,
        is_two_finger_touchpad=is_two_finger_touchpad,
        is_peace_sign=is_peace_sign,
        is_air_tap=is_air_tap,
        index_z_velocity=index_z_velocity
    )
