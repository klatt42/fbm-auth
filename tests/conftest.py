"""Shared test fixtures."""

import os

# Override settings BEFORE any fbm_auth imports
os.environ["FBM_AUTH_JWT_SECRET"] = "test-secret-key-for-unit-tests"
os.environ["FBM_AUTH_AUTH_DB_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["FBM_AUTH_ACCESS_TOKEN_MINUTES"] = "30"
os.environ["FBM_AUTH_REFRESH_TOKEN_DAYS"] = "7"
