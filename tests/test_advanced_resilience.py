"""
Advanced Resilience & Robustness Test Suite
Covers camera failure handling, latest-frame behavior, latency metrics,
network failure tolerance, authentication expiration, and emergency lockout.
"""
import time
import pytest
from unittest.mock import MagicMock, patch
from datetime import timedelta

from android.camera.opencv_camera import OpenCVCamera
from android.gestures.state_machine import GestureStateMachine
from android.gestures.feature_extractor import HandFeatures
from android.actions.action_dispatcher import ActionDispatcher
from android.config.constants import GestureType, SafeActionType
from android.models.gesture_models import GestureStateEnum, PipelineMetrics
from android.sync.local_storage import LocalStorageManager
from android.sync.sync_client import CloudSyncClient
from backend.security import create_access_token, decode_access_token


def test_camera_graceful_failure_and_simulated_fallback():
    """Verify that camera initializes fallback cleanly when physical camera is unavailable."""
    # Use invalid camera index
    cam = OpenCVCamera(camera_index=999, width=320, height=240, target_fps=30)
    started = cam.start()
    assert started is True
    assert cam.is_running() is True

    # Read frame should succeed using simulated feed
    time.sleep(0.05)
    success, frame = cam.read_frame()
    assert success is True
    assert frame is not None
    assert frame.shape == (240, 320, 3)

    cam.stop()
    assert cam.is_running() is False


def test_camera_latest_frame_no_queue_buildup():
    """Verify camera always returns the latest frame without queue lag."""
    cam = OpenCVCamera(camera_index=999, width=320, height=240, target_fps=30)
    cam.start()
    time.sleep(0.1)

    # Fetch latest frame twice
    ret1, f1 = cam.read_frame()
    ret2, f2 = cam.read_frame()
    assert ret1 is True and ret2 is True
    assert f1 is not None and f2 is not None

    cam.stop()


def test_pipeline_latency_metrics_struct():
    """Verify PipelineMetrics correctly aggregates and records timing milestones."""
    metrics = PipelineMetrics(
        camera_capture_ms=2.5,
        vision_ms=18.4,
        smoothing_ms=0.6,
        feature_ms=0.4,
        classification_ms=0.8,
        action_ms=0.5,
        total_pipeline_ms=23.2,
        fps=30.0
    )
    assert metrics.total_pipeline_ms == 23.2
    assert metrics.vision_ms == 18.4
    assert metrics.fps == 30.0
    assert metrics.camera_capture_ms == 2.5


def test_jwt_token_expiration_handling():
    """Verify expired JWT tokens are cleanly rejected."""
    payload = {"sub": "user-123", "email": "test@college.edu"}
    # Token expired 10 minutes ago
    expired_token = create_access_token(payload, expires_delta=timedelta(minutes=-10))

    decoded = decode_access_token(expired_token)
    assert decoded is None


def test_sync_client_network_failure_resilience(tmp_path):
    """Verify CloudSyncClient handles network failure gracefully without crashing."""
    db_file = tmp_path / "sync_fail_test.db"
    storage = LocalStorageManager(db_path=db_file)
    # Point to non-routable localhost port
    sync_client = CloudSyncClient(storage, api_base_url="http://127.0.0.1:59999/api/v1")

    # Queue an offline item
    storage.enqueue_sync("/mappings", "POST", {"gesture": "PINCH", "action": "TAP"})

    # sync_now should return False and not throw unhandled exception
    synced = sync_client.sync_now()
    assert synced is False
    assert sync_client.is_online is False

    # Queue must retain the item
    queue = storage.get_sync_queue()
    assert len(queue) == 1


def test_emergency_stop_remains_locked_under_burst_events():
    """Verify emergency stop withstands high-frequency subsequent event spam."""
    dispatcher = ActionDispatcher()

    # Trigger stop
    stop_res = GestureStateMachine().process_frame(
        hand_detected=True,
        detected_gesture=GestureType.FIST,
        confidence=0.95,
        features=HandFeatures(),
        mapped_action=SafeActionType.EMERGENCY_STOP.value
    )
    dispatcher.dispatch(stop_res)
    assert dispatcher.emergency_stopped is True

    # Burst of 50 consecutive tap events
    sm = GestureStateMachine()
    for i in range(50):
        res = sm.process_frame(
            hand_detected=True,
            detected_gesture=GestureType.PINCH,
            confidence=0.95,
            features=HandFeatures(pinch_distance_norm=0.1),
            mapped_action=SafeActionType.TAP.value
        )
        dispatched = dispatcher.dispatch(res)
        assert dispatched is False

    # Reset lockout
    dispatcher.reset_emergency_stop()
    assert dispatcher.emergency_stopped is False


def test_gesture_cooldown_override_configuration():
    """Verify custom cooldown durations are enforced per gesture."""
    sm = GestureStateMachine(palm_hold_ms=0)
    sm.set_cooldown(GestureType.OPEN_PALM.value, 1200)

    features = HandFeatures(extended_count=5)
    # Trigger palm
    res1 = sm.process_frame(
        hand_detected=True,
        detected_gesture=GestureType.OPEN_PALM,
        confidence=0.9,
        features=features,
        mapped_action=SafeActionType.PAUSE_GESTURES.value
    )
    assert res1.state == GestureStateEnum.ACTION_TRIGGERED

    # Within 1200ms, should stay in cooldown
    time.sleep(0.05)
    res2 = sm.process_frame(
        hand_detected=True,
        detected_gesture=GestureType.OPEN_PALM,
        confidence=0.9,
        features=features,
        mapped_action=SafeActionType.PAUSE_GESTURES.value
    )
    assert res2.state == GestureStateEnum.COOLDOWN
    assert res2.action == "NONE"

