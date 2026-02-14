"""FBM Auth configuration via environment variables."""

from pydantic_settings import BaseSettings


class FBMAuthSettings(BaseSettings):
    """Shared auth settings. Each tool adds these to its .env file."""

    # Database
    auth_db_url: str = "postgresql+asyncpg://fbm_auth:fbm_auth_dev@localhost:5440/fbm_auth"

    # JWT
    jwt_secret: str = "change-me-in-production-use-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 7

    # Service-to-service
    service_name: str = ""
    service_api_key: str = ""

    model_config = {
        "env_prefix": "FBM_AUTH_",
    }


# Singleton instance — import this in other modules
settings = FBMAuthSettings()
