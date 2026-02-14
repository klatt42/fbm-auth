"""Tests for JWT creation and validation."""

import time
import uuid
from unittest.mock import patch

import pytest

from fbm_auth.jwt import create_access_token, create_refresh_token, decode_token


def test_access_token_roundtrip():
    user_id = str(uuid.uuid4())
    token, expires_in = create_access_token(user_id, tier="pro")

    payload = decode_token(token)
    assert payload.sub == user_id
    assert payload.type == "access"
    assert payload.tier == "pro"
    assert payload.iss == "fbm-auth"
    assert expires_in == 30 * 60  # 30 minutes in seconds


def test_refresh_token_roundtrip():
    user_id = str(uuid.uuid4())
    token = create_refresh_token(user_id)

    payload = decode_token(token)
    assert payload.sub == user_id
    assert payload.type == "refresh"
    assert payload.iss == "fbm-auth"


def test_expired_token_rejected():
    """Tokens with past expiration should be rejected."""
    from datetime import datetime, timedelta, timezone
    from jose import jwt as jose_jwt
    from fbm_auth.config import settings

    expired_payload = {
        "sub": str(uuid.uuid4()),
        "type": "access",
        "tier": "free",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "iss": "fbm-auth",
    }
    token = jose_jwt.encode(expired_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    with pytest.raises(ValueError, match="Invalid token"):
        decode_token(token)


def test_wrong_secret_rejected():
    """Tokens signed with a different secret should be rejected."""
    from jose import jwt as jose_jwt
    from datetime import datetime, timedelta, timezone

    payload = {
        "sub": str(uuid.uuid4()),
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iss": "fbm-auth",
    }
    token = jose_jwt.encode(payload, "wrong-secret", algorithm="HS256")

    with pytest.raises(ValueError, match="Invalid token"):
        decode_token(token)


def test_wrong_issuer_rejected():
    """Tokens with wrong issuer should be rejected."""
    from jose import jwt as jose_jwt
    from datetime import datetime, timedelta, timezone
    from fbm_auth.config import settings

    payload = {
        "sub": str(uuid.uuid4()),
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iss": "someone-else",
    }
    token = jose_jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    with pytest.raises(ValueError, match="Invalid token issuer"):
        decode_token(token)


def test_default_tier_is_free():
    user_id = str(uuid.uuid4())
    token, _ = create_access_token(user_id)

    payload = decode_token(token)
    assert payload.tier == "free"


def test_access_and_refresh_tokens_differ():
    user_id = str(uuid.uuid4())
    access, _ = create_access_token(user_id)
    refresh = create_refresh_token(user_id)
    assert access != refresh
