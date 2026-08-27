"""
Local Storage Manager (SQLite / JSON)
Provides offline-first persistence for gesture mappings, settings, calibration profiles, and sync queues.
Includes robust error-tracking, retry counters, and acknowledgement-based sync queue management.
"""
import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from android.config.app_config import config
from android.models.gesture_models import GestureMappingItem
from android.models.settings_models import UserSettingsModel, CalibrationProfileModel
from android.config.constants import DEFAULT_GESTURE_MAPPINGS


class LocalStorageManager:
    """
    Handles local offline persistence.
    Ensures Gesture Flow runs smoothly without internet connection.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Get SQLite connection."""
        return sqlite3.connect(str(self.db_path))

    def _init_database(self) -> None:
        """Create tables if not already existing."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Mappings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gesture_mappings (
                    gesture TEXT PRIMARY KEY,
                    action TEXT NOT NULL,
                    sensitivity REAL NOT NULL,
                    confidence_threshold REAL NOT NULL,
                    cooldown_ms INTEGER NOT NULL,
                    enabled INTEGER NOT NULL,
                    description TEXT
                )
            """)

            # User Settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL
                )
            """)

            # Calibration table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calibration_profile (
                    id TEXT PRIMARY KEY,
                    profile_json TEXT NOT NULL
                )
            """)

            # Auth session table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS auth_session (
                    id INTEGER PRIMARY KEY,
                    token TEXT,
                    user_json TEXT
                )
            """)

            # Offline sync queue with retry counter and last error tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    last_error TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Migration: Ensure columns exist if table was previously created
            cursor.execute("PRAGMA table_info(sync_queue)")
            cols = [c[1] for c in cursor.fetchall()]
            if "retry_count" not in cols:
                try:
                    cursor.execute("ALTER TABLE sync_queue ADD COLUMN retry_count INTEGER DEFAULT 0")
                except Exception:
                    pass
            if "last_error" not in cols:
                try:
                    cursor.execute("ALTER TABLE sync_queue ADD COLUMN last_error TEXT")
                except Exception:
                    pass
            if "status" not in cols:
                try:
                    cursor.execute("ALTER TABLE sync_queue ADD COLUMN status TEXT DEFAULT 'pending'")
                except Exception:
                    pass

            conn.commit()

        # Seed initial mappings if empty
        self._seed_default_mappings_if_empty()

    def _seed_default_mappings_if_empty(self) -> None:
        """Seed initial mappings if database was just created."""
        mappings = self.load_mappings()
        if not mappings:
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
                self.save_mapping(item)

    # --- Gesture Mappings CRUD ---

    def load_mappings(self) -> Dict[str, GestureMappingItem]:
        """Load all gesture mappings from local database."""
        mappings = {}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT gesture, action, sensitivity, confidence_threshold, cooldown_ms, enabled, description FROM gesture_mappings")
            for row in cursor.fetchall():
                item = GestureMappingItem(
                    gesture=row[0],
                    action=row[1],
                    sensitivity=row[2],
                    confidence_threshold=row[3],
                    cooldown_ms=row[4],
                    enabled=bool(row[5]),
                    description=row[6] or ""
                )
                mappings[row[0]] = item
        return mappings

    def save_mapping(self, item: GestureMappingItem) -> None:
        """Upsert a single gesture mapping."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO gesture_mappings 
                (gesture, action, sensitivity, confidence_threshold, cooldown_ms, enabled, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                item.gesture,
                item.action,
                item.sensitivity,
                item.confidence_threshold,
                item.cooldown_ms,
                1 if item.enabled else 0,
                item.description
            ))
            conn.commit()

    # --- Settings CRUD ---

    def load_settings(self) -> UserSettingsModel:
        """Load user settings."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value_json FROM user_settings WHERE key = 'current_settings'")
            row = cursor.fetchone()
            if row:
                try:
                    data = json.loads(row[0])
                    return UserSettingsModel(**data)
                except Exception:
                    pass
        return UserSettingsModel()

    def save_settings(self, settings: UserSettingsModel) -> None:
        """Save user settings."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO user_settings (key, value_json)
                VALUES ('current_settings', ?)
            """, (json.dumps(settings.model_dump()),))
            conn.commit()

    # --- Calibration CRUD ---

    def load_calibration(self) -> CalibrationProfileModel:
        """Load calibration profile."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT profile_json FROM calibration_profile WHERE id = 'default'")
            row = cursor.fetchone()
            if row:
                try:
                    data = json.loads(row[0])
                    return CalibrationProfileModel(**data)
                except Exception:
                    pass
        return CalibrationProfileModel()

    def save_calibration(self, profile: CalibrationProfileModel) -> None:
        """Save calibration profile."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO calibration_profile (id, profile_json)
                VALUES ('default', ?)
            """, (json.dumps(profile.model_dump()),))
            conn.commit()

    # --- Auth Session CRUD ---

    def get_auth_token(self) -> Optional[str]:
        """Retrieve stored JWT auth token."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT token FROM auth_session WHERE id = 1")
            row = cursor.fetchone()
            return row[0] if row else None

    def save_auth_session(self, token: str, user_dict: dict) -> None:
        """Persist JWT auth session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO auth_session (id, token, user_json)
                VALUES (1, ?, ?)
            """, (token, json.dumps(user_dict)))
            conn.commit()

    def clear_auth_session(self) -> None:
        """Logout and clear session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM auth_session WHERE id = 1")
            conn.commit()

    # --- Sync Queue CRUD ---

    def enqueue_sync(self, endpoint: str, method: str, payload: dict) -> None:
        """Enqueue offline action for background sync."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sync_queue (endpoint, method, payload_json, retry_count, status)
                VALUES (?, ?, ?, 0, 'pending')
            """, (endpoint, method, json.dumps(payload)))
            conn.commit()

    def get_sync_queue(self) -> List[Dict[str, Any]]:
        """Fetch pending sync queue items."""
        items = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, endpoint, method, payload_json, retry_count, last_error FROM sync_queue WHERE status = 'pending' ORDER BY id ASC")
            for row in cursor.fetchall():
                items.append({
                    "id": row[0],
                    "endpoint": row[1],
                    "method": row[2],
                    "payload": json.loads(row[3]),
                    "retry_count": row[4] or 0,
                    "last_error": row[5]
                })
        return items

    def record_sync_failure(self, item_id: int, error_msg: str, max_retries: int = 5) -> None:
        """Increment retry counter and record failure error message."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sync_queue 
                SET retry_count = retry_count + 1,
                    last_error = ?,
                    status = CASE WHEN retry_count + 1 >= ? THEN 'dead_letter' ELSE 'pending' END
                WHERE id = ?
            """, (error_msg, max_retries, item_id))
            conn.commit()

    def delete_sync_item(self, item_id: int) -> None:
        """Remove successfully acknowledged item from sync queue."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sync_queue WHERE id = ?", (item_id,))
            conn.commit()
