"""
Unit Tests for Local Offline Storage and Sync Queue
"""
import os
import tempfile
import uuid
from pathlib import Path
import pytest

from android.sync.local_storage import LocalStorageManager
from android.models.gesture_models import GestureMappingItem
from android.models.settings_models import UserSettingsModel, CalibrationProfileModel


@pytest.fixture
def temp_storage():
    """Create a temporary LocalStorageManager instance."""
    unique_id = str(uuid.uuid4())[:8]
    db_file = Path(tempfile.gettempdir()) / f"gestureflow_test_{unique_id}.db"
    storage = LocalStorageManager(db_path=db_file)
    yield storage
    # Cleanup after test
    try:
        if db_file.exists():
            os.remove(str(db_file))
    except Exception:
        pass


def test_sqlite_mappings_persistence(temp_storage):
    """Verify storing and retrieving gesture mappings in local SQLite."""
    item = GestureMappingItem(
        gesture="PINCH",
        action="BACK",
        sensitivity=1.4,
        confidence_threshold=0.82,
        cooldown_ms=320,
        enabled=True,
        description="Custom Back on Pinch"
    )
    temp_storage.save_mapping(item)

    mappings = temp_storage.load_mappings()
    assert "PINCH" in mappings
    retrieved = mappings["PINCH"]
    assert retrieved.action == "BACK"
    assert retrieved.sensitivity == 1.4
    assert retrieved.confidence_threshold == 0.82
    assert retrieved.cooldown_ms == 320


def test_sqlite_settings_and_calibration(temp_storage):
    """Verify settings and calibration profiles persist in SQLite."""
    # Settings
    settings = UserSettingsModel(theme="Light", target_fps=60, pointer_sensitivity=2.0)
    temp_storage.save_settings(settings)
    loaded_settings = temp_storage.load_settings()
    assert loaded_settings.theme == "Light"
    assert loaded_settings.target_fps == 60
    assert loaded_settings.pointer_sensitivity == 2.0

    # Calibration
    calib = CalibrationProfileModel(pinch_threshold=0.29, min_confidence_floor=0.72)
    temp_storage.save_calibration(calib)
    loaded_calib = temp_storage.load_calibration()
    assert loaded_calib.pinch_threshold == 0.29
    assert loaded_calib.min_confidence_floor == 0.72


def test_offline_sync_queue(temp_storage):
    """Verify offline sync queue enqueuing and processing."""
    # Enqueue two offline updates
    temp_storage.enqueue_sync("/mappings", "POST", {"gesture": "PINCH", "action": "TAP"})
    temp_storage.enqueue_sync("/settings", "PUT", {"theme": "Dark"})

    queue = temp_storage.get_sync_queue()
    assert len(queue) == 2
    assert queue[0]["endpoint"] == "/mappings"
    assert queue[1]["endpoint"] == "/settings"

    # Delete first processed item
    item_id = queue[0]["id"]
    temp_storage.delete_sync_item(item_id)

    remaining = temp_storage.get_sync_queue()
    assert len(remaining) == 1
    assert remaining[0]["endpoint"] == "/settings"

