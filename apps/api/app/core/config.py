"""Application settings loaded from environment variables / .env file.

Never hardcode secrets. All config comes from here.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS_ORIGINS into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_dev(self) -> bool:
        return self.ENV == "dev"


settings = Settings()
