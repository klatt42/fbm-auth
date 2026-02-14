"""FastAPI dependencies for auth: get_current_user, require_service_key."""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fbm_auth.database import get_auth_session
from fbm_auth.jwt import decode_token
from fbm_auth.models import User
from fbm_auth.service_auth import ServiceIdentity, validate_service_key

bearer_scheme = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_auth_session),
) -> User:
    """Validate JWT and return the current user. Use as a FastAPI Depends().

    Raises 401 if the token is invalid/expired or user is inactive.
    """
    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type — use an access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = uuid.UUID(payload.sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def require_service_key(
    api_key: str | None = Depends(api_key_header),
    session: AsyncSession = Depends(get_auth_session),
) -> ServiceIdentity:
    """Validate X-API-Key header for service-to-service calls.

    Raises 403 if the key is missing/invalid.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-API-Key header",
        )

    service = await validate_service_key(api_key, session)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return service
