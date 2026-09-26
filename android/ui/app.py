"""
Main Kivy Application for Gesture Flow
Provides the mobile Android touchless interface with multi-screen navigation:
- Dashboard (Live Camera Viewfinder & HUD)
- Mappings (Safe Action Binding Editor)
- Calibration (3-Step Biometric Wizard)
- Settings (Tuning, Accessibility Launcher & Cloud Sync)
"""
import os
import sys
from typing import Optional

try:
    import kivy
    from kivy.app import App
    from kivy.clock import Clock
    from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    KIVY_AVAILABLE = True
except ImportError:
    KIVY_AVAILABLE = False
    App = object
    ScreenManager = object

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
from android.ui.screens.dashboard_screen import DashboardScreen
from android.ui.screens.mappings_screen import MappingsScreen
from android.ui.screens.calibration_screen import CalibrationScreen
from android.ui.screens.settings_screen import SettingsScreen


class GestureFlowApp(App if KIVY_AVAILABLE else object):
    """
    Unified Gesture Flow Kivy Application.
    Maintains a single shared pipeline and application state across all screens.
    """

    def __init__(self, **kwargs):
        if KIVY_AVAILABLE:
            super().__init__(**kwargs)
        self.title = "Gesture Flow"

        # Shared Data & Sync Layer
        self.storage = LocalStorageManager()
        self.sync_client = CloudSyncClient(self.storage)

        # Shared Vision & Gesture Pipeline
        self.camera = OpenCVCamera()
        self.detector = HandDetector()
        self.smoother = LandmarkSmoother()
        self.classifier = GestureClassifier()
        self.state_machine = GestureStateMachine()
        self.dispatcher = ActionDispatcher()

        # Wire Initial Saved State
        self.dispatcher.set_mappings(self.storage.load_mappings())
        calib = self.storage.load_calibration()
        if calib:
            self.classifier.set_pinch_threshold(calib.pinch_threshold)

        self.screen_manager = None
        self.dashboard_screen = None
        self.mappings_screen = None
        self.calibration_screen = None
        self.settings_screen = None

    def build(self):
        """Construct the multi-screen Kivy UI layout with bottom navigation."""
        if not KIVY_AVAILABLE:
            print("[GestureFlowApp] Kivy is not installed in the environment.")
            return None

        root = BoxLayout(orientation="vertical")

        # 1. Screen Manager Container
        self.screen_manager = ScreenManager(transition=FadeTransition(duration=0.15))
        
        self.dashboard_screen = DashboardScreen(self)
        self.mappings_screen = MappingsScreen(self)
        self.calibration_screen = CalibrationScreen(self)
        self.settings_screen = SettingsScreen(self)

        self.screen_manager.add_widget(self.dashboard_screen)
        self.screen_manager.add_widget(self.mappings_screen)
        self.screen_manager.add_widget(self.calibration_screen)
        self.screen_manager.add_widget(self.settings_screen)

        root.add_widget(self.screen_manager)

        # 2. Bottom Tab Navigation Bar
        nav_bar = BoxLayout(size_hint_y=0.09, spacing=4, padding=4)
        
        # Using #FDC323 (Yellow) for the main tab
        btn_dash = Button(text="HUD / Camera", background_color=(0.99, 0.76, 0.14, 1.0), font_size="12sp", bold=True)
        btn_dash.bind(on_press=lambda _: self._switch_screen("dashboard"))

        # Using #00785D (Dark Green) for Mappings
        btn_map = Button(text="Mappings", background_color=(0.0, 0.47, 0.36, 1.0), font_size="12sp", color=(1, 1, 1, 1))
        btn_map.bind(on_press=lambda _: self._switch_screen("mappings"))

        # Using #32BFDB (Light Blue) for Calibration
        btn_calib = Button(text="Calibration", background_color=(0.20, 0.75, 0.86, 1.0), font_size="12sp", color=(0, 0, 0, 1))
        btn_calib.bind(on_press=lambda _: self._switch_screen("calibration"))

        # Using #539BA9 (Teal) for Settings
        btn_sett = Button(text="Settings", background_color=(0.33, 0.61, 0.66, 1.0), font_size="12sp", color=(1, 1, 1, 1))
        btn_sett.bind(on_press=lambda _: self._switch_screen("settings"))

        nav_bar.add_widget(btn_dash)
        nav_bar.add_widget(btn_map)
        nav_bar.add_widget(btn_calib)
        nav_bar.add_widget(btn_sett)

        root.add_widget(nav_bar)

        return root

    def _switch_screen(self, screen_name: str):
        if self.screen_manager:
            self.screen_manager.current = screen_name

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
        mapping_item = self.dispatcher.get_mapping_item(g_type)
        min_confidence = mapping_item.confidence_threshold if mapping_item else 0.60

        # 4. State Machine & Debounce
        result = self.state_machine.process_frame(
            hand_detected=hand_data.hand_detected,
            detected_gesture=g_type,
            confidence=conf,
            features=features,
            mapped_action=mapped_action,
            min_confidence=min_confidence
        )

        # 5. Dispatch Action
        self.dispatcher.dispatch(result)

        # 6. Render Overlays & Update HUD
        fps = self.camera.get_fps()
        annotated_frame = OverlayRenderer.draw_hand_overlay(
            frame=frame,
            hand_data=hand_data,
            gesture_result=result,
            fps=fps,
            show_hud=True
        )

        # 7. Update Dashboard Widgets if currently active
        if self.dashboard_screen and self.dashboard_screen.image_widget:
            tex = KivyTextureBridge.frame_to_kivy_texture(annotated_frame)
            if tex:
                self.dashboard_screen.image_widget.texture = tex

            if self.dashboard_screen.fps_label:
                self.dashboard_screen.fps_label.text = f"FPS: {fps:.1f}"
            if self.dashboard_screen.gesture_label:
                self.dashboard_screen.gesture_label.text = f"Gesture: {result.gesture}"
            if self.dashboard_screen.confidence_label:
                self.dashboard_screen.confidence_label.text = f"Conf: {int(result.confidence * 100)}%"
            if self.dashboard_screen.action_label:
                self.dashboard_screen.action_label.text = f"Action: {result.action}"
