"""
MongoDB Atlas Database Connection Manager
Provides async database operations via official PyMongo / Motor client with ServerApi.
Implements connection pooling, health checks, sanitized logging, and resilient in-memory fallback.
"""
from typing import Optional, Dict, Any, List
import re
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.server_api import ServerApi
from backend.config import settings


class DatabaseManager:
    """Manages centralized connection to MongoDB Atlas."""

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.is_connected: bool = False

        # In-memory storage fallback for offline development & mock testing
        self._mock_users: Dict[str, Dict[str, Any]] = {}
        self._mock_mappings: Dict[str, List[Dict[str, Any]]] = {}
        self._mock_settings: Dict[str, Dict[str, Any]] = {}
        self._mock_calibration: Dict[str, Dict[str, Any]] = {}
        self._mock_stats: List[Dict[str, Any]] = []

    @staticmethod
    def _sanitize_uri(uri: str) -> str:
        """Sanitizes connection string by masking user credentials for safe logging."""
        if not uri:
            return ""
        return re.sub(r"://([^:]+):([^@]+)@", r"://\1:****@", uri)

    async def connect_db(self) -> bool:
        """
        Initialize reusable MongoDB Atlas client with Stable API and connection timeouts.
        Fails gracefully without crashing if MONGODB_URI is missing or offline.
        """
        uri = settings.mongodb_uri.strip()
        db_name = settings.mongodb_database.strip() or "gesture_flow"

        if not uri:
            print("[DatabaseManager] MONGODB_URI not configured. Operating in local in-memory fallback mode.")
            self.is_connected = False
            return False

        # Filter out obvious placeholder mock URIs
        if "<username>" in uri or "<password>" in uri or "demo:demo" in uri:
            print("[DatabaseManager] Notice: Placeholder MONGODB_URI detected. Using local in-memory storage for demonstration.")
            self.is_connected = False
            return False

        sanitized = self._sanitize_uri(uri)
        try:
            print(f"[DatabaseManager] Connecting to MongoDB Atlas ({sanitized})...")
            self.client = AsyncIOMotorClient(
                uri,
                server_api=ServerApi('1'),
                serverSelectionTimeoutMS=4000,
                connectTimeoutMS=4000,
                socketTimeoutMS=5000,
                maxPoolSize=50,
                minPoolSize=5
            )
            self.db = self.client[db_name]

            # Perform ping to verify cluster reachability
            await self.ping_db()
            self.is_connected = True
            print(f"[DatabaseManager] Successfully connected to MongoDB Atlas database '{db_name}'.")
            return True
        except Exception as e:
            print(f"[DatabaseManager] Warning: MongoDB Atlas connection failed ({type(e).__name__}). Using in-memory fallback mode.")
            self.is_connected = False
            return False

    async def ping_db(self) -> bool:
        """Send a ping command to verify database liveliness."""
        if self.client is None:
            return False
        try:
            res = await self.client.admin.command('ping')
            return bool(res.get('ok') == 1.0)
        except Exception:
            return False

    async def close_db(self) -> None:
        """Close MongoDB Atlas client connections cleanly."""
        if self.client is not None:
            self.client.close()
            self.client = None
            self.db = None
            self.is_connected = False
            print("[DatabaseManager] MongoDB Atlas connection closed cleanly.")

    def record_failure(self, exc: Exception) -> None:
        """
        Marks database as disconnected on connectivity/operation failure
        and safely logs error type without leaking credentials or URIs.
        """
        self.is_connected = False
        error_type = type(exc).__name__
        print(f"[DatabaseManager] MongoDB connectivity/operation failure: {error_type}. Set is_connected = False.")

    # -------------------------------------------------------------------------
    # Collection Accessors (Returns None if in mock fallback mode)
    # -------------------------------------------------------------------------

    def get_users_collection(self):
        """Users collection: auth credentials & accounts."""
        if self.is_connected and self.db is not None:
            return self.db["users"]
        return None

    def get_mappings_collection(self):
        """Gesture mappings collection: custom gesture-to-action bindings."""
        if self.is_connected and self.db is not None:
            return self.db["gesture_mappings"]
        return None

    def get_settings_collection(self):
        """User settings collection: resolution, FPS, theme, sensitivity."""
        if self.is_connected and self.db is not None:
            return self.db["user_settings"]
        return None

    def get_calibration_collection(self):
        """Calibration profiles collection: biometric thresholds & deadbands."""
        if self.is_connected and self.db is not None:
            return self.db["calibration_profiles"]
        return None

    def get_stats_collection(self):
        """Stats collection: aggregate session telemetry."""
        if self.is_connected and self.db is not None:
            return self.db["stats"]
        return None


db_manager = DatabaseManager()
