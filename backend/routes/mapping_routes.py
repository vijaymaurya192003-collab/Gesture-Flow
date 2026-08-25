"""
Gesture Mapping Routes
CRUD endpoints for managing user gesture-to-action mappings.
Supports /gestures and /mappings paths.
"""
from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from backend.models.mapping_models import MappingCreate, MappingResponse
from backend.security import get_current_user
from backend.database import db_manager
from android.config.constants import DEFAULT_GESTURE_MAPPINGS
from android.actions.action_registry import ActionRegistry

router = APIRouter(tags=["Gesture Mappings"])


@router.get("/mappings", response_model=List[MappingResponse])
@router.get("/gestures", response_model=List[MappingResponse])
async def get_user_mappings(current_user: dict = Depends(get_current_user)):
    """Fetch all gesture mappings configured for the user."""
    user_id = current_user["user_id"]
    mappings_coll = db_manager.get_mappings_collection()

    user_mappings = []
    if mappings_coll is not None:
        cursor = mappings_coll.find({"user_id": user_id})
        async for doc in cursor:
            user_mappings.append(
                MappingResponse(
                    user_id=user_id,
                    gesture=doc["gesture"],
                    action=doc["action"],
                    sensitivity=doc.get("sensitivity", 1.0),
                    confidence_threshold=doc.get("confidence_threshold", 0.70),
                    cooldown_ms=doc.get("cooldown_ms", 400),
                    enabled=doc.get("enabled", True),
                    description=doc.get("description", "")
                )
            )
    elif user_id in db_manager._mock_mappings:
        user_mappings = [MappingResponse(**m) for m in db_manager._mock_mappings[user_id]]

    # If no custom mappings found, populate with system defaults
    if not user_mappings:
        default_list = []
        for g_name, d in DEFAULT_GESTURE_MAPPINGS.items():
            default_list.append(
                MappingResponse(
                    user_id=user_id,
                    gesture=g_name,
                    action=d["action"],
                    sensitivity=d["sensitivity"],
                    confidence_threshold=d["confidence_threshold"],
                    cooldown_ms=d["cooldown_ms"],
                    enabled=d["enabled"],
                    description=d.get("description", "")
                )
            )
        return default_list

    return user_mappings


@router.post("/mappings", response_model=MappingResponse, status_code=status.HTTP_201_CREATED)
@router.post("/gestures", response_model=MappingResponse, status_code=status.HTTP_201_CREATED)
@router.put("/mappings/{gesture}", response_model=MappingResponse)
@router.put("/gestures/{gesture}", response_model=MappingResponse)
async def upsert_mapping(
    payload: MappingCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create or update a gesture mapping for the user."""
    user_id = current_user["user_id"]

    # Security check: verify action is in whitelist
    if not ActionRegistry.is_safe(payload.action):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Action '{payload.action}' is not in the safe actions whitelist."
        )

    doc_data = {
        "user_id": user_id,
        "gesture": payload.gesture,
        "action": payload.action,
        "sensitivity": payload.sensitivity,
        "confidence_threshold": payload.confidence_threshold,
        "cooldown_ms": payload.cooldown_ms,
        "enabled": payload.enabled,
        "description": payload.description or ""
    }

    mappings_coll = db_manager.get_mappings_collection()
    if mappings_coll is not None:
        await mappings_coll.update_one(
            {"user_id": user_id, "gesture": payload.gesture},
            {"$set": doc_data},
            upsert=True
        )
    else:
        if user_id not in db_manager._mock_mappings:
            db_manager._mock_mappings[user_id] = []
        # Replace existing or append
        db_manager._mock_mappings[user_id] = [
            m for m in db_manager._mock_mappings[user_id] if m["gesture"] != payload.gesture
        ]
        db_manager._mock_mappings[user_id].append(doc_data)

    return MappingResponse(**doc_data)


@router.delete("/mappings/{gesture}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/gestures/{gesture}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(gesture: str, current_user: dict = Depends(get_current_user)):
    """Reset a custom gesture mapping to default."""
    user_id = current_user["user_id"]
    mappings_coll = db_manager.get_mappings_collection()

    if mappings_coll is not None:
        await mappings_coll.delete_one({"user_id": user_id, "gesture": gesture})
    elif user_id in db_manager._mock_mappings:
        db_manager._mock_mappings[user_id] = [
            m for m in db_manager._mock_mappings[user_id] if m["gesture"] != gesture
        ]
    return None
