"""
Dependencies for the transactions module.

Provides FastAPI dependency injection for database sessions
and other resources needed by transaction endpoints.
"""

from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.sql import get_async_session

# Type alias for AsyncSession dependency
AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


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
