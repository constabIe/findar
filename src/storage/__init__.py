"""
Storage layer module.

Contains async SQL and Redis storage implementations and dependency injection.
"""

from .sql import (
    get_async_engine, 
    get_async_session_maker,
    get_async_session,
    close_async_engine,
    AsyncDbSession
)
from .redis import get_async_redis, get_sync_redis, close_redis_connections
from .dependencies import AsyncDbSessionDep, AsyncRedisDep, SyncRedisDep

__all__ = [
    # SQL
    "get_async_engine",
    "get_async_session_maker",
    "get_async_session", 
    "close_async_engine",
    "AsyncDbSession",
    # Redis
    "get_async_redis",
    "get_sync_redis",
    "close_redis_connections", 
    # Dependencies
    "AsyncDbSessionDep",
    "AsyncRedisDep",
    "SyncRedisDep"
]
