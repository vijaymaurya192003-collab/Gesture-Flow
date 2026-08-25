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

    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    is_connected: bool = False

    # In-memory storage fallback for offline development & mock testing
    _mock_users: Dict[str, Dict[str, Any]] = {}
    _mock_mappings: Dict[str, List[Dict[str, Any]]] = {}
    _mock_settings: Dict[str, Dict[str, Any]] = {}
    _mock_calibration: Dict[str, Dict[str, Any]] = {}
    _mock_stats: List[Dict[str, Any]] = []

    @classmethod
    def _sanitize_uri(cls, uri: str) -> str:
        """Sanitizes connection string by masking user credentials for safe logging."""
        if not uri:
            return ""
        return re.sub(r"://([^:]+):([^@]+)@", r"://\1:****@", uri)

    @classmethod
    async def connect_db(cls) -> bool:
        """
        Initialize reusable MongoDB Atlas client with Stable API and connection timeouts.
        Fails gracefully without crashing if MONGODB_URI is missing or offline.
        """
        uri = settings.mongodb_uri.strip()
        db_name = settings.mongodb_database.strip() or "gesture_flow"

        if not uri:
            print("[DatabaseManager] MONGODB_URI not configured. Operating in local in-memory fallback mode.")
            cls.is_connected = False
            return False

        # Filter out obvious placeholder mock URIs
        if "<username>" in uri or "<password>" in uri or "demo:demo" in uri:
            print("[DatabaseManager] Notice: Placeholder MONGODB_URI detected. Using local in-memory storage for demonstration.")
            cls.is_connected = False
            return False

        sanitized = cls._sanitize_uri(uri)
        try:
            print(f"[DatabaseManager] Connecting to MongoDB Atlas ({sanitized})...")
            cls.client = AsyncIOMotorClient(
                uri,
                server_api=ServerApi('1'),
                serverSelectionTimeoutMS=4000,
                connectTimeoutMS=4000,
                socketTimeoutMS=5000,
                maxPoolSize=50,
                minPoolSize=5
            )
            cls.db = cls.client[db_name]

            # Perform ping to verify cluster reachability
            await cls.ping_db()
            cls.is_connected = True
            print(f"[DatabaseManager] Successfully connected to MongoDB Atlas database '{db_name}'.")
            return True
        except Exception as e:
            print(f"[DatabaseManager] Warning: MongoDB Atlas connection failed ({type(e).__name__}). Using in-memory fallback mode.")
            cls.is_connected = False
            return False

    @classmethod
    async def ping_db(cls) -> bool:
        """Send a ping command to verify database liveliness."""
        if cls.client is None:
            return False
        try:
            res = await cls.client.admin.command('ping')
            return bool(res.get('ok') == 1.0)
        except Exception:
            return False

    @classmethod
    async def close_db(cls) -> None:
        """Close MongoDB Atlas client connections cleanly."""
        if cls.client is not None:
            cls.client.close()
            cls.client = None
            cls.db = None
            cls.is_connected = False
            print("[DatabaseManager] MongoDB Atlas connection closed cleanly.")

    # -------------------------------------------------------------------------
    # Collection Accessors (Returns None if in mock fallback mode)
    # -------------------------------------------------------------------------

    @classmethod
    def get_users_collection(cls):
        """Users collection: auth credentials & accounts."""
        if cls.is_connected and cls.db is not None:
            return cls.db["users"]
        return None

    @classmethod
    def get_mappings_collection(cls):
        """Gesture mappings collection: custom gesture-to-action bindings."""
        if cls.is_connected and cls.db is not None:
            return cls.db["gesture_mappings"]
        return None

    @classmethod
    def get_settings_collection(cls):
        """User settings collection: resolution, FPS, theme, sensitivity."""
        if cls.is_connected and cls.db is not None:
            return cls.db["user_settings"]
        return None

    @classmethod
    def get_calibration_collection(cls):
        """Calibration profiles collection: biometric thresholds & deadbands."""
        if cls.is_connected and cls.db is not None:
            return cls.db["calibration_profiles"]
        return None

    @classmethod
    def get_stats_collection(cls):
        """Stats collection: aggregate session telemetry."""
        if cls.is_connected and cls.db is not None:
            return cls.db["stats"]
        return None


db_manager = DatabaseManager()
