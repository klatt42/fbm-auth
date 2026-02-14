"""FBM Shared Auth — unified identity for FBM Copilot Suite tools.

Usage in any tool's main.py:

    from fbm_auth import auth_router, get_current_user, require_service_key, init_auth_db

    app = FastAPI()
    app.include_router(auth_router, prefix="/v1/auth")

    @app.on_event("startup")
    async def startup():
        await init_auth_db()
"""

from fbm_auth.config import FBMAuthSettings, settings
from fbm_auth.database import close_auth_db, get_auth_session, init_auth_db
from fbm_auth.dependencies import get_current_user, require_service_key
from fbm_auth.jwt import create_access_token, create_refresh_token, decode_token
from fbm_auth.middleware import add_cors
from fbm_auth.models import APIKey, ServiceCredential, User
from fbm_auth.passwords import hash_password, verify_password
from fbm_auth.router import auth_router
from fbm_auth.schemas import RefreshRequest, Token, TokenPayload, UserCreate, UserLogin, UserResponse
from fbm_auth.service_auth import ServiceIdentity

__all__ = [
    # Config
    "FBMAuthSettings",
    "settings",
    # Database
    "init_auth_db",
    "close_auth_db",
    "get_auth_session",
    # Models
    "User",
    "ServiceCredential",
    "APIKey",
    # Schemas
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "Token",
    "TokenPayload",
    "RefreshRequest",
    # JWT
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    # Passwords
    "hash_password",
    "verify_password",
    # Dependencies
    "get_current_user",
    "require_service_key",
    # Router
    "auth_router",
    # Service auth
    "ServiceIdentity",
    # Middleware
    "add_cors",
]
