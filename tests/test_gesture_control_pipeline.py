"""
Unit Tests for the Refactored Gesture Control Pipeline
Verifies landmark extraction, continuous Landmark 8 cursor tracking,
immediate click / tap detection, navigation swipes (Back & Forward),
two-finger scrolling, and fist / closed palm reset.
"""
import pytest
from gesture_control_pipeline import (
    Gesture,
    Point3D,
    ExtractedFeatures,
    LandmarkExtractor,
    CoordinateTransformer,
    CursorSmoother,
    GestureRecognizer,
    GestureControlPipeline
)


def create_mock_hand(
    index_extended: bool = True,
    middle_extended: bool = False,
    ring_extended: bool = False,
    pinky_extended: bool = False,
    thumb_extended: bool = False,
    pinch: bool = False,
    index_x: float = 0.45,
    index_y: float = 0.30,
    z_offset: float = 0.0
):
    """Generates synthetic 21-point MediaPipe hand landmark skeleton."""
    hand = [Point3D(0.5, 0.8, 0.0) for _ in range(21)]
    hand[0] = Point3D(0.50, 0.80, 0.0)  # Wrist

    # Thumb
    hand[1] = Point3D(0.45, 0.75, 0.0)
    hand[2] = Point3D(0.40, 0.70, 0.0)
    hand[3] = Point3D(0.35, 0.65, 0.0)
    hand[4] = Point3D(0.30 if thumb_extended else 0.42, 0.60 if thumb_extended else 0.72, 0.0)

    # Index
    hand[5] = Point3D(0.45, 0.60, 0.0)
    hand[6] = Point3D(0.45, 0.50, 0.0)
    hand[7] = Point3D(0.45, 0.40, 0.0)
    hand[8] = Point3D(index_x if index_extended else 0.45, index_y if index_extended else 0.62, z_offset)

    # Middle
    hand[9] = Point3D(0.50, 0.58, 0.0)
    hand[10] = Point3D(0.50, 0.48, 0.0)
    hand[11] = Point3D(0.50, 0.38, 0.0)
    hand[12] = Point3D(0.50, 0.28 if middle_extended else 0.62, 0.0)

    # Ring
    hand[13] = Point3D(0.55, 0.60, 0.0)
    hand[14] = Point3D(0.55, 0.50, 0.0)
    hand[15] = Point3D(0.55, 0.40, 0.0)
    hand[16] = Point3D(0.55, 0.32 if ring_extended else 0.62, 0.0)

    # Pinky
    hand[17] = Point3D(0.60, 0.63, 0.0)
    hand[18] = Point3D(0.60, 0.55, 0.0)
    hand[19] = Point3D(0.60, 0.47, 0.0)
    hand[20] = Point3D(0.60, 0.38 if pinky_extended else 0.64, 0.0)

    if pinch:
        # Move thumb tip close to index tip
        hand[4] = Point3D(hand[8].x - 0.01, hand[8].y + 0.01, hand[8].z)

    return hand


def test_cursor_movement_tracking():
    """Verify cursor coordinates track Landmark 8 continuously."""
    pipeline = GestureControlPipeline()
    hand = create_mock_hand(index_extended=True, index_x=0.45, index_y=0.30)

    gesture, (cx, cy), features = pipeline.process_frame_landmarks(hand)
    assert gesture in (Gesture.CURSOR_MOVE, Gesture.NONE)
    assert features is not None
    assert features.index_extended is True
    assert cx > 0 and cy > 0


def test_pinch_click_action():
    """Verify pinching index finger to thumb triggers an immediate click."""
    recognizer = GestureRecognizer(pinch_threshold=0.38)
    extractor = LandmarkExtractor()

    # Frame 1: Index pointing (idle)
    hand1 = create_mock_hand(index_extended=True, pinch=False)
    feat1 = extractor.extract(hand1)
    g1, _ = recognizer.process_frame(feat1)
    assert g1 == Gesture.CURSOR_MOVE

    # Frame 2: Pinch engaged
    hand2 = create_mock_hand(index_extended=True, pinch=True)
    feat2 = extractor.extract(hand2)
    g2, _ = recognizer.process_frame(feat2)
    assert g2 == Gesture.CLICK

    # Frame 3: Holding pinch during cooldown should NOT fire repeated clicks
    g3, _ = recognizer.process_frame(feat2)
    assert g3 == Gesture.NONE


def test_fist_closed_palm_instant_reset():
    """Verify fist / closed palm instantly resets tracking baselines and states."""
    recognizer = GestureRecognizer()
    extractor = LandmarkExtractor()

    # Artificially populate state & cooldowns
    recognizer.click_cooldown_counter = 5
    recognizer.swipe_cooldown_counter = 8
    recognizer.pinch_is_engaged = True

    # Closed fist (all fingers curled)
    fist_hand = create_mock_hand(
        index_extended=False,
        middle_extended=False,
        ring_extended=False,
        pinky_extended=False,
        thumb_extended=False
    )
    features = extractor.extract(fist_hand)
    assert features.is_fist_or_closed_palm is True

    gesture, _ = recognizer.process_frame(features)
    assert gesture == Gesture.RESET
    assert recognizer.click_cooldown_counter == 0
    assert recognizer.swipe_cooldown_counter == 0
    assert recognizer.pinch_is_engaged is False


