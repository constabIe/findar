"""
Application configuration management.

This module provides centralized configuration using pydantic-settings
that reads from .env file in the project root.
"""

from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Find project root (where .env is located)
PROJECT_ROOT = Path(__file__).parent.parent


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    POSTGRES_DB: str = Field(default="findar")
    POSTGRES_USER: str = Field(default="postgres")
    POSTGRES_PASSWORD: str = Field(default="postgres")
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_ASYNC_URL: Optional[str] = Field(default=None)

    @field_validator("POSTGRES_ASYNC_URL", mode="before")
    @classmethod
    def build_postgres_url(cls, v: Optional[str], info) -> str:
        """Build PostgreSQL async URL if not provided."""
        if v:
            return v

        # Access other fields from info.data
        data = info.data
        user = data.get("POSTGRES_USER", "")
        password = data.get("POSTGRES_PASSWORD", "")
        host = data.get("POSTGRES_HOST", "")
        port = data.get("POSTGRES_PORT", -1)
        db = data.get("POSTGRES_DB", "")

        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


class RedisSettings(BaseSettings):
    """Redis configuration settings."""

    REDIS_HOST: str = Field(default="redis")
    REDIS_PORT: int = Field(default=6379)
    REDIS_DB: int = Field(default=0)
    REDIS_PASSWORD: str = Field(default="")

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""

    level: str = Field(default="INFO")
    json_format: bool = Field(default=False)
    enable_console: bool = Field(default=True)
    enable_file: bool = Field(default=False)
    file_path: str = Field(default="logs/findar.log")

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class BackendSettings(BaseSettings):
    """Backend service configuration."""

    BACKEND_HOST: str = Field(default="localhost")
    BACKEND_PORT: int = Field(default=8001)

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


class GrafanaSettings(BaseSettings):
    """Grafana configuration settings."""

    GF_SECURITY_ADMIN_USER: str = Field(default="admin")
    GF_SECURITY_ADMIN_PASSWORD: str = Field(default="admin")
    GF_PORT: int = Field(default=3000)

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


class NotificationSettings(BaseSettings):
    """Notification service configuration."""

    TELEGRAM_BOT_TOKEN: str = Field(default="")
    EMAIL_SMTP_USER: str = Field(default="")

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


class JWTSettings(BaseSettings):
    """JWT authentication configuration."""

    SECRET_KEY: str = Field(
        default="your-secret-key-please-change-in-production-at-least-32-characters-long",
        description="Secret key for JWT token signing"
    )
    ALGORITHM: str = Field(
        default="HS256",
        description="JWT encoding algorithm"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60 * 24,  # 24 hours
        description="Access token expiration time in minutes"
    )

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


class Settings(BaseSettings):
    """Main application settings."""

    # Sub-configurations
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    backend: BackendSettings = Field(default_factory=BackendSettings)
    grafana: GrafanaSettings = Field(default_factory=GrafanaSettings)
    notifications: NotificationSettings = Field(default_factory=NotificationSettings)
    jwt: JWTSettings = Field(default_factory=JWTSettings)

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Global settings instance
settings = Settings()
