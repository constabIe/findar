"""
Pydantic schemas for user-related requests and responses.

Defines data transfer objects (DTOs) for user registration, login,
and user information.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """Schema for user registration."""

    email: EmailStr = Field(
        ...,
        description="User's email address (used for login)"
    )
    password: str = Field(
        ...,
        min_length=1,
        description="User's password (minimum 6 characters)"
    )
    telegram_alias: str = Field(
        ...,
        min_length=3,
        description="Telegram username (without @)"
    )

    @field_validator("telegram_alias")
    @classmethod
    def validate_telegram_alias(cls, v: str) -> str:
        """Remove @ prefix if present and validate."""
        # Remove @ if user accidentally included it
        if v.startswith("@"):
            v = v[1:]

        # Validate length after removing @
        if len(v) < 3:
            raise ValueError("Telegram alias must be at least 3 characters")

        return v.lower()  # Store in lowercase for consistency


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr = Field(
        ...,
        description="User's email address"
    )
    password: str = Field(
        ...,
        description="User's password"
    )


class TokenResponse(BaseModel):
    """Schema for authentication token response."""

    access_token: str = Field(
        ...,
        description="JWT access token"
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')"
    )


class UserResponse(BaseModel):
    """Schema for user information response."""

    id: UUID = Field(
        ...,
        description="User's unique identifier"
    )
    email: str = Field(
        ...,
        description="User's email address"
    )
    telegram_alias: str = Field(
        ...,
        description="Telegram username"
    )
    telegram_id: Optional[int] = Field(
        default=None,
        description="Telegram user ID (if bot started)"
    )
    created_at: datetime = Field(
        ...,
        description="Account creation timestamp"
    )

    class Config:
        """Pydantic configuration."""
        from_attributes = True  # Enable ORM mode for SQLModel compatibility
