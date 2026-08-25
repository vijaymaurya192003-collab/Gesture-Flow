"""
Mappings Screen
Allows users to view, edit, enable/disable, save, and reset gesture-to-action bindings.
Enforces safe action whitelist and persists to local SQLite + sync queue.
"""
try:
    from kivy.uix.screenmanager import Screen
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.gridlayout import GridLayout
    from kivy.uix.scrollview import ScrollView
    from kivy.uix.label import Label
    from kivy.uix.button import Button
    from kivy.uix.spinner import Spinner
    from kivy.uix.switch import Switch
    KIVY_AVAILABLE = True
except ImportError:
    Screen = object
    KIVY_AVAILABLE = False

from android.actions.action_registry import ActionRegistry
from android.models.gesture_models import GestureMappingItem
from android.config.constants import DEFAULT_GESTURE_MAPPINGS


class MappingsScreen(Screen if KIVY_AVAILABLE else object):
    """Gesture Mappings customizer screen."""

    def __init__(self, app_context, **kwargs):
        if KIVY_AVAILABLE:
            super().__init__(**kwargs)
        self.app = app_context
        self.name = "mappings"
        self._spinners = {}
        self._switches = {}
        self._status_banner = None

        if KIVY_AVAILABLE:
            self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", padding=10, spacing=8)

        # Header Title
        title_box = BoxLayout(size_hint_y=0.10, orientation="vertical")
        title = Label(text="Gesture Mappings", font_size="18sp", bold=True, size_hint_y=0.6)
        self._status_banner = Label(text="Configure safe actions for each gesture", font_size="12sp", color=(0.7, 0.7, 0.8, 1), size_hint_y=0.4)
        title_box.add_widget(title)
        title_box.add_widget(self._status_banner)
        root.add_widget(title_box)

        # Scrollable Mappings Table
        scroll = ScrollView(size_hint_y=0.76)
        self.grid = GridLayout(cols=1, spacing=8, size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter('height'))

        scroll.add_widget(self.grid)
        root.add_widget(scroll)

        # Bottom Button Bar
        btn_bar = BoxLayout(size_hint_y=0.14, spacing=10)
        btn_save = Button(text="Save Mappings", background_color=(0.2, 0.7, 0.3, 1), bold=True)
        btn_save.bind(on_press=self._save_mappings)

        btn_reset = Button(text="Reset Defaults", background_color=(0.5, 0.5, 0.6, 1))
        btn_reset.bind(on_press=self._reset_defaults)

        btn_bar.add_widget(btn_save)
        btn_bar.add_widget(btn_reset)
        root.add_widget(btn_bar)

        self.add_widget(root)

    def on_enter(self):
        """Populate mappings on screen enter."""
        self._populate_mappings()

    def _populate_mappings(self):
        if not KIVY_AVAILABLE:
            return
        self.grid.clear_widgets()
        self._spinners.clear()
        self._switches.clear()

        safe_actions = ActionRegistry.list_all_actions()
        current_mappings = self.app.storage.load_mappings()

        for g_name in sorted(DEFAULT_GESTURE_MAPPINGS.keys()):
            current_item = current_mappings.get(g_name)
            current_action = current_item.action if current_item else DEFAULT_GESTURE_MAPPINGS[g_name]["action"]
            is_enabled = current_item.enabled if current_item else True

            row = BoxLayout(size_hint_y=None, height=44, spacing=6, padding=4)
            lbl = Label(text=g_name, size_hint_x=0.40, font_size="13sp", bold=True, halign="left")
            
            spin = Spinner(
                text=current_action,
                values=safe_actions,
                size_hint_x=0.45,
                font_size="11sp"
            )
            self._spinners[g_name] = spin

            sw = Switch(active=is_enabled, size_hint_x=0.15)
            self._switches[g_name] = sw

            row.add_widget(lbl)
            row.add_widget(spin)
            row.add_widget(sw)
            self.grid.add_widget(row)

    def _save_mappings(self, instance):
        """Save edited mappings to SQLite and queue cloud synchronization."""
        saved_count = 0
        current_mappings = self.app.storage.load_mappings()

        for g_name, spinner in self._spinners.items():
            selected_action = spinner.text
            is_enabled = self._switches[g_name].active

            if not ActionRegistry.is_safe(selected_action):
                continue

            existing = current_mappings.get(g_name)
            item = GestureMappingItem(
                gesture=g_name,
                action=selected_action,
                sensitivity=existing.sensitivity if existing else 1.0,
                confidence_threshold=existing.confidence_threshold if existing else 0.70,
                cooldown_ms=existing.cooldown_ms if existing else 400,
                enabled=is_enabled,
                description=f"Mapped to {selected_action}"
            )
            self.app.storage.save_mapping(item)
            self.app.storage.enqueue_sync(
                endpoint="/mappings",
                method="POST",
                payload=item.model_dump()
            )
            saved_count += 1

        # Reload mappings into dispatcher
        self.app.dispatcher.set_mappings(self.app.storage.load_mappings())
        if self._status_banner:
            self._status_banner.text = f"Saved {saved_count} mappings to local storage & sync queue."
            self._status_banner.color = (0.3, 1.0, 0.4, 1)

    def _reset_defaults(self, instance):
        """Reset mappings to system defaults."""
        for g_name, data in DEFAULT_GESTURE_MAPPINGS.items():
            item = GestureMappingItem(
                gesture=g_name,
                action=data["action"],
                sensitivity=data["sensitivity"],
                confidence_threshold=data["confidence_threshold"],
                cooldown_ms=data["cooldown_ms"],
                enabled=data["enabled"],
                description=data.get("description", "")
            )
            self.app.storage.save_mapping(item)
            self.app.storage.enqueue_sync(
                endpoint="/mappings",
                method="POST",
                payload=item.model_dump()
            )

        self.app.dispatcher.set_mappings(self.app.storage.load_mappings())
        self._populate_mappings()
        if self._status_banner:
            self._status_banner.text = "Reset all mappings to default."
            self._status_banner.color = (0.4, 0.8, 1.0, 1)

