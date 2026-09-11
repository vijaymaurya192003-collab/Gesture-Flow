"""
Usage Statistics & Telemetry Routes
Endpoints to record session usage counts (No video or continuous frames).
"""
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from backend.models.stats_models import StatsRecord, StatsSummary
from backend.security import get_current_user
from backend.database import db_manager

router = APIRouter(prefix="/stats", tags=["Usage Statistics"])


def _parse_timestamp(ts) -> Optional[datetime]:
    """Parse raw timestamp field into timezone-aware datetime or None if missing/invalid."""
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)
    if isinstance(ts, (int, float)):
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            return None
    if isinstance(ts, str):
        try:
            val_clean = ts.replace("Z", "+00:00")
            dt = datetime.fromisoformat(val_clean)
            return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


@router.post("", status_code=status.HTTP_201_CREATED)
async def record_session_stats(payload: StatsRecord, current_user: dict = Depends(get_current_user)):
    """Record summary usage metrics from an active session."""
    user_id = current_user["user_id"]
    stats_doc = {
        "user_id": user_id,
        "session_duration_seconds": payload.session_duration_seconds,
        "gesture_counts": payload.gesture_counts,
        "average_fps": payload.average_fps,
        "platform": payload.platform,
        "app_version": payload.app_version,
        "timestamp": datetime.now(timezone.utc)
    }

    stats_coll = db_manager.get_stats_collection()
    if stats_coll is not None:
        try:
            await stats_coll.insert_one(stats_doc)
        except Exception as exc:
            db_manager.record_failure(exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable: failed to record stats."
            )
    else:
        db_manager._mock_stats.append(stats_doc)

    return {"status": "recorded", "session_duration": payload.session_duration_seconds}


@router.get("/summary", response_model=StatsSummary)
async def get_stats_summary(current_user: dict = Depends(get_current_user)):
    """Fetch aggregated usage summary."""
    user_id = current_user["user_id"]
    stats_coll = db_manager.get_stats_collection()

    total_sessions = 0
    total_duration = 0.0
    gesture_totals = {}
    max_ts: Optional[datetime] = None

    if stats_coll is not None:
        try:
            cursor = stats_coll.find({"user_id": user_id})
            async for doc in cursor:
                total_sessions += 1
                total_duration += doc.get("session_duration_seconds", 0.0)
                for g, count in doc.get("gesture_counts", {}).items():
                    gesture_totals[g] = gesture_totals.get(g, 0) + count
                parsed_ts = _parse_timestamp(doc.get("timestamp"))
                if parsed_ts is not None:
                    if max_ts is None or parsed_ts > max_ts:
                        max_ts = parsed_ts
        except Exception as exc:
            db_manager.record_failure(exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable while fetching stats summary."
            )
    else:
        user_records = [r for r in db_manager._mock_stats if r["user_id"] == user_id]
        for r in user_records:
            total_sessions += 1
            total_duration += r.get("session_duration_seconds", 0.0)
            for g, count in r.get("gesture_counts", {}).items():
                gesture_totals[g] = gesture_totals.get(g, 0) + count
            parsed_ts = _parse_timestamp(r.get("timestamp"))
            if parsed_ts is not None:
                if max_ts is None or parsed_ts > max_ts:
                    max_ts = parsed_ts

    last_active = max_ts.isoformat() if max_ts is not None else None

    return StatsSummary(
        user_id=user_id,
        total_sessions=total_sessions,
        total_duration_seconds=total_duration,
        gesture_breakdown=gesture_totals,
        last_active=last_active
    )

