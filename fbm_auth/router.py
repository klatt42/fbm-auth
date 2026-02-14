"""Mountable auth router: /auth/register, /auth/login, /auth/refresh, /auth/me."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fbm_auth.database import get_auth_session
from fbm_auth.dependencies import get_current_user
from fbm_auth.jwt import create_access_token, create_refresh_token, decode_token
from fbm_auth.models import User
from fbm_auth.passwords import hash_password, verify_password
from fbm_auth.schemas import RefreshRequest, Token, UserCreate, UserLogin, UserResponse

auth_router = APIRouter(tags=["auth"])


@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate,
    session: AsyncSession = Depends(get_auth_session),
):
    """Register a new user."""
    # Check email uniqueness
    result = await session.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        name=data.name,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@auth_router.post("/login", response_model=Token)
async def login(
    data: UserLogin,
    session: AsyncSession = Depends(get_auth_session),
):
    """Authenticate and return access + refresh tokens."""
    result = await session.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    access_token, expires_in = create_access_token(str(user.id), tier=user.subscription_tier)
    refresh_token = create_refresh_token(str(user.id))

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


@auth_router.post("/refresh", response_model=Token)
async def refresh(
    data: RefreshRequest,
    session: AsyncSession = Depends(get_auth_session),
):
    """Exchange a refresh token for a new access + refresh token pair."""
    try:
        payload = decode_token(data.refresh_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if payload.type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not a refresh token",
        )

    import uuid
    result = await session.execute(select(User).where(User.id == uuid.UUID(payload.sub)))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    access_token, expires_in = create_access_token(str(user.id), tier=user.subscription_tier)
    new_refresh = create_refresh_token(str(user.id))

    return Token(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in=expires_in,
    )


@auth_router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Return the current authenticated user."""
    return user
