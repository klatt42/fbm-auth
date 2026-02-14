"""Password hashing and verification via passlib.

Uses passlib's CryptContext which is backward-compatible with raw bcrypt
hashes from Seller-Metrics while also supporting the Inbox pattern.
"""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a plaintext password."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a hash."""
    return pwd_context.verify(plain, hashed)
