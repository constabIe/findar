"""
Storage dependencies for FastAPI dependency injection.

This module provides centralized access to async database sessions and Redis clients
for the fraud detection system components.
"""

from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends
from redis import Redis as SyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from .redis import get_async_redis_dependency, get_sync_redis_dependency
from .sql import get_async_session

# Type aliases for direct use in FastAPI endpoints
AsyncDbSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


# Convenience functions for explicit dependency usage
async def get_db_session():
    """
    FastAPI dependency for async database session.

    Yields async SQLModel database session.
    """
    async for session in get_async_session():
        yield session


DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


# Direct dependency for async Redis - no wrapper needed
AsyncRedisDep = Annotated[redis.Redis, Depends(get_async_redis_dependency)]


# Direct dependency for sync Redis - no wrapper needed  
SyncRedisDep = Annotated[SyncRedis, Depends(get_sync_redis_dependency)]
