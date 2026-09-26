"""
MediaPipe Hand Landmark Detection
Performs local hand landmark tracking on OpenCV video frames with lightweight fast inference.
Supports desktop MediaPipe Hands solution with graceful fallback reporting when running in
environments without compiled MediaPipe wheels (such as stock Python-for-Android).
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
        self._tasks_landmarker = None
        self._last_results = None
        self._last_video_timestamp_ms = -1
        self._mp_image = None
        self._backend_name = "None"
        self._init_detector()

    def _init_detector(self) -> None:
        """Initialize MediaPipe Hands (legacy solutions API or new Tasks API)."""
        try:
            import mediapipe as mp
            if hasattr(mp, "solutions") and hasattr(mp.solutions, "hands"):
                self._mp_hands = mp.solutions.hands
                self._hands = self._mp_hands.Hands(
                    static_image_mode=False,
                    max_num_hands=self.max_num_hands,
                    model_complexity=self.model_complexity,
                    min_detection_confidence=self.min_detection_confidence,
                    min_tracking_confidence=self.min_tracking_confidence
                )
                self._backend_name = "MediaPipe Desktop (Python Wheel)"
                return
        except Exception:
            self._hands = None

        # Fallback: MediaPipe Tasks Vision API (mediapipe >= 1.0, where
        # mp.solutions.hands was removed, e.g. Python 3.12+/3.14 wheels).
        try:
            import mediapipe as mp
            from mediapipe.tasks.python.vision.core import image as mp_image_mod
            self._mp_image_mod = mp_image_mod
            from mediapipe.tasks import python as mp_tasks
            from mediapipe.tasks.python import vision as mp_vision
            import os

            model_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "models", "hand_landmarker.task"
            )
            if not os.path.exists(model_path):
                self._backend_name = "Unavailable (hand_landmarker.task model file missing)"
                return

            base_options = mp_tasks.BaseOptions(model_asset_path=model_path)
            options = mp_vision.HandLandmarkerOptions(
                base_options=base_options,
                running_mode=mp_vision.RunningMode.VIDEO,
                num_hands=self.max_num_hands,
                min_hand_detection_confidence=self.min_detection_confidence,
                min_hand_presence_confidence=self.min_tracking_confidence,
                min_tracking_confidence=self.min_tracking_confidence
            )
            self._tasks_landmarker = mp_vision.HandLandmarker.create_from_options(options)
            self._last_results = None
            self._backend_name = "MediaPipe Tasks Vision (HandLandmarker)"
            print(f"[HandDetector] Successfully initialized {self._backend_name}.")
        except Exception as e:
            # MediaPipe is not compiled for Python-for-Android arm64.
            # In native Android production, MediaPipe Tasks Vision AAR is integrated via Java.
            self._tasks_landmarker = None
            self._backend_name = f"Unavailable ({type(e).__name__})"
            print(f"[HandDetector] Warning: Hand detector unavailable ({e}). Running without MediaPipe.")

    def is_available(self) -> bool:
        """Check if active landmark tracking backend is initialized."""
        return self._hands is not None or self._tasks_landmarker is not None

    def get_backend_name(self) -> str:
        """Return the active vision backend name."""
        return self._backend_name

    def detect_hands(self, frame_bgr: np.ndarray) -> HandFrameData:
        """
        Process a single BGR frame and extract normalized hand landmarks.
        Uses fast scaled inference for optimal FPS.
        """
        now = time.time()
        if frame_bgr is None or self._hands is None and self._tasks_landmarker is None:
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

        if self._hands is not None:
            frame_rgb.flags.writeable = False
            try:
                results = self._hands.process(frame_rgb)
            except Exception:
                return HandFrameData(hand_detected=False, timestamp=now)
        else:
            # MediaPipe Tasks Vision VIDEO mode path (mp.solutions unavailable)
            try:
                mp_image = self._mp_image_mod.Image(
                    image_format=self._mp_image_mod.ImageFormat.SRGB, data=frame_rgb
                )
                timestamp_ms = int(now * 1000.0)
                if timestamp_ms <= self._last_video_timestamp_ms:
                    timestamp_ms = self._last_video_timestamp_ms + 1
                self._last_video_timestamp_ms = timestamp_ms
                results = self._tasks_landmarker.detect_for_video(mp_image, timestamp_ms)
            except Exception:
                return HandFrameData(hand_detected=False, timestamp=now)

        first_hand_landmarks = None
        handedness_label = "Right"
        if self._hands is not None:
            if not results or not results.multi_hand_landmarks:
                return HandFrameData(hand_detected=False, timestamp=now)
            first_hand_landmarks = results.multi_hand_landmarks[0]
            if results.multi_handedness and len(results.multi_handedness) > 0:
                handedness_label = results.multi_handedness[0].classification[0].label
        else:
            if (not results
                    or not getattr(results, "hand_landmarks", None)
                    or len(results.hand_landmarks) == 0):
                return HandFrameData(hand_detected=False, timestamp=now)
            first_hand_landmarks = results.hand_landmarks[0]
            if getattr(results, "handedness", None) and len(results.handedness) > 0:
                handedness_label = results.handedness[0][0].category_name

        landmarks_list: List[LandmarkPoint] = []
        raw_coords: List[Tuple[float, float, float]] = []

        xs: List[int] = []
        ys: List[int] = []

        lm_iterable = first_hand_landmarks.landmark if hasattr(first_hand_landmarks, "landmark") else first_hand_landmarks
        for lm in lm_iterable:
            landmarks_list.append(
                LandmarkPoint(
                    x=float(lm.x),
                    y=float(lm.y),
                    z=float(lm.z) if hasattr(lm, 'z') else 0.0,
                    visibility=float(lm.visibility) if getattr(lm, 'visibility', None) is not None else 1.0
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
        if self._tasks_landmarker is not None:
            try:
                self._tasks_landmarker.close()
            except Exception:
                pass
            self._tasks_landmarker = None
