# backend/app/core/config.py
"""Application configuration from environment variables."""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import os


# Development-only defaults — MUST be overridden in production.
_DEV_JWT = "dev-jwt-secret-key-change-in-production-0123456789"
_DEV_CSRF = "dev-csrf-secret-key-change-in-prod-9876543210"


class Settings(BaseSettings):
    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")

    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./data/app.db", validation_alias="DATABASE_URL")

    # Auth / JWT
    jwt_secret: str = Field(default=_DEV_JWT, min_length=32, validation_alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours
    csrf_secret: str = Field(default=_DEV_CSRF, min_length=32, validation_alias="CSRF_SECRET")

    # Keycloak / OIDC
    keycloak_url: str = Field(default="http://localhost:8080", validation_alias="KEYCLOAK_URL")
    keycloak_realm: str = Field(default="cloud-infra", validation_alias="KEYCLOAK_REALM")
    keycloak_client_id: str = Field(default="cloud-infra-planner", validation_alias="KEYCLOAK_CLIENT_ID")
    keycloak_client_secret: Optional[str] = Field(default=None, validation_alias="KEYCLOAK_CLIENT_SECRET")

    # LLM
    llm_provider: str = Field(default="openai", validation_alias="LLM_PROVIDER")
    llm_model: str = Field(default="gpt-4o", validation_alias="LLM_MODEL")
    llm_base_url: str = Field(default="https://api.openai.com/v1", validation_alias="LLM_BASE_URL")
    llm_api_key: Optional[str] = Field(default=None, validation_alias="LLM_API_KEY")

    # Demo mode (localhost only)
    demo_mode: bool = Field(default=False, validation_alias="DEMO_MODE")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "populate_by_name": True,
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def validate_production_settings(s: Settings) -> None:
    """Refuse to run in production with dev defaults or demo mode."""
    if s.environment == "production":
        if s.jwt_secret == _DEV_JWT:
            raise RuntimeError("JWT_SECRET must be set in production")
        if s.csrf_secret == _DEV_CSRF:
            raise RuntimeError("CSRF_SECRET must be set in production")
        if s.demo_mode:
            raise RuntimeError("DEMO_MODE is refused in production; bind to localhost in development only")