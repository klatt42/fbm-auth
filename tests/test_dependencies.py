"""Tests for FastAPI auth dependencies using a real in-memory SQLite database."""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from fastapi import Depends, FastAPI
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from fbm_auth.database import AuthBase, get_auth_session
from fbm_auth.dependencies import get_current_user, require_service_key
from fbm_auth.jwt import create_access_token, create_refresh_token
from fbm_auth.models import ServiceCredential, User
from fbm_auth.passwords import hash_password
from fbm_auth.router import auth_router

# --- In-memory SQLite engine for tests ---

test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@event.listens_for(test_engine.sync_engine, "connect")
def _enable_foreign_keys(dbapi_conn, connection_record):
    """SQLite needs explicit FK enforcement."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async def override_get_auth_session():
    async with test_session_factory() as session:
        yield session


# --- Test app ---

app = FastAPI()
app.include_router(auth_router, prefix="/v1/auth")
app.dependency_overrides[get_auth_session] = override_get_auth_session


@app.get("/v1/protected")
async def protected_endpoint(user: User = Depends(get_current_user)):
    return {"user_id": str(user.id), "email": user.email}


@app.get("/v1/service-only")
async def service_endpoint(service=Depends(require_service_key)):
    return {"service": service.name, "scopes": service.scopes}


# --- Fixtures ---

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(AuthBase.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(AuthBase.metadata.drop_all)


@pytest_asyncio.fixture
async def test_user() -> User:
    """Insert a test user and return it."""
    async with test_session_factory() as session:
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            hashed_password=hash_password("testpassword123"),
            name="Test User",
            subscription_tier="pro",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def service_cred() -> tuple[ServiceCredential, str]:
    """Insert a service credential and return (cred, raw_key)."""
    raw_key = "sk_test_supersecretkey123"
    async with test_session_factory() as session:
        cred = ServiceCredential(
            service_name="copilot_test",
            api_key_hash=hash_password(raw_key),
            scopes=["read:users", "write:fraud"],
        )
        session.add(cred)
        await session.commit()
        await session.refresh(cred)
        return cred, raw_key


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# --- Auth endpoint tests ---

@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    # Register
    resp = await client.post("/v1/auth/register", json={
        "email": "new@example.com",
        "password": "securepassword",
        "name": "New User",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@example.com"
    assert "id" in data

    # Login
    resp = await client.post("/v1/auth/login", json={
        "email": "new@example.com",
        "password": "securepassword",
    })
    assert resp.status_code == 200
    tokens = resp.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"
    assert tokens["expires_in"] > 0


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    await client.post("/v1/auth/register", json={
        "email": "dup@example.com",
        "password": "password123",
    })
    resp = await client.post("/v1/auth/register", json={
        "email": "dup@example.com",
        "password": "password456",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user: User):
    resp = await client.post("/v1/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, test_user: User):
    token, _ = create_access_token(str(test_user.id), tier="pro")
    resp = await client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert data["subscription_tier"] == "pro"


@pytest.mark.asyncio
async def test_refresh_token_flow(client: AsyncClient, test_user: User):
    refresh = create_refresh_token(str(test_user.id))
    resp = await client.post("/v1/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_with_access_token_rejected(client: AsyncClient, test_user: User):
    """Using an access token as refresh token should fail."""
    access, _ = create_access_token(str(test_user.id))
    resp = await client.post("/v1/auth/refresh", json={"refresh_token": access})
    assert resp.status_code == 401


# --- Protected endpoint tests ---

@pytest.mark.asyncio
async def test_protected_endpoint_with_valid_token(client: AsyncClient, test_user: User):
    token, _ = create_access_token(str(test_user.id))
    resp = await client.get("/v1/protected", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["user_id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client: AsyncClient):
    resp = await client.get("/v1/protected")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_invalid_token(client: AsyncClient):
    resp = await client.get("/v1/protected", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_refresh_token_rejected(client: AsyncClient, test_user: User):
    """Refresh tokens should not be accepted for protected endpoints."""
    refresh = create_refresh_token(str(test_user.id))
    resp = await client.get("/v1/protected", headers={"Authorization": f"Bearer {refresh}"})
    assert resp.status_code == 401


# --- Service auth tests ---

@pytest.mark.asyncio
async def test_service_endpoint_with_valid_key(client: AsyncClient, service_cred):
    _, raw_key = service_cred
    resp = await client.get("/v1/service-only", headers={"X-API-Key": raw_key})
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "copilot_test"
    assert "read:users" in data["scopes"]


@pytest.mark.asyncio
async def test_service_endpoint_without_key(client: AsyncClient):
    resp = await client.get("/v1/service-only")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_service_endpoint_with_invalid_key(client: AsyncClient, service_cred):
    resp = await client.get("/v1/service-only", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 403
