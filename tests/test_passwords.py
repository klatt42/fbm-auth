"""Tests for password hashing and verification."""

from fbm_auth.passwords import hash_password, verify_password


def test_hash_and_verify():
    plain = "my-secure-password"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)


def test_wrong_password_fails():
    hashed = hash_password("correct-password")
    assert not verify_password("wrong-password", hashed)


def test_different_hashes_for_same_password():
    """Bcrypt generates unique salts each time."""
    h1 = hash_password("same-password")
    h2 = hash_password("same-password")
    assert h1 != h2
    assert verify_password("same-password", h1)
    assert verify_password("same-password", h2)


def test_empty_password_hashes():
    """Empty strings are valid bcrypt input (edge case)."""
    hashed = hash_password("")
    assert verify_password("", hashed)
    assert not verify_password("not-empty", hashed)
