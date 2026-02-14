"""One-time migration: copy users from Metrics DB (port 5434) to shared auth DB (port 5440).

Preserves original UUIDs so all existing foreign keys remain valid.

Usage:
    cd ~/projects/fbm-auth
    source .venv/bin/activate
    python migrate_users_to_shared_auth.py
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Source: Metrics operational DB
METRICS_DB_URL = "postgresql+asyncpg://sellermetrics:password@localhost:5434/sellermetrics"

# Target: Shared auth DB
AUTH_DB_URL = "postgresql+asyncpg://fbm_auth:fbm_auth_dev@localhost:5440/fbm_auth"


async def migrate():
    source_engine = create_async_engine(METRICS_DB_URL)
    target_engine = create_async_engine(AUTH_DB_URL)

    source_session_factory = async_sessionmaker(source_engine, class_=AsyncSession)
    target_session_factory = async_sessionmaker(target_engine, class_=AsyncSession)

    # Read all users from Metrics DB
    async with source_session_factory() as source:
        result = await source.execute(text(
            "SELECT id, email, hashed_password, name, subscription_tier, created_at, updated_at FROM users"
        ))
        users = result.fetchall()

    print(f"Found {len(users)} users in Metrics DB")

    # Insert into auth DB
    migrated = 0
    skipped = 0
    async with target_session_factory() as target:
        for user in users:
            # Check if already exists (idempotent)
            existing = await target.execute(
                text("SELECT id FROM users WHERE id = :id OR email = :email"),
                {"id": user.id, "email": user.email},
            )
            if existing.scalar_one_or_none() is not None:
                print(f"  SKIP: {user.email} (already exists)")
                skipped += 1
                continue

            await target.execute(
                text("""
                    INSERT INTO users (id, email, hashed_password, name, subscription_tier, created_at, updated_at)
                    VALUES (:id, :email, :hashed_password, :name, :subscription_tier, :created_at, :updated_at)
                """),
                {
                    "id": user.id,
                    "email": user.email,
                    "hashed_password": user.hashed_password,
                    "name": user.name,
                    "subscription_tier": user.subscription_tier,
                    "created_at": user.created_at,
                    "updated_at": user.updated_at,
                },
            )
            print(f"  MIGRATED: {user.email} ({user.id})")
            migrated += 1

        await target.commit()

    print(f"\nDone: {migrated} migrated, {skipped} skipped")

    # Verify
    async with target_session_factory() as target:
        result = await target.execute(text("SELECT id, email FROM users ORDER BY email"))
        auth_users = result.fetchall()
        print(f"\nAuth DB now has {len(auth_users)} users:")
        for u in auth_users:
            print(f"  {u.email} ({u.id})")

    await source_engine.dispose()
    await target_engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate())
