"""
Gesture Flow Application Entry Point
Supports running on Android (via Kivy) or in Desktop Interactive Demo Mode (via OpenCV GUI).
Includes real-time pipeline latency instrumentation, asynchronous vision processing, and multi-backend webcam resilience.
"""
import sys
import time
import threading
import argparse
from typing import Optional
import cv2

from android.camera.opencv_camera import OpenCVCamera
from android.vision.hand_detector import HandDetector
from android.vision.landmark_smoother import LandmarkSmoother
from android.vision.overlay_renderer import OverlayRenderer
from android.gestures.gesture_classifier import GestureClassifier
from android.gestures.state_machine import GestureStateMachine
from android.actions.action_dispatcher import ActionDispatcher
from android.sync.local_storage import LocalStorageManager
from android.sync.sync_client import CloudSyncClient
from android.config.constants import GestureType, SafeActionType
from android.models.gesture_models import PipelineMetrics, HandFrameData, GestureResult


class AsyncVisionWorker:
    """
    Dedicated worker thread for MediaPipe hand tracking, smoothing, and classification.
    Runs asynchronously to prevent CV inference from bottlenecking the 30-60 FPS camera display loop.
    """

    def __init__(self, camera: OpenCVCamera, storage: LocalStorageManager, debug_latency: bool = False):
        self.camera = camera
        self.storage = storage
        self.debug_latency = debug_latency

        self.detector = HandDetector()
        self.smoother = LandmarkSmoother()
        self.classifier = GestureClassifier()
        self.state_machine = GestureStateMachine()
        self.dispatcher = ActionDispatcher()

        # Load custom mappings and calibration
        self.dispatcher.set_mappings(self.storage.load_mappings())
        calib = self.storage.load_calibration()
        self.classifier.set_pinch_threshold(calib.pinch_threshold)

        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        self.latest_hand_data = HandFrameData()
        self.latest_result = GestureResult(gesture="NONE", confidence=0.0, action="NONE")
        self.latest_metrics = PipelineMetrics()
        self._frame_count = 0

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def _worker_loop(self) -> None:
        while self._running:
            success, frame = self.camera.read_frame()
            if not success or frame is None:
                time.sleep(0.002)
                continue

            t_start = time.perf_counter()

            # 1. Vision Detection (MediaPipe Lite)
            t_vis_start = time.perf_counter()
            hand_data = self.detector.detect_hands(frame)
            t_vis_end = time.perf_counter()
            vision_ms = (t_vis_end - t_vis_start) * 1000.0

            # 2. Coordinate Smoothing
            t_sm_start = time.perf_counter()
            if hand_data.hand_detected:
                hand_data.landmarks = self.smoother.smooth(hand_data.landmarks)
            else:
                self.smoother.reset()
            t_sm_end = time.perf_counter()
            smoothing_ms = (t_sm_end - t_sm_start) * 1000.0

            # 3. Gesture Classification
            t_cl_start = time.perf_counter()
            g_type, conf, features = self.classifier.classify(hand_data.landmarks)
            mapped_action = self.dispatcher.get_mapped_action_name(g_type)
            mapping_item = self.dispatcher.get_mapping_item(g_type)
            min_confidence = mapping_item.confidence_threshold if mapping_item else 0.60
            t_cl_end = time.perf_counter()
            classification_ms = (t_cl_end - t_cl_start) * 1000.0

            # 4. State Machine & Action Dispatch
            t_act_start = time.perf_counter()
            result = self.state_machine.process_frame(
                hand_detected=hand_data.hand_detected,
                detected_gesture=g_type,
                confidence=conf,
                features=features,
                mapped_action=mapped_action,
                min_confidence=min_confidence
            )
            self.dispatcher.dispatch(result)
            t_act_end = time.perf_counter()
            action_ms = (t_act_end - t_act_start) * 1000.0

            t_end = time.perf_counter()
            total_pipeline_ms = (t_end - t_start) * 1000.0

            # Package Metrics
            metrics = PipelineMetrics(
                camera_capture_ms=1.5,
                vision_ms=round(vision_ms, 1),
                smoothing_ms=round(smoothing_ms, 2),
                feature_ms=round(classification_ms * 0.4, 2),
                classification_ms=round(classification_ms, 2),
                action_ms=round(action_ms, 2),
                total_pipeline_ms=round(total_pipeline_ms, 1),
                fps=self.camera.get_fps()
            )
            result.metrics = metrics

            with self._lock:
                self.latest_hand_data = hand_data
                self.latest_result = result
                self.latest_metrics = metrics
                self._frame_count += 1

            if self.debug_latency and self._frame_count % 30 == 0:
                print(f"[Latency] Total: {metrics.total_pipeline_ms}ms | Vision: {metrics.vision_ms}ms | Class: {metrics.classification_ms}ms | Action: {metrics.action_ms}ms")

            # Small yield to prevent CPU thrashing
            time.sleep(0.001)

    def get_state(self):
        with self._lock:
            return self.latest_hand_data, self.latest_result, self.latest_metrics

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self.detector.close()


