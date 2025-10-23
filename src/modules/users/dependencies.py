"""
FastAPI dependencies for user authentication and authorization.

Provides dependency injection for protected endpoints that require
authenticated users.
"""

from typing import Annotated, AsyncGenerator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.dependencies import AsyncDbSessionDep
from src.storage.models import User
from src.storage.sql.engine import get_async_session

from .repository import UserRepository
from .utils import decode_access_token

# Bearer token authentication scheme
security = HTTPBearer()


def get_user_repository(session: AsyncDbSessionDep) -> UserRepository:
    """Get user repository instance with database dependency."""
    return UserRepository(session)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    repo: UserRepository = Depends(get_user_repository),
) -> User:
    """
    Get the current authenticated user from JWT token.

    This dependency extracts the JWT token from the Authorization header,
    validates it, and retrieves the corresponding user from the database.

    Args:
        credentials: Bearer token from Authorization header
        repo: User repository

    Returns:
        User object for the authenticated user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    # Extract token from credentials
    token = credentials.credentials

    # Decode and validate token
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user ID from token
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Convert string ID to UUID
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user = await repo.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_transaction_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session for transaction operations.

    This is a convenience wrapper around the storage layer's
    get_async_session function, specifically for the transactions module.

    Yields:
        AsyncSession: Async SQLAlchemy session
    """
    async for session in get_async_session():
        yield session


# Type alias for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
AsyncSessionDep = Annotated[AsyncSession, Depends(get_transaction_db_session)]
