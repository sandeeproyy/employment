"""
AutoApply — Application Configuration

Loads settings from environment variables / .env file.
Uses pydantic-settings for type-safe configuration.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ─────────────────────────────────────────
    app_name: str = "AutoApply"
    debug: bool = True
    secret_key: str = "change-this-to-a-random-secret-key"

    # ── Database ─────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://autoapply:autoapply@db:5432/autoapply"
    database_url_sync: str = "postgresql://autoapply:autoapply@db:5432/autoapply"

    # ── Redis ────────────────────────────────────────────────
    redis_url: str = "redis://redis:6379/0"

    # ── AI Provider (Google Gemini) ──────────────────────────
    gemini_api_key: str = ""

    # ── CORS ─────────────────────────────────────────────────
    frontend_url: str = "http://localhost:3000"

    # ── File Storage ─────────────────────────────────────────
    upload_dir: str = "./uploads"
    generated_dir: str = "./generated"

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def generated_path(self) -> Path:
        path = Path(self.generated_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    # ── Celery ───────────────────────────────────────────────
    @property
    def celery_broker_url(self) -> str:
        return self.redis_url

    @property
    def celery_result_backend(self) -> str:
        return self.redis_url


# Singleton settings instance
settings = Settings()
