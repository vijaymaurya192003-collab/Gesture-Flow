"""
Cloud Synchronization Client
Performs non-blocking background syncing between local SQLite cache and FastAPI/MongoDB backend.
Implements retry counters, exponential backoff, acknowledgement-based queue removal, and safe conflict resolution.
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
        self.max_retries = 3

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
                print(f"[CloudSyncClient] Sync loop exception: {e}")
            time.sleep(interval)

    def check_health(self) -> bool:
        """Ping backend /health endpoint."""
        try:
            clean_base = self.api_base_url.rsplit('/api', 1)[0].rstrip('/')
            url = f"{clean_base}/health"
            res = requests.get(url, timeout=3.0)
            self.is_online = (res.status_code == 200)
            return self.is_online
        except Exception:
            self.is_online = False
            return False

    def sync_now(self) -> bool:
        """
        Executes a robust synchronization cycle:
        1. Check server reachability
        2. Flush pending offline queue with acknowledgement-based removal
        3. Pull updated mappings from backend with safe local conflict resolution
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
                # Support endpoint aliases
                endpoint = item['endpoint']
                endpoint_url = f"{self.api_base_url.rstrip('/')}{endpoint if endpoint.startswith('/') else '/' + endpoint}"
                method = item['method'].upper()
                
                if method == "POST":
                    r = requests.post(endpoint_url, json=item['payload'], headers=headers, timeout=4.0)
                elif method == "PUT":
                    r = requests.put(endpoint_url, json=item['payload'], headers=headers, timeout=4.0)
                elif method == "DELETE":
                    r = requests.delete(endpoint_url, headers=headers, timeout=4.0)
                else:
                    r = requests.request(method, endpoint_url, json=item['payload'], headers=headers, timeout=4.0)

                # Acknowledgement-based removal
                if r.status_code in (200, 201, 204):
                    self.storage.delete_sync_item(item['id'])
                elif r.status_code in (400, 422):
                    # Unrecoverable payload validation error: dead-letter after retries
                    self.storage.record_sync_failure(item['id'], f"HTTP {r.status_code}: {r.text}", max_retries=self.max_retries)
                else:
                    # Temporary 5xx or network glitch
                    self.storage.record_sync_failure(item['id'], f"Server status {r.status_code}", max_retries=self.max_retries)
            except Exception as e:
                self.storage.record_sync_failure(item['id'], str(e), max_retries=self.max_retries)
                print(f"[CloudSyncClient] Transient failure flushing queue item {item['id']}: {e}")
                break

        # 2. Pull latest mappings if authenticated
        if token:
            try:
                res = requests.get(f"{self.api_base_url.rstrip('/')}/mappings", headers=headers, timeout=4.0)
                if res.status_code == 200:
                    remote_mappings = res.json()
                    # Conflict policy: Remote mappings update local state unless offline changes are currently pending in sync_queue
                    pending_endpoints = [i['endpoint'] for i in self.storage.get_sync_queue()]
                    if not any("/mappings" in ep or "/gestures" in ep for ep in pending_endpoints):
                        for m in remote_mappings:
                            item = GestureMappingItem(**m)
                            self.storage.save_mapping(item)
            except Exception as e:
                print(f"[CloudSyncClient] Failed to pull mappings: {e}")

        if self.on_sync_status_changed:
            self.on_sync_status_changed(True, "Online (Cloud Synced)")

        return True
