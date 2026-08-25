"""
Thread-Safe OpenCV Camera Capture & Video Source Provider
Runs frame acquisition in a dedicated background worker thread with multi-backend Windows/Android fallback,
MJPEG hardware acceleration, and synthetic test feed resilience.
"""
import time
import threading
from typing import Optional, Tuple
import cv2
import numpy as np
from android.camera.frame_source import BaseFrameSource


class OpenCVCamera(BaseFrameSource):
    """
    High-performance, thread-safe camera capture provider.
    Tries multiple capture backends (DirectShow, MSMF, Default) and provides a simulated
    fallback stream if physical webcam is inaccessible.
    """

    def __init__(
        self,
        camera_index: int = 0,
        width: int = 640,
        height: int = 480,
        target_fps: int = 30
    ):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.target_fps = target_fps
        self.frame_interval = 1.0 / max(target_fps, 1)

        self._cap: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

        self._latest_frame: Optional[np.ndarray] = None
        self._frame_ready = False
        self._frame_count = 0
        self._fps_start_time = time.time()
        self._current_fps = 0.0
        self._using_simulated_feed = False

    def start(self) -> bool:
        """Initialize video capture and start background worker thread."""
        with self._lock:
            if self._running:
                return True

            self._cap = None
            self._using_simulated_feed = False

            # Try multiple backends and indices
            backends_to_try = [
                (self.camera_index, getattr(cv2, "CAP_DSHOW", 700)),
                (self.camera_index, getattr(cv2, "CAP_MSMF", 1400)),
                (self.camera_index, getattr(cv2, "CAP_ANY", 0)),
                (1, getattr(cv2, "CAP_DSHOW", 700)),
                (1, getattr(cv2, "CAP_ANY", 0)),
            ]

            for idx, backend in backends_to_try:
                try:
                    cap = cv2.VideoCapture(idx, backend) if backend != 0 else cv2.VideoCapture(idx)
                    if cap is not None and cap.isOpened():
                        # Configure camera hardware properties for high FPS
                        try:
                            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                            cap.set(cv2.CAP_PROP_FPS, self.target_fps)
                        except Exception:
                            pass

                        # Test reading a single frame
                        ret, test_frame = cap.read()
                        if ret and test_frame is not None:
                            self._cap = cap
                            print(f"[OpenCVCamera] Connected to camera index {idx} with backend {backend}")
                            break
                        else:
                            cap.release()
                except Exception:
                    pass

            if self._cap is None or not self._cap.isOpened():
                print("[OpenCVCamera] Warning: Physical webcam not accessible. Initializing Simulated Live Demo Feed...")
                self._using_simulated_feed = True
                self._latest_frame = self._generate_simulated_frame(0)
                self._frame_ready = True

            self._running = True
            self._frame_count = 0
            self._fps_start_time = time.time()
            self._current_fps = float(self.target_fps)

            self._thread = threading.Thread(target=self._capture_worker, daemon=True)
            self._thread.start()
            mode = "Simulated Demo Feed" if self._using_simulated_feed else f"Webcam ({self.width}x{self.height})"
            print(f"[OpenCVCamera] Camera engine started [{mode}] @ {self.target_fps} FPS")
            return True

    def _capture_worker(self) -> None:
        """Background capture loop with zero frame buffering."""
        last_frame_time = 0.0
        anim_step = 0

        while self._running:
            now = time.time()
            elapsed = now - last_frame_time

            # Rate-limiting to target FPS
            if elapsed < self.frame_interval:
                time.sleep(max(0.0005, self.frame_interval - elapsed))

            frame = None

            if not self._using_simulated_feed and self._cap is not None and self._cap.isOpened():
                try:
                    success, captured = self._cap.read()
                    if success and captured is not None:
                        # Mirror frame horizontally for natural front-camera interaction
                        frame = cv2.flip(captured, 1)
                except Exception:
                    frame = None

            # Generate synthetic animated frame if webcam unavailable
            if frame is None:
                frame = self._generate_simulated_frame(anim_step)
                anim_step += 1

            with self._lock:
                self._latest_frame = frame
                self._frame_ready = True
                self._frame_count += 1

                # Calculate smoothed FPS every 10 frames
                if self._frame_count % 10 == 0:
                    delta = time.time() - self._fps_start_time
                    if delta > 0:
                        self._current_fps = round(self._frame_count / delta, 1)

            last_frame_time = time.time()

    def _generate_simulated_frame(self, step: int) -> np.ndarray:
        """Generates an animated synthetic hand canvas for demonstration if webcam is offline."""
        canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        canvas[:] = (20, 22, 28)

        # Draw grid pattern
        for x in range(0, self.width, 40):
            cv2.line(canvas, (x, 0), (x, self.height), (30, 34, 42), 1)
        for y in range(0, self.height, 40):
            cv2.line(canvas, (0, y), (self.width, y), (30, 34, 42), 1)

        # Draw simulated moving hand guide
        t = step * 0.05
        cx = int(self.width / 2 + np.sin(t) * 120)
        cy = int(self.height / 2 + np.cos(t * 0.7) * 80)

        # Draw subtle hand silhouette
        cv2.circle(canvas, (cx, cy), 45, (45, 55, 70), -1)
        cv2.circle(canvas, (cx - 20, cy - 60), 12, (45, 55, 70), -1)
        cv2.circle(canvas, (cx, cy - 75), 12, (45, 55, 70), -1)
        cv2.circle(canvas, (cx + 20, cy - 60), 12, (45, 55, 70), -1)

        # Watermark text
        cv2.putText(canvas, "GESTURE FLOW - CAMERA ACTIVE", (20, self.height - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 150, 200), 1, cv2.LINE_AA)
        return canvas

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Fetch a copy of the latest captured frame."""
        with self._lock:
            if not self._running or self._latest_frame is None:
                return False, None
            return True, self._latest_frame.copy()

    def stop(self) -> None:
        """Stop worker and release camera capture device."""
        with self._lock:
            self._running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

        with self._lock:
            if self._cap:
                try:
                    self._cap.release()
                except Exception:
                    pass
                self._cap = None
            self._latest_frame = None
            self._frame_ready = False
            print("[OpenCVCamera] Camera stopped and released.")

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def get_fps(self) -> float:
        with self._lock:
            return self._current_fps
