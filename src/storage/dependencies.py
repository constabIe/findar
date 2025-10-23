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
# AsyncRedisDep = Annotated[redis.Redis, Depends(get_async_redis_dependency)]
SyncRedisDep = Annotated[SyncRedis, Depends(get_sync_redis_dependency)]


# Convenience functions for explicit dependency usage
def get_db_session():
    """
    FastAPI dependency for async database session.

    Returns dependency that provides async SQLModel database session.
    """
    return Depends(get_async_session)


DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]

def get_async_redis_client():
    """
    FastAPI dependency for async Redis client.

    Returns dependency that provides async Redis client.
    """
    return Depends(get_async_redis_dependency)


AsyncRedisDep = Annotated[redis.Redis, get_async_redis_client()]


def get_sync_redis_client():
    """
    FastAPI dependency for sync Redis client (used by Celery workers).

    Returns dependency that provides sync Redis client.
    """
    return Depends(get_sync_redis_dependency)
