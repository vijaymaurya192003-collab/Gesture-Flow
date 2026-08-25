"""
Integration Tests for FastAPI Backend Endpoints
Covers Auth (/auth/register, /auth/login, /auth/me), Gestures (/gestures),
Settings (/settings), Calibration (/calibration), Stats (/stats), Health, and Security.
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import db_manager

client = TestClient(app)


def setup_module():
    """Clear in-memory mock collections before testing."""
    db_manager._mock_users.clear()
    db_manager._mock_mappings.clear()
    db_manager._mock_settings.clear()
    db_manager._mock_calibration.clear()
    db_manager._mock_stats.clear()


def test_health_check_endpoint():
    """Verify /health returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Gesture Flow API"


def test_auth_register_and_login_flow():
    """Verify user registration, login, and JWT access token issuance."""
    test_email = "student@college.edu"
    test_password = "securepassword123"
    test_name = "Alex Johnson"

    # 1. Register User via /auth/register
    reg_res = client.post("/auth/register", json={
        "email": test_email,
        "password": test_password,
        "name": test_name
    })
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == test_email
    assert reg_data["user"]["name"] == test_name

    # 2. Duplicate registration rejection
    dup_res = client.post("/auth/register", json={
        "email": test_email,
        "password": test_password,
        "name": test_name
    })
    assert dup_res.status_code == 400

    # 3. Login
    login_res = client.post("/auth/login", json={
        "email": test_email,
        "password": test_password
    })
    assert login_res.status_code == 200
    login_data = login_res.json()
    token = login_data["access_token"]
    assert token is not None

    # 4. Fetch Profile via /auth/me with Bearer token
    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == test_email


def test_gesture_mappings_crud():
    """Verify custom mapping creation, retrieval, and reset via /gestures."""
    # Login as student
    login_res = client.post("/auth/login", json={
        "email": "student@college.edu",
        "password": "securepassword123"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Fetch initial mappings (should return defaults)
    get_res = client.get("/gestures", headers=headers)
    assert get_res.status_code == 200
    mappings = get_res.json()
    assert len(mappings) > 0

    # 2. Upsert custom mapping: Change PINCH to VOLUME_UP
    put_res = client.post("/gestures", headers=headers, json={
        "gesture": "PINCH",
        "action": "VOLUME_UP",
        "sensitivity": 1.5,
        "confidence_threshold": 0.80,
        "cooldown_ms": 350,
        "enabled": True
    })
    assert put_res.status_code == 201
    put_data = put_res.json()
    assert put_data["action"] == "VOLUME_UP"

    # 3. Verify updated mapping persistence
    verify_res = client.get("/gestures", headers=headers)
    assert verify_res.status_code == 200
    pinch_map = next(m for m in verify_res.json() if m["gesture"] == "PINCH")
    assert pinch_map["action"] == "VOLUME_UP"
    assert pinch_map["cooldown_ms"] == 350

    # 4. Reset mapping via DELETE
    del_res = client.delete("/gestures/PINCH", headers=headers)
    assert del_res.status_code == 204


def test_settings_and_calibration_endpoints():
    """Verify settings and calibration profiles."""
    login_res = client.post("/auth/login", json={
        "email": "student@college.edu",
        "password": "securepassword123"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Update Settings
    set_res = client.put("/settings", headers=headers, json={
        "theme": "midnight_blue",
        "camera_resolution": "1280x720",
        "target_fps": 60,
        "pointer_sensitivity": 1.5
    })
    assert set_res.status_code == 200
    set_data = set_res.json()
    assert set_data["target_fps"] == 60
    assert set_data["theme"] == "midnight_blue"

    # 2. Update Calibration Profile
    cal_res = client.put("/calibration", headers=headers, json={
        "pinch_threshold": 0.38,
        "hand_scale_baseline": 0.22,
        "confidence_threshold": 0.85,
        "jitter_deadband": 0.015
    })
    assert cal_res.status_code == 200
    cal_data = cal_res.json()
    assert cal_data["pinch_threshold"] == 0.38
    assert cal_data["jitter_deadband"] == 0.015


def test_invalid_bearer_token_rejected():
    """Verify that unauthorized requests or invalid JWT tokens return 401."""
    res = client.get("/auth/me", headers={"Authorization": "Bearer invalid_malformed_token"})
    assert res.status_code == 401


def test_unwhitelisted_action_rejected():
    """Verify that unwhitelisted shell or arbitrary actions are rejected with 400."""
    login_res = client.post("/auth/login", json={
        "email": "student@college.edu",
        "password": "securepassword123"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/gestures", headers=headers, json={
        "gesture": "PINCH",
        "action": "EXEC_MALICIOUS_SHELL_CMD",
        "sensitivity": 1.0,
        "confidence_threshold": 0.70,
        "cooldown_ms": 400,
        "enabled": True
    })
    assert res.status_code == 400
