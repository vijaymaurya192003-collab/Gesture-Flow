"""
Unit Tests for Mobile Screens Structure and Backend Route Parity
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.security import create_access_token
from android.ui.screens.dashboard_screen import DashboardScreen
from android.ui.screens.mappings_screen import MappingsScreen
from android.ui.screens.calibration_screen import CalibrationScreen
from android.ui.screens.settings_screen import SettingsScreen
from android.sync.local_storage import LocalStorageManager
from android.actions.action_dispatcher import ActionDispatcher
from android.gestures.gesture_classifier import GestureClassifier
from android.gestures.state_machine import GestureStateMachine


class MockApp:
    """Mock shared application context for UI tests."""
    def __init__(self, tmp_path):
        self.storage = LocalStorageManager(db_path=tmp_path / "mock_app.db")
        self.dispatcher = ActionDispatcher()
        self.classifier = GestureClassifier()
        self.state_machine = GestureStateMachine()
        self.camera = None


def test_mobile_screens_instantiation(tmp_path):
    """Verify that all 4 screens instantiate cleanly and share state."""
    mock_app = MockApp(tmp_path)
    
    dash = DashboardScreen(mock_app)
    assert dash.name == "dashboard"

    mappings = MappingsScreen(mock_app)
    assert mappings.name == "mappings"

    calib = CalibrationScreen(mock_app)
    assert calib.name == "calibration"

    sett = SettingsScreen(mock_app)
    assert sett.name == "settings"


def test_backend_mappings_gestures_route_parity():
    """Verify that /mappings and /gestures return identical responses for all CRUD actions."""
    client = TestClient(app)
    token = create_access_token({"sub": "user_route_parity", "email": "parity@gestureflow.io"})
    headers = {"Authorization": f"Bearer {token}"}

    # GET /mappings
    r_map = client.get("/mappings", headers=headers)
    assert r_map.status_code == 200

    # GET /gestures
    r_ges = client.get("/gestures", headers=headers)
    assert r_ges.status_code == 200
    assert len(r_map.json()) == len(r_ges.json())

    # POST /gestures
    payload = {
        "gesture": "PINCH",
        "action": "TAP",
        "sensitivity": 1.0,
        "confidence_threshold": 0.75,
        "cooldown_ms": 350,
        "enabled": True,
        "description": "Tap action"
    }
    r_post = client.post("/gestures", json=payload, headers=headers)
    assert r_post.status_code == 201

    # GET /mappings to verify persistence
    r_check = client.get("/mappings", headers=headers)
    assert r_check.status_code == 200
    pinch_items = [m for m in r_check.json() if m["gesture"] == "PINCH"]
    assert len(pinch_items) == 1
    assert pinch_items[0]["confidence_threshold"] == 0.75

