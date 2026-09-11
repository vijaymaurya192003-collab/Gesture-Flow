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


def test_put_mapping_conflicting_body_gesture_rejected_regression():
    """Regression test #4: PUT /mappings/{gesture} with different body gesture returns 400 and preserves original."""
    login_res = client.post("/auth/login", json={
        "email": "student@college.edu",
        "password": "securepassword123"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # First set PINCH to TAP
    init_res = client.post("/mappings", headers=headers, json={
        "gesture": "PINCH",
        "action": "TAP",
        "sensitivity": 1.0,
        "confidence_threshold": 0.70,
        "cooldown_ms": 400,
        "enabled": True
    })
    assert init_res.status_code == 201

    # Attempt PUT /mappings/PINCH with conflicting body gesture "FIST"
    put_res = client.put("/mappings/PINCH", headers=headers, json={
        "gesture": "FIST",
        "action": "VOLUME_UP",
        "sensitivity": 1.0,
        "confidence_threshold": 0.70,
        "cooldown_ms": 400,
        "enabled": True
    })
    assert put_res.status_code == 400
    assert "Conflicting resource identifiers" in put_res.json()["detail"]

    # Confirm PINCH mapping was NOT modified
    verify_res = client.get("/mappings", headers=headers)
    assert verify_res.status_code == 200
    pinch_map = next(m for m in verify_res.json() if m["gesture"] == "PINCH")
    assert pinch_map["action"] == "TAP"


def test_stats_summary_last_active_true_max_out_of_order_regression():
    """Regression test #5: Stats summary last_active returns true max across out-of-order records."""
    from datetime import datetime, timezone, timedelta
    login_res = client.post("/auth/login", json={
        "email": "student@college.edu",
        "password": "securepassword123"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Clear mock stats for test
    db_manager._mock_stats.clear()

    base = datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc)
    t1 = base
    t2 = base + timedelta(hours=5)   # True latest
    t3 = base + timedelta(hours=2)   # Middle, but inserted last

    user_id = client.get("/auth/me", headers=headers).json()["user_id"]
    db_manager._mock_stats.append({
        "user_id": user_id,
        "session_duration_seconds": 10.0,
        "gesture_counts": {"PINCH": 1},
        "average_fps": 30.0,
        "platform": "desktop",
        "app_version": "1.0.0",
        "timestamp": t1
    })
    db_manager._mock_stats.append({
        "user_id": user_id,
        "session_duration_seconds": 20.0,
        "gesture_counts": {"PINCH": 2},
        "average_fps": 30.0,
        "platform": "desktop",
        "app_version": "1.0.0",
        "timestamp": t2  # MAX timestamp
    })
    db_manager._mock_stats.append({
        "user_id": user_id,
        "session_duration_seconds": 15.0,
        "gesture_counts": {"PINCH": 3},
        "average_fps": 30.0,
        "platform": "desktop",
        "app_version": "1.0.0",
        "timestamp": t3  # Inserted last, but earlier than t2
    })
    db_manager._mock_stats.append({
        "user_id": user_id,
        "session_duration_seconds": 5.0,
        "gesture_counts": {"PINCH": 1},
        "average_fps": 30.0,
        "platform": "desktop",
        "app_version": "1.0.0",
        "timestamp": "invalid-timestamp-string"
    })

    summary_res = client.get("/stats/summary", headers=headers)
    assert summary_res.status_code == 200
    summary_data = summary_res.json()
    assert summary_data["total_sessions"] == 4
    assert summary_data["last_active"] == t2.isoformat()


def test_production_environment_fails_loudly_on_unset_secrets_regression():
    """Regression test #1: BackendSettings fails loudly with clear error in production if secrets are unset."""
    import os
    from backend.config import BackendSettings

    orig_env = os.environ.get("ENVIRONMENT")
    orig_jwt = os.environ.get("JWT_SECRET")
    orig_mongo = os.environ.get("MONGODB_URI")
    try:
        os.environ["ENVIRONMENT"] = "production"
        os.environ["JWT_SECRET"] = "changeme_use_a_long_random_value"
        os.environ["MONGODB_URI"] = "mongodb+srv://<user>:<password>@<cluster>/"

        with pytest.raises(RuntimeError) as exc_info:
            BackendSettings()
        assert "Production startup failed" in str(exc_info.value)
    finally:
        if orig_env is not None:
            os.environ["ENVIRONMENT"] = orig_env
        else:
            os.environ.pop("ENVIRONMENT", None)
        if orig_jwt is not None:
            os.environ["JWT_SECRET"] = orig_jwt
        else:
            os.environ.pop("JWT_SECRET", None)
        if orig_mongo is not None:
            os.environ["MONGODB_URI"] = orig_mongo
        else:
            os.environ.pop("MONGODB_URI", None)


def test_cors_allowlist_no_regex_wildcard_bypass_regression():
    """Regression test #2: Verify random untrusted origin is NOT allowed by CORS."""
    res = client.options(
        "/health",
        headers={
            "Origin": "https://evil-untrusted-origin.com",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert res.headers.get("access-control-allow-origin") != "https://evil-untrusted-origin.com"
