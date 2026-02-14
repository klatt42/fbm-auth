"""Service-to-service API key validation."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fbm_auth.models import ServiceCredential
from fbm_auth.passwords import verify_password


class ServiceIdentity:
    """Represents an authenticated service after API key validation."""

    def __init__(self, name: str, scopes: list[str] | None):
        self.name = name
        self.scopes = scopes or []

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes


async def validate_service_key(api_key: str, session: AsyncSession) -> ServiceIdentity | None:
    """Validate a service API key and return the service identity.

    Returns None if the key is invalid or the service is inactive.
    """
    result = await session.execute(
        select(ServiceCredential).where(ServiceCredential.is_active == True)  # noqa: E712
    )
    credentials = result.scalars().all()

    for cred in credentials:
        if verify_password(api_key, cred.api_key_hash):
            # Update last_used_at
            cred.last_used_at = datetime.now(timezone.utc)
            await session.commit()
            return ServiceIdentity(name=cred.service_name, scopes=cred.scopes)

    return None