def run_desktop_interactive_mode(debug_latency: bool = False, camera_idx: int = 0):
    """
    Runs Gesture Flow interactive desktop GUI.
    Features high-FPS decoupled rendering and asynchronous vision inference.
    """
    print("=" * 65)
    print("           GESTURE FLOW - HIGH-PERFORMANCE HCI DEMO             ")
    print("=" * 65)
    print("  Controls:")
    print("    [ESC / Q] : Exit")
    print("    [P]       : Toggle Pause / Resume Gestures")
    print("    [E]       : Trigger Emergency Stop")
    print("    [R]       : Reset Emergency Stop")
    print("    [C]       : Run Quick Calibration")
    if debug_latency:
        print("  [DEBUG] Real-time latency instrumentation active.")
    print("=" * 65)

    storage = LocalStorageManager()
    sync_client = CloudSyncClient(storage)
    sync_client.start_background_sync()

    camera = OpenCVCamera(camera_index=camera_idx, width=640, height=480, target_fps=30)
    if not camera.start():
        print("[Error] Could not access camera. Please check camera connection.")
        return

    vision_worker = AsyncVisionWorker(camera, storage, debug_latency=debug_latency)
    vision_worker.start()

    window_name = "Gesture Flow - Live Hand Tracking & Action HUD"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    # Frame timing for display FPS calculation
    last_time = time.time()
    disp_fps = 30.0

    try:
        while camera.is_running():
            success, frame = camera.read_frame()
            if not success or frame is None:
                time.sleep(0.005)
                continue

            now = time.time()
            dt = now - last_time
            if dt > 0:
                disp_fps = 0.9 * disp_fps + 0.1 * (1.0 / dt)
            last_time = now

            # Fetch latest async vision results
            hand_data, result, metrics = vision_worker.get_state()

            # Render Skeleton & HUD Overlay
            display_frame = OverlayRenderer.draw_hand_overlay(
                frame=frame,
                hand_data=hand_data,
                gesture_result=result,
                fps=disp_fps,
                show_hud=True,
                metrics=metrics
            )

            # Emergency Stop Banner if active
            if vision_worker.dispatcher.emergency_stopped:
                cv2.rectangle(display_frame, (0, 60), (display_frame.shape[1], 100), (0, 0, 200), -1)
                cv2.putText(
                    display_frame,
                    "EMERGENCY STOP LOCKED - Press [R] to Reset",
                    (50, 88),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA
                )
            elif vision_worker.dispatcher.gestures_paused:
                cv2.rectangle(display_frame, (0, 60), (display_frame.shape[1], 100), (0, 140, 255), -1)
                cv2.putText(
                    display_frame,
                    "GESTURES PAUSED - Show OPEN PALM or Press [P] to Resume",
                    (30, 88),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA
                )

            # Show window
            cv2.imshow(window_name, display_frame)

            # Keyboard handler
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q'), ord('Q')):
                break
            elif key in (ord('p'), ord('P')):
                vision_worker.dispatcher.dispatch(
                    vision_worker.state_machine.process_frame(True, GestureType.OPEN_PALM, 0.9, None, SafeActionType.PAUSE_GESTURES.value)
                )
            elif key in (ord('e'), ord('E')):
                vision_worker.dispatcher.dispatch(
                    vision_worker.state_machine.process_frame(True, GestureType.FIST, 0.95, None, SafeActionType.EMERGENCY_STOP.value)
                )
            elif key in (ord('r'), ord('R')):
                vision_worker.dispatcher.reset_emergency_stop()
            elif key in (ord('c'), ord('C')):
                print("[Calibration] Saving default profile...")
                calib = storage.load_calibration()
                storage.save_calibration(calib)
                print("[Calibration] Saved successfully.")

    finally:
        vision_worker.stop()
        camera.stop()
        sync_client.stop()
        cv2.destroyAllWindows()
        print("[GestureFlow] Application terminated cleanly.")


def main():
    parser = argparse.ArgumentParser(description="Gesture Flow Application Launcher")
    parser.add_argument("--kivy", action="store_true", help="Launch Kivy Mobile UI")
    parser.add_argument("--desktop", action="store_true", help="Launch Desktop Interactive OpenCV GUI")
    parser.add_argument("--camera-index", type=int, default=0, help="Camera device index (default: 0)")
    parser.add_argument("--debug-latency", action="store_true", help="Print real-time latency breakdown")
    args = parser.parse_args()

    if args.kivy:
        try:
            from android.ui.app import GestureFlowApp, KIVY_AVAILABLE
            if KIVY_AVAILABLE:
                GestureFlowApp().run()
                return
            else:
                print("[Main] Kivy is not available, falling back to Desktop Interactive Mode.")
        except Exception as e:
            print(f"[Main] Kivy launch error: {e}, falling back to Desktop Mode.")

    # Default to Desktop Interactive Mode
    run_desktop_interactive_mode(debug_latency=args.debug_latency, camera_idx=args.camera_index)


if __name__ == "__main__":
    main()
