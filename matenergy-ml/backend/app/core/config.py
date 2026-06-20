"""
Application settings loaded from environment variables via pydantic-settings.

All fields with no default are **required** at startup.  Missing required
fields cause an immediate ``ValidationError`` with a clear description of
what is missing — fail fast rather than fail mysteriously at request time.

Precedence (highest to lowest):
  1. Actual environment variables
  2. Values from the .env file
  3. Pydantic field defaults

The ``settings`` singleton at module level is the single source of truth
throughout the codebase.  Import it as:
    from app.core.config import settings
"""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # silently drop unknown env vars rather than erroring
        case_sensitive=True,
    )

    # -----------------------------------------------------------------------
    # Application
    # -----------------------------------------------------------------------
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "MatEnergy-ML"
    API_V1_PREFIX: str = "/api/v1"

    # -----------------------------------------------------------------------
    # Database
    # -----------------------------------------------------------------------
    POSTGRES_USER: str = "matenergy"
    POSTGRES_PASSWORD: str = Field(..., description="PostgreSQL password — required")
    POSTGRES_DB: str = "matenergy_db"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> str:
        """Async-compatible SQLAlchemy connection string."""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # -----------------------------------------------------------------------
    # JWT / Security
    # -----------------------------------------------------------------------
    SECRET_KEY: str = Field(..., description="General application secret key — required")
    JWT_SECRET_KEY: str = Field(..., description="Key used to sign JWT tokens — required")
    JWT_ISSUER: str = "matenergy-ml"
    JWT_AUDIENCE: str = "matenergy-ml-users"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # -----------------------------------------------------------------------
    # CORS
    # Kept as str so pydantic-settings 2.x doesn't attempt JSON-parsing.
    # Use the `cors_origins` property everywhere, not this field directly.
    # -----------------------------------------------------------------------
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]

    # -----------------------------------------------------------------------
    # Rate limiting / brute-force protection
    # -----------------------------------------------------------------------
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # -----------------------------------------------------------------------
    # File upload
    # -----------------------------------------------------------------------
    MAX_UPLOAD_SIZE_MB: int = 50
    MAX_ROWS_PER_DATASET: int = 100_000

    # -----------------------------------------------------------------------
    # Scientific / ML defaults
    # -----------------------------------------------------------------------
    STABILITY_THRESHOLD_EV: float = 0.05   # eV/atom — boundary for "stable" label
    MIN_TRAINING_SAMPLES: int = 20

    # -----------------------------------------------------------------------
    # Storage paths
    # -----------------------------------------------------------------------
    ARTIFACT_STORAGE_PATH: str = "./artifacts"
    DATA_STORAGE_PATH: str = "./data"

    # -----------------------------------------------------------------------
    # Logging
    # -----------------------------------------------------------------------
    LOG_LEVEL: str = "INFO"
    AUDIT_LOG_ENABLED: bool = True

    # -----------------------------------------------------------------------
    # External APIs (all optional — empty string disables the integration)
    # -----------------------------------------------------------------------
    MATERIALS_PROJECT_API_KEY: str = ""
    JARVIS_API_KEY: str = ""
    NOMAD_TOKEN: str = ""

    # -----------------------------------------------------------------------
    # Redis (optional — empty string disables Redis-backed features)
    # -----------------------------------------------------------------------
    REDIS_URL: str = ""


# Module-level singleton — import this everywhere
settings = Settings()  # type: ignore[call-arg]
