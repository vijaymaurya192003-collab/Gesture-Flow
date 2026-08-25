"""
Settings Screen
Provides configurable options for camera index, confidence thresholds, smoothing parameters,
AccessibilityService system launcher, and cloud synchronization controls.
"""
try:
    from kivy.uix.screenmanager import Screen
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.gridlayout import GridLayout
    from kivy.uix.scrollview import ScrollView
    from kivy.uix.label import Label
    from kivy.uix.button import Button
    from kivy.uix.slider import Slider
    from kivy.uix.textinput import TextInput
    from kivy.uix.switch import Switch
    KIVY_AVAILABLE = True
except ImportError:
    Screen = object
    KIVY_AVAILABLE = False

from android.models.settings_models import UserSettingsModel
from android.android.accessibility import AndroidAccessibilityBridge


class SettingsScreen(Screen if KIVY_AVAILABLE else object):
    """Application preferences and cloud synchronization settings."""

    def __init__(self, app_context, **kwargs):
        if KIVY_AVAILABLE:
            super().__init__(**kwargs)
        self.app = app_context
        self.name = "settings"

        self.current_settings = UserSettingsModel()
        self.slider_sens = None
        self.lbl_sens_val = None
        self.slider_scroll = None
        self.lbl_scroll_val = None
        self.switch_overlay = None
        self.switch_vibrate = None
        self.txt_api_url = None
        self.lbl_sync_status = None
        self.lbl_service_status = None

        if KIVY_AVAILABLE:
            self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", padding=10, spacing=8)

        # Header Title
        title = Label(text="Application Settings", font_size="18sp", bold=True, size_hint_y=0.08)
        root.add_widget(title)

        # Scrollable Settings Container
        scroll = ScrollView(size_hint_y=0.78)
        content = BoxLayout(orientation="vertical", spacing=12, size_hint_y=None, padding=6)
        content.bind(minimum_height=content.setter('height'))

        # Section 1: Accessibility Service
        sec1 = BoxLayout(orientation="vertical", size_hint_y=None, height=90, spacing=4)
        sec1_title = Label(text="Android Accessibility Service", font_size="14sp", bold=True, halign="left", size_hint_y=0.3)
        self.lbl_service_status = Label(
            text="Status: " + AndroidAccessibilityBridge.get_service_status_text(),
            font_size="12sp",
            color=(0.3, 0.8, 1, 1),
            size_hint_y=0.3
        )
        btn_open_settings = Button(
            text="Open Android Accessibility Settings",
            background_color=(0.2, 0.5, 0.8, 1),
            size_hint_y=0.4
        )
        btn_open_settings.bind(on_press=self._open_accessibility_settings)
        sec1.add_widget(sec1_title)
        sec1.add_widget(self.lbl_service_status)
        sec1.add_widget(btn_open_settings)
        content.add_widget(sec1)

        # Section 2: Pointer & Gesture Tuning
        sec2 = BoxLayout(orientation="vertical", size_hint_y=None, height=130, spacing=6)
        sec2_title = Label(text="Pointer & Scroll Tuning", font_size="14sp", bold=True, size_hint_y=0.25)
        
        row_sens = BoxLayout(size_hint_y=0.35, spacing=8)
        self.lbl_sens_val = Label(text="Pointer Sensitivity: 1.2x", size_hint_x=0.45, font_size="12sp")
        self.slider_sens = Slider(min=0.5, max=3.0, value=1.2, step=0.1, size_hint_x=0.55)
        self.slider_sens.bind(value=lambda _, val: setattr(self.lbl_sens_val, 'text', f"Pointer Sensitivity: {val:.1f}x"))
        row_sens.add_widget(self.lbl_sens_val)
        row_sens.add_widget(self.slider_sens)

        row_scroll = BoxLayout(size_hint_y=0.35, spacing=8)
        self.lbl_scroll_val = Label(text="Scroll Sensitivity: 1.0x", size_hint_x=0.45, font_size="12sp")
        self.slider_scroll = Slider(min=0.5, max=3.0, value=1.0, step=0.1, size_hint_x=0.55)
        self.slider_scroll.bind(value=lambda _, val: setattr(self.lbl_scroll_val, 'text', f"Scroll Sensitivity: {val:.1f}x"))
        row_scroll.add_widget(self.lbl_scroll_val)
        row_scroll.add_widget(self.slider_scroll)

        sec2.add_widget(sec2_title)
        sec2.add_widget(row_sens)
        sec2.add_widget(row_scroll)
        content.add_widget(sec2)

        # Section 3: Feedback & Display
        sec3 = BoxLayout(orientation="vertical", size_hint_y=None, height=90, spacing=6)
        sec3_title = Label(text="Feedback & Visuals", font_size="14sp", bold=True, size_hint_y=0.3)
        
        row_fb = BoxLayout(size_hint_y=0.7, spacing=10)
        lbl_vibe = Label(text="Haptic Vibration", font_size="12sp", size_hint_x=0.35)
        self.switch_vibrate = Switch(active=True, size_hint_x=0.15)
        lbl_hud = Label(text="HUD Landmarks", font_size="12sp", size_hint_x=0.35)
        self.switch_overlay = Switch(active=True, size_hint_x=0.15)
        row_fb.add_widget(lbl_vibe)
        row_fb.add_widget(self.switch_vibrate)
        row_fb.add_widget(lbl_hud)
        row_fb.add_widget(self.switch_overlay)

        sec3.add_widget(sec3_title)
        sec3.add_widget(row_fb)
        content.add_widget(sec3)

        # Section 4: Cloud Sync
        sec4 = BoxLayout(orientation="vertical", size_hint_y=None, height=120, spacing=6)
        sec4_title = Label(text="Cloud Synchronization", font_size="14sp", bold=True, size_hint_y=0.25)
        
        row_url = BoxLayout(size_hint_y=0.35, spacing=8)
        lbl_url = Label(text="API URL:", size_hint_x=0.25, font_size="12sp")
        self.txt_api_url = TextInput(text="https://gestureflow-backend.onrender.com", size_hint_x=0.75, multiline=False)
        row_url.add_widget(lbl_url)
        row_url.add_widget(self.txt_api_url)

        row_sync = BoxLayout(size_hint_y=0.40, spacing=8)
        self.lbl_sync_status = Label(text="Sync Status: Local SQLite Active", font_size="12sp", size_hint_x=0.65, color=(0.7, 0.9, 0.7, 1))
        btn_sync_now = Button(text="Sync Now", size_hint_x=0.35, background_color=(0.2, 0.6, 0.8, 1))
        btn_sync_now.bind(on_press=self._manual_sync)
        row_sync.add_widget(self.lbl_sync_status)
        row_sync.add_widget(btn_sync_now)

        sec4.add_widget(sec4_title)
        sec4.add_widget(row_url)
        sec4.add_widget(row_sync)
        content.add_widget(sec4)

        scroll.add_widget(content)
        root.add_widget(scroll)

        # Bottom Button Bar
        btn_bar = BoxLayout(size_hint_y=0.14, spacing=10)
        btn_save = Button(text="Save Settings", background_color=(0.2, 0.7, 0.3, 1), bold=True)
        btn_save.bind(on_press=self._save_settings)

        btn_reset = Button(text="Reset Defaults", background_color=(0.5, 0.5, 0.6, 1))
        btn_reset.bind(on_press=self._reset_defaults)

        btn_bar.add_widget(btn_save)
        btn_bar.add_widget(btn_reset)
        root.add_widget(btn_bar)

        self.add_widget(root)

    def on_enter(self):
        """Load settings on enter."""
        loaded = self.app.storage.load_settings()
        if loaded:
            self.current_settings = loaded
            self._apply_to_ui()
        if self.lbl_service_status:
            self.lbl_service_status.text = "Status: " + AndroidAccessibilityBridge.get_service_status_text()

    def _apply_to_ui(self):
        if not KIVY_AVAILABLE:
            return
        if self.slider_sens:
            self.slider_sens.value = self.current_settings.pointer_sensitivity
        if self.slider_scroll:
            self.slider_scroll.value = self.current_settings.scroll_sensitivity
        if self.switch_vibrate:
            self.switch_vibrate.active = self.current_settings.vibration_feedback
        if self.switch_overlay:
            self.switch_overlay.active = self.current_settings.show_landmark_overlay

    def _open_accessibility_settings(self, instance):
        AndroidAccessibilityBridge.open_accessibility_settings()

    def _manual_sync(self, instance):
        if hasattr(self.app, 'sync_client'):
            synced = self.app.sync_client.sync_now()
            if self.lbl_sync_status:
                self.lbl_sync_status.text = "Sync: Success" if synced else "Sync: Offline / Queued"

    def _save_settings(self, instance):
        if self.slider_sens:
            self.current_settings.pointer_sensitivity = round(self.slider_sens.value, 2)
        if self.slider_scroll:
            self.current_settings.scroll_sensitivity = round(self.slider_scroll.value, 2)
        if self.switch_vibrate:
            self.current_settings.vibration_feedback = self.switch_vibrate.active
        if self.switch_overlay:
            self.current_settings.show_landmark_overlay = self.switch_overlay.active

        self.app.storage.save_settings(self.current_settings)
        self.app.storage.enqueue_sync(
            endpoint="/settings",
            method="PUT",
            payload=self.current_settings.model_dump()
        )
        if self.lbl_sync_status:
            self.lbl_sync_status.text = "Settings saved & queued for cloud sync."

    def _reset_defaults(self, instance):
        self.current_settings = UserSettingsModel()
        self._apply_to_ui()
        self.app.storage.save_settings(self.current_settings)

