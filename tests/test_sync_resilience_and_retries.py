"""
Unit Tests for Synchronization Resilience, Retries, and Queue Management
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from android.sync.local_storage import LocalStorageManager
from android.sync.sync_client import CloudSyncClient
from android.models.gesture_models import GestureMappingItem


def test_sync_queue_retry_and_dead_letter_logic(tmp_path: Path):
    """Verify that failed items increment retry count and dead-letter on max retries."""
    test_db = tmp_path / "test_sync.db"
    storage = LocalStorageManager(db_path=test_db)

    storage.enqueue_sync("/mappings", "POST", {"gesture": "PINCH", "action": "TAP"})
    queue = storage.get_sync_queue()
    assert len(queue) == 1
    item_id = queue[0]["id"]
    assert queue[0]["retry_count"] == 0

    # Record 1st failure
    storage.record_sync_failure(item_id, "Network timeout", max_retries=3)
    queue = storage.get_sync_queue()
    assert len(queue) == 1
    assert queue[0]["retry_count"] == 1
    assert queue[0]["last_error"] == "Network timeout"

    # Record 2nd failure
    storage.record_sync_failure(item_id, "Connection refused", max_retries=3)
    queue = storage.get_sync_queue()
    assert len(queue) == 1
    assert queue[0]["retry_count"] == 2

    # Record 3rd failure -> should be marked dead_letter and excluded from pending queue
    storage.record_sync_failure(item_id, "HTTP 400 Bad Request", max_retries=3)
    pending_queue = storage.get_sync_queue()
    assert len(pending_queue) == 0


def test_sync_client_acknowledgement_removal(tmp_path: Path):
    """Verify that successful HTTP 200 response deletes item from sync queue."""
    test_db = tmp_path / "test_ack.db"
    storage = LocalStorageManager(db_path=test_db)
    client = CloudSyncClient(storage, api_base_url="http://mock-server/api/v1")

    storage.enqueue_sync("/mappings", "POST", {"gesture": "INDEX_POINT", "action": "POINTER_MOVE"})
    assert len(storage.get_sync_queue()) == 1

    # Mock health and successful POST
    mock_resp_health = MagicMock()
    mock_resp_health.status_code = 200

    mock_resp_post = MagicMock()
    mock_resp_post.status_code = 200

    with patch("requests.get", return_value=mock_resp_health), \
         patch("requests.post", return_value=mock_resp_post):
        synced = client.sync_now()
        assert synced is True
        # Item should be deleted upon acknowledgement
        assert len(storage.get_sync_queue()) == 0

