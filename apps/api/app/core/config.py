"""Application settings loaded from environment variables / .env file.

Never hardcode secrets. All config comes from here.
"""

from __future__ import annotations

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Dev-only fallback secret. Booting in prod with this value is refused below.
_DEV_JWT_SECRET = "dev-insecure-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database — must use postgresql+asyncpg:// for async driver
    DATABASE_URL: str = "postgresql+asyncpg://chronoflow:chronoflow@localhost:5432/chronoflow"

    # CORS: comma-separated list of allowed origins
    CORS_ORIGINS: str = "http://localhost:5173"

    # Environment: dev | prod
    ENV: str = "dev"

    # ── Auth ───────────────────────────────────────────────────────────────
    # JWT signing secret (HS256). MUST be set from env in prod — see guard below.
    JWT_SECRET: str = _DEV_JWT_SECRET
    JWT_EXPIRE_MINUTES: int = 60
    # Session cookie name carrying the JWT (httpOnly).
    AUTH_COOKIE_NAME: str = "chronoflow_session"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS_ORIGINS into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_dev(self) -> bool:
        return self.ENV == "dev"

    @property
    def cookie_secure(self) -> bool:
        """Send the auth cookie only over HTTPS in prod (http in dev)."""
        return not self.is_dev

    @model_validator(mode="after")
    def _require_prod_secret(self) -> Settings:
        if not self.is_dev and self.JWT_SECRET == _DEV_JWT_SECRET:
            raise ValueError("JWT_SECRET must be set from env when ENV=prod")
        return self


settings = Settings()
