"""
MediaPipe Hand Landmark Detection
Performs local hand landmark tracking on OpenCV video frames with lightweight fast inference.
"""
import time
from typing import Optional, List, Tuple
import cv2
import numpy as np
from android.models.gesture_models import HandFrameData, LandmarkPoint


class HandDetector:
    """
    Tracks 21 3D hand landmarks in real time using MediaPipe Hands Lite.
    All processing is performed strictly locally on device.
    """

    def __init__(
        self,
        max_num_hands: int = 1,
        min_detection_confidence: float = 0.55,
        min_tracking_confidence: float = 0.50,
        model_complexity: int = 0
    ):
        self.max_num_hands = max_num_hands
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.model_complexity = model_complexity

        self._mp_hands = None
        self._hands = None
        self._init_mediapipe()

    def _init_mediapipe(self) -> None:
        """Initialize MediaPipe Hands solution with Lite model."""
        try:
            import mediapipe as mp
            self._mp_hands = mp.solutions.hands
            self._hands = self._mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=self.max_num_hands,
                model_complexity=self.model_complexity,
                min_detection_confidence=self.min_detection_confidence,
                min_tracking_confidence=self.min_tracking_confidence
            )
        except Exception as e:
            print(f"[HandDetector] Warning: MediaPipe initialization exception: {e}")
            self._hands = None

    def detect_hands(self, frame_bgr: np.ndarray) -> HandFrameData:
        """
        Process a single BGR frame and extract normalized hand landmarks.
        Uses fast scaled inference for optimal FPS.
        """
        now = time.time()
        if frame_bgr is None or self._hands is None:
            return HandFrameData(hand_detected=False, timestamp=now)

        h, w, _ = frame_bgr.shape

        # Downscale image for fast MediaPipe inference if larger than 360px wide
        if w > 360:
            scale = 360.0 / w
            proc_w = 360
            proc_h = int(h * scale)
            small_frame = cv2.resize(frame_bgr, (proc_w, proc_h), interpolation=cv2.INTER_NEAREST)
        else:
            small_frame = frame_bgr

        # MediaPipe requires RGB input
        frame_rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        frame_rgb.flags.writeable = False

        try:
            results = self._hands.process(frame_rgb)
        except Exception as e:
            return HandFrameData(hand_detected=False, timestamp=now)

        if not results.multi_hand_landmarks:
            return HandFrameData(hand_detected=False, timestamp=now)

        # Extract primary tracked hand
        first_hand_landmarks = results.multi_hand_landmarks[0]
        handedness_label = "Right"
        if results.multi_handedness and len(results.multi_handedness) > 0:
            handedness_label = results.multi_handedness[0].classification[0].label

        landmarks_list: List[LandmarkPoint] = []
        raw_coords: List[Tuple[float, float, float]] = []

        xs: List[int] = []
        ys: List[int] = []

        for lm in first_hand_landmarks.landmark:
            landmarks_list.append(
                LandmarkPoint(
                    x=float(lm.x),
                    y=float(lm.y),
                    z=float(lm.z) if hasattr(lm, 'z') else 0.0,
                    visibility=float(lm.visibility) if hasattr(lm, 'visibility') else 1.0
                )
            )
            raw_coords.append((float(lm.x), float(lm.y), float(lm.z) if hasattr(lm, 'z') else 0.0))
            xs.append(int(lm.x * w))
            ys.append(int(lm.y * h))

        # Compute bounding box
        bbox = None
        if xs and ys:
            pad = 20
            min_x = max(0, min(xs) - pad)
            min_y = max(0, min(ys) - pad)
            max_x = min(w, max(xs) + pad)
            max_y = min(h, max(ys) + pad)
            bbox = (min_x, min_y, max_x, max_y)

        return HandFrameData(
            hand_detected=True,
            handedness=handedness_label,
            landmarks=landmarks_list,
            raw_landmarks=raw_coords,
            bounding_box=bbox,
            timestamp=now
        )

    def close(self) -> None:
        """Release MediaPipe resources."""
        if self._hands is not None:
            self._hands.close()
            self._hands = None
