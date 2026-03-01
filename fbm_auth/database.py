"""Auth database engine and session factory."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from fbm_auth.config import settings

engine = create_async_engine(settings.auth_db_url, echo=False)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class AuthBase(DeclarativeBase):
    """Base class for all auth DB models."""
    pass


async def init_auth_db() -> None:
    """Initialize the auth database connection. Call on app startup."""
    # Connection pool is lazy — this just validates the URL is reachable.
    async with engine.begin():
        pass


async def close_auth_db() -> None:
    """Dispose of the auth database engine. Call on app shutdown."""
    await engine.dispose()


async def get_auth_session() -> AsyncSession:
    """Yield an async session for the auth database. Use as a FastAPI dependency."""
    async with async_session_factory() as session:
        yield session
