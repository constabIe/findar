"""
Utility functions for user authentication.

Provides password hashing/verification and JWT token generation/validation.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import bcrypt
import jwt

from src.config import settings


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password string
    """
    # Convert password to bytes
    password_bytes = password.encode("utf-8")

    # Generate salt and hash password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)

    # Return as string
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to verify against

    Returns:
        True if password matches, False otherwise
    """
    # Convert to bytes
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")

    # Verify password
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(user_id: UUID, email: str) -> str:
    """
    Create a JWT access token for a user.

    Args:
        user_id: User's unique identifier
        email: User's email address

    Returns:
        Encoded JWT token string
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode = {
        "sub": str(user_id),  # Subject: user ID
        "email": email,
        "exp": expire,  # Expiration time
        "iat": datetime.now(timezone.utc),  # Issued at
    }

    encoded_jwt = jwt.encode(
        to_encode, settings.jwt.SECRET_KEY, algorithm=settings.jwt.ALGORITHM
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT access token.

    Args:
        token: JWT token string to decode

    Returns:
        Decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token, settings.jwt.SECRET_KEY, algorithms=[settings.jwt.ALGORITHM]
        )
        return payload
    except jwt.InvalidTokenError:
        return None
