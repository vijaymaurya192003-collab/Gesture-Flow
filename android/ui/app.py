"""
Main Kivy / KivyMD Application
Provides the mobile Android touchless interface with camera viewfinder HUD, settings, and calibration.
"""
import os
import sys
from typing import Optional

# Safe check for Kivy availability
try:
    import kivy
    from kivy.app import App
    from kivy.clock import Clock
    from kivy.uix.screenmanager import ScreenManager, Screen
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.image import Image
    from kivy.uix.label import Label
    from kivy.uix.button import Button
    from kivy.uix.togglebutton import ToggleButton
    from kivy.core.window import Window
    KIVY_AVAILABLE = True
except ImportError:
    KIVY_AVAILABLE = False
    App = object
    Screen = object

from android.camera.opencv_camera import OpenCVCamera
from android.camera.kivy_texture_bridge import KivyTextureBridge
from android.vision.hand_detector import HandDetector
from android.vision.landmark_smoother import LandmarkSmoother
from android.vision.overlay_renderer import OverlayRenderer
from android.gestures.gesture_classifier import GestureClassifier
from android.gestures.state_machine import GestureStateMachine
from android.actions.action_dispatcher import ActionDispatcher
from android.sync.local_storage import LocalStorageManager
from android.sync.sync_client import CloudSyncClient
from android.config.constants import GestureType, SafeActionType


class DashboardScreen(Screen):
    """Main camera viewfinder and real-time gesture HUD screen."""
    pass


class MappingsScreen(Screen):
    """Gesture-to-Action customization screen."""
    pass


class CalibrationScreen(Screen):
    """3-step hand geometry calibration wizard."""
    pass


class SettingsScreen(Screen):
    """Settings screen."""
    pass


class GestureFlowApp(App if KIVY_AVAILABLE else object):
    """
    Kivy Mobile Application for Gesture Flow.
    """

    def __init__(self, **kwargs):
        if KIVY_AVAILABLE:
            super().__init__(**kwargs)
        self.title = "Gesture Flow"
        self.storage = LocalStorageManager()
        self.sync_client = CloudSyncClient(self.storage)

        # Vision & Gesture Pipeline components
        self.camera = OpenCVCamera()
        self.detector = HandDetector()
        self.smoother = LandmarkSmoother()
        self.classifier = GestureClassifier()
        self.state_machine = GestureStateMachine()
        self.dispatcher = ActionDispatcher()

        # Wire custom mappings
        self.dispatcher.set_mappings(self.storage.load_mappings())
        calib = self.storage.load_calibration()
        self.classifier.set_pinch_threshold(calib.pinch_threshold)

        self._image_widget = None
        self._fps_label = None
        self._gesture_label = None
        self._status_label = None

    def build(self):
        """Construct the Kivy UI layout."""
        if not KIVY_AVAILABLE:
            print("[GestureFlowApp] Kivy is not installed in the environment.")
            return None

        # Build Main View Layout
        root = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Top Header Bar
        header = BoxLayout(size_hint_y=0.08, spacing=10)
        self._fps_label = Label(text="FPS: 0", size_hint_x=0.25, font_size="16sp", bold=True)
        self._gesture_label = Label(text="Gesture: NONE", size_hint_x=0.5, font_size="16sp", bold=True, color=(0.2, 0.8, 1, 1))
        self._status_label = Label(text="Local CV Active", size_hint_x=0.25, font_size="14sp", color=(0.5, 1, 0.5, 1))
        header.add_widget(self._fps_label)
        header.add_widget(self._gesture_label)
        header.add_widget(self._status_label)
        root.add_widget(header)

        # Camera Viewfinder View
        self._image_widget = Image(size_hint_y=0.78, allow_stretch=True, keep_ratio=True)
        root.add_widget(self._image_widget)

        # Bottom Control Panel
        controls = BoxLayout(size_hint_y=0.14, spacing=12)
        btn_toggle = ToggleButton(text="Tracking: ON", state='down', size_hint_x=0.33)
        btn_toggle.bind(on_press=self._toggle_tracking)

        btn_pause = Button(text="Pause / Resume", size_hint_x=0.33)
        btn_pause.bind(on_press=lambda x: self.dispatcher.dispatch(self.state_machine.process_frame(True, GestureType.OPEN_PALM, 0.9, None, SafeActionType.PAUSE_GESTURES.value)))

        btn_emergency = Button(text="EMERGENCY STOP", background_color=(0.9, 0.2, 0.2, 1), size_hint_x=0.34, bold=True)
        btn_emergency.bind(on_press=self._handle_emergency_stop)

        controls.add_widget(btn_toggle)
        controls.add_widget(btn_pause)
        controls.add_widget(btn_emergency)
        root.add_widget(controls)

        return root

    def on_start(self):
        """Lifecycle start hook."""
        if not KIVY_AVAILABLE:
            return
        self.camera.start()
        self.sync_client.start_background_sync()
        # Schedule update loop at 30 FPS
        Clock.schedule_interval(self.update_frame, 1.0 / 30.0)

    def on_stop(self):
        """Lifecycle stop hook."""
        if self.camera:
            self.camera.stop()
        if self.detector:
            self.detector.close()
        if self.sync_client:
            self.sync_client.stop()

    def update_frame(self, dt):
        """Main CV processing and rendering tick."""
        if not self.camera.is_running():
            return

        success, frame = self.camera.read_frame()
        if not success or frame is None:
            return

        # 1. Detect Landmarks locally
        hand_data = self.detector.detect_hands(frame)

        # 2. Smooth Coordinates
        if hand_data.hand_detected:
            hand_data.landmarks = self.smoother.smooth(hand_data.landmarks)

        # 3. Classify Gesture
        g_type, conf, features = self.classifier.classify(hand_data.landmarks)
        mapped_action = self.dispatcher.get_mapped_action_name(g_type)

        # 4. State Machine & Debounce
        result = self.state_machine.process_frame(
            hand_detected=hand_data.hand_detected,
            detected_gesture=g_type,
            confidence=conf,
            features=features,
            mapped_action=mapped_action
        )

        # 5. Dispatch Action
        self.dispatcher.dispatch(result)

        # 6. Render Overlays
        fps = self.camera.get_fps()
        annotated_frame = OverlayRenderer.draw_hand_overlay(
            frame=frame,
            hand_data=hand_data,
            gesture_result=result,
            fps=fps,
            show_hud=True
        )

        # 7. Update Kivy Texture
        if self._image_widget:
            tex = KivyTextureBridge.frame_to_kivy_texture(annotated_frame)
            if tex:
                self._image_widget.texture = tex

        if self._fps_label:
            self._fps_label.text = f"FPS: {fps:.1f}"
        if self._gesture_label:
            if result.gesture != "NONE":
                self._gesture_label.text = f"{result.gesture} -> {result.action}"
            else:
                self._gesture_label.text = "Searching..."

    def _toggle_tracking(self, instance):
        if instance.state == 'down':
            instance.text = "Tracking: ON"
            self.camera.start()
        else:
            instance.text = "Tracking: OFF"
            self.camera.stop()

    def _handle_emergency_stop(self, instance):
        if self.dispatcher.emergency_stopped:
            self.dispatcher.reset_emergency_stop()
            instance.text = "EMERGENCY STOP"
            instance.background_color = (0.9, 0.2, 0.2, 1)
        else:
            self.dispatcher.emergency_stopped = True
            instance.text = "UNLOCK ACTIONS"
            instance.background_color = (0.2, 0.7, 0.2, 1)

