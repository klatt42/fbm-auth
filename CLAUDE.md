# FBM Auth - Shared Authentication Package

## What This Is

Shared authentication package for the FBM Copilot Suite. Provides unified user identity, JWT tokens, and service-to-service API key validation across all FBM tools (Metrics, Guard, Inbox, Ads).

## Tech Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI 0.109.0+ (async)
- **Database**: PostgreSQL 16 (Docker, port 5440) / SQLite (testing)
- **ORM**: SQLAlchemy 2.0+ async (asyncpg + aiosqlite)
- **JWT**: python-jose with HS256
- **Passwords**: passlib + bcrypt
- **Migrations**: Alembic 1.13.0+
- **Config**: Pydantic v2 BaseSettings (`FBM_AUTH_` prefix)

## Structure

```
fbm_auth/              # Main package
  config.py            # FBMAuthSettings (Pydantic BaseSettings)
  database.py          # Engine, session factory, lifecycle
  models.py            # User, ServiceCredential, APIKey (SQLAlchemy ORM)
  schemas.py           # Pydantic request/response models
  router.py            # /v1/auth endpoints (register/login/refresh/me)
  jwt.py               # Token creation/decoding
  dependencies.py      # get_current_user, require_service_key (FastAPI Depends)
  service_auth.py      # ServiceIdentity, validate_service_key()
  passwords.py         # hash_password(), verify_password()
  middleware.py         # add_cors() helper
alembic/               # Database migrations
tests/                 # pytest (in-memory SQLite, no Docker needed)
```

## Database (Port 5440)

Three tables with UUID PKs: `users`, `service_credentials`, `api_keys`.

## Auth Endpoints (mounted at /v1/auth)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/register` | Create user (201) |
| POST | `/login` | Get access + refresh tokens |
| POST | `/refresh` | Rotate token pair |
| GET | `/me` | Current user profile |

## JWT Tokens

- **Access**: 30min, `{ sub, type: "access", tier, exp, iss: "fbm-auth" }`
- **Refresh**: 7 days, `{ sub, type: "refresh", exp, iss: "fbm-auth" }`
- Shared HS256 secret across all FBM tools

## Integration Pattern

```python
# In another FBM tool:
pip install -e ~/projects/fbm-auth

from fbm_auth import auth_router, init_auth_db, get_current_user, add_cors
app.include_router(auth_router, prefix="/v1/auth")

@app.get("/protected")
async def endpoint(user: User = Depends(get_current_user)):
    ...
```

## Environment (.env)

```
FBM_AUTH_AUTH_DB_URL=postgresql+asyncpg://fbm_auth:fbm_auth_dev@localhost:5440/fbm_auth
FBM_AUTH_JWT_SECRET=your-shared-secret
FBM_AUTH_JWT_ALGORITHM=HS256
FBM_AUTH_ACCESS_TOKEN_MINUTES=30
FBM_AUTH_REFRESH_TOKEN_DAYS=7
FBM_AUTH_SERVICE_NAME=copilot_metrics
FBM_AUTH_SERVICE_API_KEY=sk_metrics_xxxx
```

## Dev Commands

```bash
source .venv/bin/activate
pip install -e ".[dev]"
docker compose up -d                    # PostgreSQL on 5440
alembic upgrade head                    # Run migrations
pytest -v                               # Tests (SQLite, no Docker)
alembic revision --autogenerate -m "x"  # New migration
```

## Conventions

- Tables: snake_case (`service_credentials`)
- Functions: snake_case (`create_access_token`)
- Classes: PascalCase (`FBMAuthSettings`)
- API keys prefixed: `sk_`
- 100% async/await
- `StringList` TypeDecorator handles ARRAY (Postgres) vs JSON (SQLite)
- Editable install (`pip install -e`), not PyPI
