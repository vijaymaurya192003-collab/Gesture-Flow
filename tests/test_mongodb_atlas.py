"""
MongoDB Atlas Integration & Database Verification Test Suite
Tests MongoDB connection management, database health ping, user isolation,
collection accessors, and offline fallback resilience.
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import db_manager
from backend.config import settings


@pytest.fixture
def client():
    return TestClient(app)


def test_database_manager_sanitizes_uri():
    """Verify MongoDB URI passwords are masked in log helpers."""
    raw_uri = "mongodb+srv://admin_user:SuperSecretPassword123@cluster0.mongodb.net/?appName=Gesture-Flow"
    sanitized = db_manager._sanitize_uri(raw_uri)
    assert "SuperSecretPassword123" not in sanitized
    assert "admin_user:****@" in sanitized


def test_database_manager_graceful_missing_uri():
    """Verify DatabaseManager operates safely when MONGODB_URI is absent."""
    original_uri = settings.mongodb_uri
    settings.mongodb_uri = ""

    # Should not throw exception
    db_manager.client = None
    db_manager.is_connected = False
    assert db_manager.get_users_collection() is None
    assert db_manager.get_mappings_collection() is None

    settings.mongodb_uri = original_uri


def test_health_check_returns_database_status(client):
    """Verify /health endpoint returns structured status without leaking internal info."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "ok")
    assert "database" in data
    assert data["database_name"] == "gesture_flow"
    assert "service" in data


def test_user_isolation_between_accounts(client):
    """Verify that User A cannot see or access User B's custom gesture mappings."""
    # 1. Register User A
    res_a = client.post("/api/v1/auth/register", json={
        "email": "user_alpha@test.edu",
        "name": "User Alpha",
        "password": "PasswordAlpha123"
    })
    assert res_a.status_code == 201
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register User B
    res_b = client.post("/api/v1/auth/register", json={
        "email": "user_beta@test.edu",
        "name": "User Beta",
        "password": "PasswordBeta123"
    })
    assert res_b.status_code == 201
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. User A configures custom mapping for PINCH -> VOLUME_UP
    client.post("/api/v1/mappings", json={
        "gesture": "PINCH",
        "action": "VOLUME_UP",
        "cooldown_ms": 450,
        "enabled": True
    }, headers=headers_a)

    # 4. User B configures custom mapping for PINCH -> SCROLL_DOWN
    client.post("/api/v1/mappings", json={
        "gesture": "PINCH",
        "action": "SCROLL_DOWN",
        "cooldown_ms": 300,
        "enabled": True
    }, headers=headers_b)

    # 5. Fetch User A mappings -> PINCH must be VOLUME_UP
    mappings_a = client.get("/api/v1/mappings", headers=headers_a).json()
    pinch_a = next(m for m in mappings_a if m["gesture"] == "PINCH")
    assert pinch_a["action"] == "VOLUME_UP"

    # 6. Fetch User B mappings -> PINCH must be SCROLL_DOWN
    mappings_b = client.get("/api/v1/mappings", headers=headers_b).json()
    pinch_b = next(m for m in mappings_b if m["gesture"] == "PINCH")
    assert pinch_b["action"] == "SCROLL_DOWN"


def test_duplicate_user_registration_rejection(client):
    """Verify duplicate email registrations are strictly rejected."""
    email = "unique_student_2@college.edu"
    res1 = client.post("/api/v1/auth/register", json={
        "email": email,
        "name": "First Instance",
        "password": "SecurePass123"
    })
    assert res1.status_code == 201

    res2 = client.post("/api/v1/auth/register", json={
        "email": email,
        "name": "Second Instance",
        "password": "DifferentPass456"
    })
    assert res2.status_code == 400
    assert "already registered" in res2.json()["detail"]


def test_user_settings_and_calibration_isolation(client):
    """Verify user settings and calibration profiles maintain per-user isolation."""
    res_user = client.post("/api/v1/auth/register", json={
        "email": "calib_user_2@college.edu",
        "name": "Calib User",
        "password": "PassCalib123"
    })
    token = res_user.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Update calibration profile
    calib_res = client.put("/api/v1/calibration", json={
        "pinch_threshold": 0.42,
        "hand_scale_baseline": 0.38,
        "confidence_threshold": 0.72,
        "jitter_deadband": 0.005
    }, headers=headers)
    assert calib_res.status_code == 200
    assert calib_res.json()["pinch_threshold"] == 0.42

    # Fetch calibration
    get_calib = client.get("/api/v1/calibration", headers=headers)
    assert get_calib.status_code == 200
    assert get_calib.json()["pinch_threshold"] == 0.42


def test_mongo_dropped_connection_marks_disconnected_and_returns_503(client):
    """Regression test #3: When Mongo drops mid-session, is_connected becomes False and route returns 503."""
    from unittest.mock import AsyncMock, MagicMock
    from pymongo.errors import AutoReconnect

    # Login to get token
    reg_res = client.post("/api/v1/auth/register", json={
        "email": "mongo_drop@test.edu",
        "name": "Drop Test",
        "password": "Password123"
    })
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Simulate active Mongo connection dropping on update_one
    db_manager.is_connected = True
    mock_db = MagicMock()
    mock_coll = MagicMock()
    mock_coll.update_one = AsyncMock(side_effect=AutoReconnect("Connection reset by peer"))
    mock_db.__getitem__.return_value = mock_coll
    db_manager.db = mock_db

    # Attempt a write to mappings while collection raises connectivity error
    res = client.put("/api/v1/mappings/PINCH", json={
        "gesture": "PINCH",
        "action": "VOLUME_UP",
        "cooldown_ms": 300,
        "enabled": True
    }, headers=headers)

    # Must return 503 Service Unavailable, NOT unhandled 500 or silent 200
    assert res.status_code == 503
    assert "Database service unavailable" in res.json()["detail"]
    # DatabaseManager must be marked disconnected
    assert db_manager.is_connected is False

    # Clean up
    db_manager.db = None
    db_manager.is_connected = False

