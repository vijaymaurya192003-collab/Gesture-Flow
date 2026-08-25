"""
Usage Statistics & Telemetry Routes
Endpoints to record session usage counts (No video or continuous frames).
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from backend.models.stats_models import StatsRecord, StatsSummary
from backend.security import get_current_user
from backend.database import db_manager

router = APIRouter(prefix="/stats", tags=["Usage Statistics"])


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
        await stats_coll.insert_one(stats_doc)
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
    last_active = None

    if stats_coll is not None:
        cursor = stats_coll.find({"user_id": user_id})
        async for doc in cursor:
            total_sessions += 1
            total_duration += doc.get("session_duration_seconds", 0.0)
            for g, count in doc.get("gesture_counts", {}).items():
                gesture_totals[g] = gesture_totals.get(g, 0) + count
            ts = doc.get("timestamp")
            if ts:
                last_active = ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)
    else:
        user_records = [r for r in db_manager._mock_stats if r["user_id"] == user_id]
        for r in user_records:
            total_sessions += 1
            total_duration += r.get("session_duration_seconds", 0.0)
            for g, count in r.get("gesture_counts", {}).items():
                gesture_totals[g] = gesture_totals.get(g, 0) + count
            ts = r.get("timestamp")
            if ts:
                last_active = ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)

    return StatsSummary(
        user_id=user_id,
        total_sessions=total_sessions,
        total_duration_seconds=total_duration,
        gesture_breakdown=gesture_totals,
        last_active=last_active
    )

