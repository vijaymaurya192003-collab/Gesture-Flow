"""
Dashboard Screen
Main camera viewfinder with real-time gesture HUD, tracking controls, and AccessibilityService status.
"""
try:
    from kivy.uix.screenmanager import Screen
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.gridlayout import GridLayout
    from kivy.uix.image import Image
    from kivy.uix.label import Label
    from kivy.uix.button import Button
    from kivy.uix.togglebutton import ToggleButton
    KIVY_AVAILABLE = True
except ImportError:
    Screen = object
    KIVY_AVAILABLE = False

from android.android.accessibility import AndroidAccessibilityBridge
from android.config.constants import GestureType, SafeActionType


class DashboardScreen(Screen if KIVY_AVAILABLE else object):
    """Main live camera viewfinder and real-time gesture HUD screen."""

    def __init__(self, app_context, **kwargs):
        if KIVY_AVAILABLE:
            super().__init__(**kwargs)
        self.app = app_context
        self.name = "dashboard"

        self.image_widget = None
        self.fps_label = None
        self.gesture_label = None
        self.confidence_label = None
        self.action_label = None
        self.service_status_btn = None
        self.btn_emergency = None

        if KIVY_AVAILABLE:
            self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", padding=8, spacing=8)

        # 1. Top Status & Telemetry Header
        header = BoxLayout(orientation="vertical", size_hint_y=0.15, spacing=4)
        
        row1 = BoxLayout(spacing=8)
        self.fps_label = Label(text="FPS: 0.0", size_hint_x=0.25, font_size="14sp", bold=True)
        self.gesture_label = Label(text="Gesture: NONE", size_hint_x=0.45, font_size="15sp", bold=True, color=(0.2, 0.8, 1, 1))
        self.confidence_label = Label(text="Conf: 0%", size_hint_x=0.30, font_size="14sp", color=(0.7, 0.9, 0.7, 1))
        row1.add_widget(self.fps_label)
        row1.add_widget(self.gesture_label)
        row1.add_widget(self.confidence_label)
        header.add_widget(row1)

        row2 = BoxLayout(spacing=8)
        self.action_label = Label(text="Action: IDLE", size_hint_x=0.5, font_size="13sp", color=(1, 0.9, 0.4, 1))
        self.service_status_btn = Button(
            text="Service: Checking...",
            size_hint_x=0.5,
            font_size="11sp",
            background_color=(0.3, 0.3, 0.4, 1)
        )
        self.service_status_btn.bind(on_press=self._on_service_button_click)
        row2.add_widget(self.action_label)
        row2.add_widget(self.service_status_btn)
        header.add_widget(row2)

        root.add_widget(header)

        # 2. Camera Viewfinder View
        self.image_widget = Image(size_hint_y=0.70, allow_stretch=True, keep_ratio=True)
        root.add_widget(self.image_widget)

        # 3. Quick Action Controls Panel
        controls = BoxLayout(size_hint_y=0.15, spacing=8)
        
        self.btn_toggle = ToggleButton(text="Camera: ON", state="down", size_hint_x=0.33)
        self.btn_toggle.bind(on_press=self._toggle_camera)

        btn_pause = Button(text="Pause / Resume", size_hint_x=0.33)
        btn_pause.bind(on_press=self._toggle_pause_gestures)

        self.btn_emergency = Button(
            text="EMERGENCY\nSTOP",
            background_color=(0.9, 0.2, 0.2, 1),
            size_hint_x=0.34,
            bold=True
        )
        self.btn_emergency.bind(on_press=self._toggle_emergency_stop)

        controls.add_widget(self.btn_toggle)
        controls.add_widget(btn_pause)
        controls.add_widget(self.btn_emergency)
        root.add_widget(controls)

        self.add_widget(root)

    def on_enter(self):
        """Screen entered callback."""
        self.update_service_status()

    def update_service_status(self):
        """Refresh Accessibility Service status indicator."""
        if not self.service_status_btn:
            return
        if AndroidAccessibilityBridge.is_service_enabled():
            self.service_status_btn.text = "Service: ACTIVE"
            self.service_status_btn.background_color = (0.2, 0.7, 0.3, 1)
        else:
            self.service_status_btn.text = "Enable Accessibility >"
            self.service_status_btn.background_color = (0.8, 0.4, 0.1, 1)

    def _on_service_button_click(self, instance):
        """Direct user to Android Settings to enable the service."""
        if not AndroidAccessibilityBridge.is_service_enabled():
            opened = AndroidAccessibilityBridge.open_accessibility_settings()
            if not opened:
                print("[Dashboard] Open Accessibility Settings requested (desktop simulated).")

    def _toggle_camera(self, instance):
        if instance.state == "down":
            instance.text = "Camera: ON"
            self.app.camera.start()
        else:
            instance.text = "Camera: OFF"
            self.app.camera.stop()

    def _toggle_pause_gestures(self, instance):
        self.app.dispatcher.dispatch(
            self.app.state_machine.process_frame(
                True, GestureType.OPEN_PALM, 0.9, None, SafeActionType.PAUSE_GESTURES.value
            )
        )

    def _toggle_emergency_stop(self, instance):
        if self.app.dispatcher.emergency_stopped:
            self.app.dispatcher.reset_emergency_stop()
            instance.text = "EMERGENCY\nSTOP"
            instance.background_color = (0.9, 0.2, 0.2, 1)
        else:
            self.app.dispatcher.emergency_stopped = True
            instance.text = "UNLOCK\nACTIONS"
            instance.background_color = (0.2, 0.7, 0.2, 1)

