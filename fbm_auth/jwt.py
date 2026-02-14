"""JWT creation and validation for access and refresh tokens."""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from fbm_auth.config import settings
from fbm_auth.schemas import TokenPayload


def create_access_token(user_id: str, tier: str = "free") -> tuple[str, int]:
    """Create a short-lived access token.

    Returns (token_string, expires_in_seconds).
    """
    expires_in = settings.access_token_minutes * 60
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    payload = {
        "sub": user_id,
        "type": "access",
        "tier": tier,
        "exp": expire,
        "iss": "fbm-auth",
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_in


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "iss": "fbm-auth",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> TokenPayload:
    """Decode and validate a JWT token.

    Raises ValueError on invalid/expired tokens.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e

    if payload.get("iss") != "fbm-auth":
        raise ValueError("Invalid token issuer")

    return TokenPayload(
        sub=payload["sub"],
        type=payload.get("type", "access"),
        tier=payload.get("tier"),
        exp=payload["exp"],
        iss=payload.get("iss", "fbm-auth"),
    )
