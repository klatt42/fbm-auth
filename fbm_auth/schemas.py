"""Pydantic request/response models for auth endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# --- Request models ---

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# --- Response models ---

class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    is_active: bool
    is_verified: bool
    subscription_tier: str
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenPayload(BaseModel):
    sub: str  # user UUID as string
    type: str  # "access" or "refresh"
    tier: str | None = None
    exp: int
    iss: str = "fbm-auth"
