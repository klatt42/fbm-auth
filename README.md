# fbm-auth

Shared authentication package for the FBM Copilot Suite. Provides unified user identity, JWT tokens, and service-to-service API key validation across all tools (Metrics, Guard, Inbox, Ads).

## Quick Start

### 1. Start the auth database

```bash
cd ~/projects/fbm-auth
docker compose up -d
```

This starts PostgreSQL on **port 5440** with database `fbm_auth`.

### 2. Run migrations

```bash
source .venv/bin/activate
alembic upgrade head
```

### 3. Install in your tool

```bash
# From your tool's venv:
pip install -e ~/projects/fbm-auth
```

### 4. Add env vars to your tool's `.env`

```env
FBM_AUTH_AUTH_DB_URL=postgresql+asyncpg://fbm_auth:fbm_auth_dev@localhost:5440/fbm_auth
FBM_AUTH_JWT_SECRET=your-shared-secret-here
FBM_AUTH_JWT_ALGORITHM=HS256
FBM_AUTH_ACCESS_TOKEN_MINUTES=30
FBM_AUTH_REFRESH_TOKEN_DAYS=7
FBM_AUTH_SERVICE_NAME=copilot_metrics
FBM_AUTH_SERVICE_API_KEY=sk_metrics_xxxxxxxxxxxx
```

### 5. Integrate with FastAPI

```python
from fastapi import FastAPI, Depends
from fbm_auth import auth_router, get_current_user, require_service_key, init_auth_db, close_auth_db

app = FastAPI()

# Mount shared auth endpoints
app.include_router(auth_router, prefix="/v1/auth")

@app.on_event("startup")
async def startup():
    await init_auth_db()

@app.on_event("shutdown")
async def shutdown():
    await close_auth_db()

# User-authenticated endpoint
@app.get("/v1/inventory")
async def list_inventory(user=Depends(get_current_user)):
    # user.id, user.email, user.subscription_tier available
    ...

# Service-to-service endpoint
@app.get("/integrations/loss-summary")
async def loss_summary(service=Depends(require_service_key)):
    # service.name, service.scopes, service.has_scope("read:fees")
    ...
```

## Auth Endpoints (mounted router)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/auth/register` | Create a new user |
| POST | `/v1/auth/login` | Get access + refresh tokens |
| POST | `/v1/auth/refresh` | Exchange refresh token for new pair |
| GET | `/v1/auth/me` | Get current user profile |

## JWT Token Format

**Access token** (30 min): `{ sub, type: "access", tier, exp, iss: "fbm-auth" }`

**Refresh token** (7 days): `{ sub, type: "refresh", exp, iss: "fbm-auth" }`

All tools share the same JWT secret, so a token from Metrics works in Guard.

## Service-to-Service Auth

Services authenticate to each other via `X-API-Key` header. Keys are stored hashed in the `service_credentials` table.

```python
# Service calling another service
import httpx

async def call_metrics_api():
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "http://localhost:8501/v1/fees/calculate",
            params={"price": 29.99, "category": "electronics"},
            headers={"X-API-Key": os.environ["FBM_SERVICE_API_KEY"]},
        )
        return resp.json()
```

## Database Schema

Three tables in the `fbm_auth` database (port 5440):

- **users** — Shared user identity (email, password, subscription tier, Stripe IDs)
- **service_credentials** — Service-to-service API keys with scopes
- **api_keys** — Per-user API keys for Business tier external integrations

## Development

```bash
# Setup
cd ~/projects/fbm-auth
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests (uses in-memory SQLite, no Docker needed)
pytest -v

# Run migrations against real DB
docker compose up -d
alembic upgrade head
```

## Exports

```python
from fbm_auth import (
    # Config
    FBMAuthSettings, settings,
    # Database
    init_auth_db, close_auth_db, get_auth_session,
    # Models
    User, ServiceCredential, APIKey,
    # Schemas
    UserCreate, UserLogin, UserResponse, Token, TokenPayload, RefreshRequest,
    # JWT
    create_access_token, create_refresh_token, decode_token,
    # Passwords
    hash_password, verify_password,
    # Dependencies (FastAPI Depends)
    get_current_user, require_service_key,
    # Router
    auth_router,
    # Service auth
    ServiceIdentity,
    # Middleware
    add_cors,
)
```
