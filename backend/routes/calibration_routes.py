"""
Calibration Profile Routes
Endpoints for user hand size and threshold calibration profiles.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from backend.models.calibration_models import CalibrationUpdate, CalibrationResponse
from backend.security import get_current_user
from backend.database import db_manager

router = APIRouter(prefix="/calibration", tags=["Calibration"])


@router.get("", response_model=CalibrationResponse)
async def get_calibration(current_user: dict = Depends(get_current_user)):
    """Fetch user hand calibration profile."""
    user_id = current_user["user_id"]
    calib_coll = db_manager.get_calibration_collection()

    if calib_coll is not None:
        doc = await calib_coll.find_one({"user_id": user_id})
        if doc:
            doc.pop("_id", None)
            return CalibrationResponse(**doc)
    elif user_id in db_manager._mock_calibration:
        return CalibrationResponse(**db_manager._mock_calibration[user_id])

    return CalibrationResponse(user_id=user_id)


@router.put("", response_model=CalibrationResponse)
async def update_calibration(payload: CalibrationUpdate, current_user: dict = Depends(get_current_user)):
    """Update user hand calibration profile."""
    user_id = current_user["user_id"]
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    update_data["user_id"] = user_id
    update_data["calibrated_at"] = datetime.now(timezone.utc).isoformat()

    calib_coll = db_manager.get_calibration_collection()
    if calib_coll is not None:
        await calib_coll.update_one({"user_id": user_id}, {"$set": update_data}, upsert=True)
        doc = await calib_coll.find_one({"user_id": user_id})
        doc.pop("_id", None)
        return CalibrationResponse(**doc)
    else:
        existing = db_manager._mock_calibration.get(user_id, CalibrationResponse(user_id=user_id).model_dump())
        existing.update(update_data)
        db_manager._mock_calibration[user_id] = existing
        return CalibrationResponse(**existing)

