"""
Cloud Synchronization Client
Performs non-blocking background syncing between local SQLite cache and FastAPI/MongoDB backend.
"""
import time
import threading
from typing import Optional, Dict, Any, Callable
import requests

from android.config.app_config import config
from android.sync.local_storage import LocalStorageManager
from android.models.gesture_models import GestureMappingItem


class CloudSyncClient:
    """
    Non-blocking background client that synchronizes offline updates to the FastAPI backend.
    """

    def __init__(self, storage: LocalStorageManager, api_base_url: Optional[str] = None):
        self.storage = storage
        self.api_base_url = api_base_url or config.api_base_url
        self.is_online = False
        self._sync_thread: Optional[threading.Thread] = None
        self._running = False
        self.on_sync_status_changed: Optional[Callable[[bool, str], None]] = None

    def start_background_sync(self, interval_seconds: int = 45) -> None:
        """Start background sync daemon thread."""
        if self._running:
            return
        self._running = True
        self._sync_thread = threading.Thread(target=self._sync_loop, args=(interval_seconds,), daemon=True)
        self._sync_thread.start()
        print("[CloudSyncClient] Background sync worker started.")

    def stop(self) -> None:
        """Stop background sync worker."""
        self._running = False
        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=1.0)
        print("[CloudSyncClient] Background sync worker stopped.")

    def _sync_loop(self, interval: int) -> None:
        """Periodic sync loop."""
        while self._running:
            try:
                self.sync_now()
            except Exception as e:
                print(f"[CloudSyncClient] Sync error: {e}")
            time.sleep(interval)

    def check_health(self) -> bool:
        """Ping backend /health endpoint."""
        try:
            url = f"{self.api_base_url.rsplit('/api', 1)[0]}/health"
            res = requests.get(url, timeout=3.0)
            self.is_online = (res.status_code == 200)
            return self.is_online
        except Exception:
            self.is_online = False
            return False

    def sync_now(self) -> bool:
        """
        Executes a synchronization cycle:
        1. Check server reachability
        2. Flush pending offline queue
        3. Pull updated mappings from backend
        """
        online = self.check_health()
        if not online:
            if self.on_sync_status_changed:
                self.on_sync_status_changed(False, "Offline (Local mode active)")
            return False

        token = self.storage.get_auth_token()
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        # 1. Flush offline sync queue
        queue = self.storage.get_sync_queue()
        for item in queue:
            try:
                endpoint_url = f"{self.api_base_url}{item['endpoint']}"
                method = item['method'].upper()
                if method == "POST":
                    r = requests.post(endpoint_url, json=item['payload'], headers=headers, timeout=4.0)
                elif method == "PUT":
                    r = requests.put(endpoint_url, json=item['payload'], headers=headers, timeout=4.0)
                else:
                    r = requests.request(method, endpoint_url, json=item['payload'], headers=headers, timeout=4.0)

                if r.status_code in (200, 201, 204):
                    self.storage.delete_sync_item(item['id'])
            except Exception as e:
                print(f"[CloudSyncClient] Failed to flush queue item {item['id']}: {e}")
                break

        # 2. Pull latest mappings if authenticated
        if token:
            try:
                res = requests.get(f"{self.api_base_url}/mappings", headers=headers, timeout=4.0)
                if res.status_code == 200:
                    remote_mappings = res.json()
                    for m in remote_mappings:
                        item = GestureMappingItem(**m)
                        self.storage.save_mapping(item)
            except Exception as e:
                print(f"[CloudSyncClient] Failed to pull mappings: {e}")

        if self.on_sync_status_changed:
            self.on_sync_status_changed(True, "Online (Cloud Synced)")

        return True

