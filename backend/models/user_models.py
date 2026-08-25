"""
User Authentication Schemas
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class UserRegister(BaseModel):
    """Registration request payload."""
    email: str = Field(min_length=3, max_length=120)
    name: str = Field(min_length=2, max_length=60)
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    """Login request payload."""
    email: str = Field(min_length=3, max_length=120)
    password: str


class UserResponse(BaseModel):
    """User profile response."""
    user_id: str
    email: str
    name: str
    created_at: Optional[datetime] = None


class Token(BaseModel):
    """JWT Token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

