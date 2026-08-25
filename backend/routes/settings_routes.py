"""
Settings Routes
Endpoints for user preferences and sensitivity parameters.
"""
from fastapi import APIRouter, Depends
from backend.models.settings_models import SettingsUpdate, SettingsResponse
from backend.security import get_current_user
from backend.database import db_manager

router = APIRouter(prefix="/settings", tags=["User Settings"])


@router.get("", response_model=SettingsResponse)
async def get_settings(current_user: dict = Depends(get_current_user)):
    """Fetch user settings."""
    user_id = current_user["user_id"]
    settings_coll = db_manager.get_settings_collection()

    if settings_coll is not None:
        doc = await settings_coll.find_one({"user_id": user_id})
        if doc:
            doc.pop("_id", None)
            return SettingsResponse(**doc)
    elif user_id in db_manager._mock_settings:
        return SettingsResponse(**db_manager._mock_settings[user_id])

    return SettingsResponse(user_id=user_id)


@router.put("", response_model=SettingsResponse)
async def update_settings(payload: SettingsUpdate, current_user: dict = Depends(get_current_user)):
    """Update user settings."""
    user_id = current_user["user_id"]
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    update_data["user_id"] = user_id

    settings_coll = db_manager.get_settings_collection()
    if settings_coll is not None:
        await settings_coll.update_one({"user_id": user_id}, {"$set": update_data}, upsert=True)
        doc = await settings_coll.find_one({"user_id": user_id})
        doc.pop("_id", None)
        return SettingsResponse(**doc)
    else:
        existing = db_manager._mock_settings.get(user_id, SettingsResponse(user_id=user_id).model_dump())
        existing.update(update_data)
        db_manager._mock_settings[user_id] = existing
        return SettingsResponse(**existing)