def test_two_finger_scrolling():
    """Verify two fingers moving up/down triggers Scroll Up / Down."""
    recognizer = GestureRecognizer(scroll_threshold=0.01)
    extractor = LandmarkExtractor()

    # Frame 1: Two fingers extended
    hand1 = create_mock_hand(index_extended=True, middle_extended=True)
    hand1[12].x = hand1[8].x + 0.02
    hand1[12].y = hand1[8].y
    feat1 = extractor.extract(hand1)
    assert feat1.is_two_finger_mode is True
    g1, _ = recognizer.process_frame(feat1)

    # Frame 2: Two fingers moved upwards (dy < -0.015)
    hand2 = create_mock_hand(index_extended=True, middle_extended=True)
    hand2[8].y -= 0.03
    hand2[12].x = hand2[8].x + 0.02
    hand2[12].y = hand2[8].y
    feat2 = extractor.extract(hand2)
    g2, step2 = recognizer.process_frame(feat2)
    assert g2 == Gesture.SCROLL_UP
    assert step2 == 1

    # Frame 3: Two fingers moved downwards
    hand3 = create_mock_hand(index_extended=True, middle_extended=True)
    hand3[8].y += 0.04
    hand3[12].x = hand3[8].x + 0.02
    hand3[12].y = hand3[8].y
    feat3 = extractor.extract(hand3)
    g3, step3 = recognizer.process_frame(feat3)
    assert g3 == Gesture.SCROLL_DOWN
    assert step3 == -1


def test_navigation_swipes():
    """Verify lateral horizontal slides trigger Back (Left) and Forward (Right)."""
    recognizer = GestureRecognizer(swipe_velocity_threshold=0.03)

    # Mock open hand with leftward velocity
    features_left = ExtractedFeatures(
        landmarks=[],
        hand_scale=0.2,
        index_tip=Point3D(0.3, 0.4),
        thumb_tip=Point3D(0.2, 0.5),
        middle_tip=Point3D(0.3, 0.3),
        pinch_dist_norm=0.8,
        index_extended=True,
        middle_extended=True,
        ring_extended=True,
        pinky_extended=True,
        thumb_extended=True,
        extended_count=5,
        is_fist_or_closed_palm=False,
        is_two_finger_mode=False,
        two_finger_center=(0.3, 0.4),
        velocity_xy=(-0.05, 0.005)
    )
    g_left, _ = recognizer.process_frame(features_left)
    assert g_left == Gesture.SWIPE_LEFT

    recognizer.reset_state()

    # Mock open hand with rightward velocity
    features_right = ExtractedFeatures(
        landmarks=[],
        hand_scale=0.2,
        index_tip=Point3D(0.6, 0.4),
        thumb_tip=Point3D(0.5, 0.5),
        middle_tip=Point3D(0.6, 0.3),
        pinch_dist_norm=0.8,
        index_extended=True,
        middle_extended=True,
        ring_extended=True,
        pinky_extended=True,
        thumb_extended=True,
        extended_count=5,
        is_fist_or_closed_palm=False,
        is_two_finger_mode=False,
        two_finger_center=(0.6, 0.4),
        velocity_xy=(0.05, 0.005)
    )
    g_right, _ = recognizer.process_frame(features_right)
    assert g_right == Gesture.SWIPE_RIGHT


def test_coordinate_transformer_reach_all_corners():
    """Verify margin scaling allows cursor to reach physical 0,0 and max screen boundaries."""
    transformer = CoordinateTransformer(margin_x=0.15, margin_y=0.15)
    sw, sh = transformer.screen_w, transformer.screen_h

    # Top-Left corner within margin
    x_tl, y_tl = transformer.transform(0.10, 0.10)
    assert x_tl == 0
    assert y_tl == 0

    # Bottom-Right corner within margin
    x_br, y_br = transformer.transform(0.90, 0.90)
    assert x_br == sw - 1
    assert y_br == sh - 1

    # Center
    x_c, y_c = transformer.transform(0.50, 0.50)
    assert abs(x_c - sw // 2) <= 2
    assert abs(y_c - sh // 2) <= 2


def test_cursor_smoother_deadband():
    """Verify tiny tremors (< 3px) are locked to suppress jitter."""
    smoother = CursorSmoother(deadband_px=3.0)
    smoother.smooth(500, 500)

    # 1.5 pixel jitter should be ignored
    sx, sy = smoother.smooth(501, 501)
    assert sx == 500
    assert sy == 500

    # Large motion moves smoothly
    sx2, sy2 = smoother.smooth(600, 600)
    assert sx2 > 500
    assert sy2 > 500
