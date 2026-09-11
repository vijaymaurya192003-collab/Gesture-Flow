"""
Gesture Mapping Routes
CRUD endpoints for managing user gesture-to-action mappings.
Provides 100% interoperability between /gestures and /mappings endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Path
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
        try:
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
        except Exception as exc:
            db_manager.record_failure(exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable while fetching mappings."
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
async def create_mapping(
    payload: MappingCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create or replace a gesture mapping for the user."""
    return await _save_mapping_document(payload.gesture, payload, current_user["user_id"], is_path_param=False)


@router.put("/mappings/{gesture}", response_model=MappingResponse)
@router.put("/gestures/{gesture}", response_model=MappingResponse)
async def update_mapping_by_path(
    gesture: str,
    payload: MappingCreate,
    current_user: dict = Depends(get_current_user)
):
    """Update a specific gesture mapping by path parameter."""
    if payload.gesture and payload.gesture.strip() != gesture.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Conflicting resource identifiers: URL specifies '{gesture}' but body specifies '{payload.gesture}'."
        )
    return await _save_mapping_document(gesture, payload, current_user["user_id"], is_path_param=True)


async def _save_mapping_document(gesture_key: str, payload: MappingCreate, user_id: str, is_path_param: bool = False) -> MappingResponse:
    """Internal helper to persist gesture mapping."""
    target_gesture = gesture_key if is_path_param else (payload.gesture or gesture_key)

    # Security check: verify action is in whitelist
    if not ActionRegistry.is_safe(payload.action):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Action '{payload.action}' is not in the safe actions whitelist."
        )

    doc_data = {
        "user_id": user_id,
        "gesture": target_gesture,
        "action": payload.action,
        "sensitivity": payload.sensitivity,
        "confidence_threshold": payload.confidence_threshold,
        "cooldown_ms": payload.cooldown_ms,
        "enabled": payload.enabled,
        "description": payload.description or ""
    }

    mappings_coll = db_manager.get_mappings_collection()
    if mappings_coll is not None:
        try:
            await mappings_coll.update_one(
                {"user_id": user_id, "gesture": target_gesture},
                {"$set": doc_data},
                upsert=True
            )
        except Exception as exc:
            db_manager.record_failure(exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable: failed to save mapping."
            )
    else:
        if user_id not in db_manager._mock_mappings:
            db_manager._mock_mappings[user_id] = []
        db_manager._mock_mappings[user_id] = [
            m for m in db_manager._mock_mappings[user_id] if m["gesture"] != target_gesture
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
        try:
            await mappings_coll.delete_one({"user_id": user_id, "gesture": gesture})
        except Exception as exc:
            db_manager.record_failure(exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable: failed to delete mapping."
            )
    elif user_id in db_manager._mock_mappings:
        db_manager._mock_mappings[user_id] = [
            m for m in db_manager._mock_mappings[user_id] if m["gesture"] != gesture
        ]
    return None
