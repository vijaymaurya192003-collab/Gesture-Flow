"""
Authentication Routes
Endpoints for user registration, login, and profile fetching.
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends
from backend.models.user_models import UserRegister, UserLogin, UserResponse, Token
from backend.security import hash_password, verify_password, create_access_token, get_current_user
from backend.database import db_manager

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister):
    """Register a new user account."""
    email_clean = payload.email.lower().strip()
    users_coll = db_manager.get_users_collection()

    if users_coll is not None:
        try:
            existing = await users_coll.find_one({"email": email_clean})
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A user with this email address is already registered"
                )
            user_id = str(uuid.uuid4())
            user_doc = {
                "_id": user_id,
                "user_id": user_id,
                "email": email_clean,
                "name": payload.name.strip(),
                "password_hash": hash_password(payload.password),
                "created_at": datetime.now(timezone.utc)
            }
            await users_coll.insert_one(user_doc)
        except HTTPException:
            raise
        except Exception as exc:
            db_manager.record_failure(exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable during registration."
            )
    else:
        # In-memory mock fallback
        for u in db_manager._mock_users.values():
            if u["email"] == email_clean:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A user with this email address is already registered"
                )
        user_id = str(uuid.uuid4())
        user_doc = {
            "user_id": user_id,
            "email": email_clean,
            "name": payload.name.strip(),
            "password_hash": hash_password(payload.password),
            "created_at": datetime.now(timezone.utc)
        }
        db_manager._mock_users[user_id] = user_doc

    user_resp = UserResponse(
        user_id=user_id,
        email=email_clean,
        name=user_doc["name"],
        created_at=user_doc["created_at"]
    )
    token = create_access_token({"sub": user_id, "email": email_clean, "name": user_resp.name})
    return Token(access_token=token, token_type="bearer", user=user_resp)


@router.post("/login", response_model=Token)
async def login(payload: UserLogin):
    """Authenticate with email and password to receive JWT token."""
    email_clean = payload.email.lower().strip()
    users_coll = db_manager.get_users_collection()

    user_doc = None
    if users_coll is not None:
        try:
            user_doc = await users_coll.find_one({"email": email_clean})
        except Exception as exc:
            db_manager.record_failure(exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable during login."
            )
    else:
        for u in db_manager._mock_users.values():
            if u["email"] == email_clean:
                user_doc = u
                break

    if not user_doc or not verify_password(payload.password, user_doc["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = user_doc.get("user_id") or str(user_doc.get("_id"))
    user_resp = UserResponse(
        user_id=user_id,
        email=user_doc["email"],
        name=user_doc["name"],
        created_at=user_doc.get("created_at")
    )
    token = create_access_token({"sub": user_id, "email": user_doc["email"], "name": user_resp.name})
    return Token(access_token=token, token_type="bearer", user=user_resp)


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """Fetch profile of current authenticated user."""
    user_id = current_user["user_id"]
    users_coll = db_manager.get_users_collection()

    if users_coll is not None:
        try:
            user_doc = await users_coll.find_one({"_id": user_id})
        except Exception as exc:
            db_manager.record_failure(exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable."
            )
        if user_doc:
            return UserResponse(
                user_id=user_id,
                email=user_doc["email"],
                name=user_doc["name"],
                created_at=user_doc.get("created_at")
            )
    elif user_id in db_manager._mock_users:
        u = db_manager._mock_users[user_id]
        return UserResponse(
            user_id=user_id,
            email=u["email"],
            name=u["name"],
            created_at=u.get("created_at")
        )

    return UserResponse(
        user_id=user_id,
        email=current_user.get("email", ""),
        name=current_user.get("name", "User")
    )

