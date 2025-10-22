"""
Redis client and connection management.

This module provides Redis connection management for caching and
Celery queue operations in the fraud detection system.
"""

from typing import Annotated, AsyncGenerator, Generator

from redis import Redis as SyncRedis
from redis.asyncio import ConnectionPool as AsyncConnectionPool
from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import (
    ConnectionError as RedisConnectionError,
)
from redis.exceptions import (
    ResponseError,
    TimeoutError,
)

from src.core.exceptions import ConfigurationError, DatabaseError
from src.core.logging import get_logger

logger = get_logger("storage.redis.client")

# Global Redis client instances
_async_redis_client = None
_sync_redis_client = None
_async_redis_pool = None


def get_redis_url() -> str:
    """
    Build Redis connection URL from settings.

    Returns:
        str: Redis connection URL

    Raises:
        ConfigurationError: If Redis configuration is missing or invalid
    """
    try:
        from src.config import settings

        # Validate required Redis configuration
        try:
            host = settings.redis.REDIS_HOST
            port = settings.redis.REDIS_PORT
            db = settings.redis.REDIS_DB
            password = settings.redis.REDIS_PASSWORD
        except AttributeError as e:
            raise ConfigurationError(
                "Missing required Redis configuration",
                config_key=str(e),
                details={"missing_config": "Redis settings in .env"},
            )

        # Validate configuration values
        if not host:
            raise ConfigurationError(
                "Redis host cannot be empty", config_key="REDIS_HOST"
            )

        # Validate port is numeric and in valid range
        try:
            port = int(port)
            if port <= 0 or port > 65535:
                raise ValueError("Port must be between 1 and 65535")
        except (ValueError, TypeError) as e:
            raise ConfigurationError(
                f"Invalid Redis port: {port}",
                config_key="REDIS_PORT",
                details={"provided_value": str(port), "error": str(e)},
            )

        # Validate database number
        try:
            db = int(db)
            if db < 0 or db > 15:  # Redis typically supports 0-15 databases
                raise ValueError("Database must be between 0 and 15")
        except (ValueError, TypeError) as e:
            raise ConfigurationError(
                f"Invalid Redis database number: {db}",
                config_key="REDIS_DB",
                details={"provided_value": str(db), "error": str(e)},
            )

        if password:
            return f"redis://:{password}@{host}:{port}/{db}"
        else:
            return f"redis://{host}:{port}/{db}"

    except ImportError as e:
        raise ConfigurationError(
            "Failed to import configuration", details={"import_error": str(e)}
        ) from e


async def get_async_redis() -> AsyncConnectionPool:
    """
    Get or create async Redis connection pool.

    Returns:
        AsyncConnectionPool: Redis connection pool for async operations

    Raises:
        DatabaseError: If connection to Redis fails
        ConfigurationError: If Redis configuration is invalid
    """
    from src.core.logging import get_logger

    logger = get_logger("storage.redis")

    global _async_redis_pool

    if _async_redis_pool is None:
        try:
            redis_url = get_redis_url()
            logger.info(
                "Creating async Redis connection pool",
                url=redis_url.split("@")[-1] if "@" in redis_url else redis_url,
            )

            _async_redis_pool = AsyncConnectionPool.from_url(
                url=redis_url,
                max_connections=20,
                retry_on_timeout=True,
                retry_on_error=[ConnectionError, TimeoutError],
                decode_responses=True,
            )

            # Test the connection
            try:
                redis_client = AsyncRedis(connection_pool=_async_redis_pool)
                await redis_client.ping()
                logger.info("Async Redis connection established successfully")
            except (ConnectionError, TimeoutError, ResponseError) as e:
                raise DatabaseError(
                    "Failed to connect to Redis",
                    operation="ping",
                    details={"error": str(e), "connection_type": "async"},
                ) from e
            except Exception as e:
                raise DatabaseError(
                    "Unexpected error during Redis connection test",
                    operation="ping",
                    details={"error": str(e), "connection_type": "async"},
                ) from e

        except ConfigurationError:
            # Re-raise configuration errors as-is
            raise
        except Exception as e:
            logger.error("Failed to create async Redis connection pool", error=str(e))
            raise DatabaseError(
                "Failed to create Redis connection pool",
                operation="create_pool",
                details={"error": str(e), "connection_type": "async"},
            ) from e

    return _async_redis_pool


def get_sync_redis() -> SyncRedis:
    """
    Get or create sync Redis client for Celery workers.

    Returns:
        SyncRedis: Synchronous Redis client

    Raises:
        DatabaseError: If connection to Redis fails
        ConfigurationError: If Redis configuration is invalid
    """
    from src.core.logging import get_logger

    logger = get_logger("storage.redis")

    global _sync_redis_client

    if _sync_redis_client is None:
        try:
            redis_url = get_redis_url()
            logger.info(
                "Creating sync Redis client",
                url=redis_url.split("@")[-1] if "@" in redis_url else redis_url,
            )

            _sync_redis_client = SyncRedis.from_url(
                url=redis_url,
                decode_responses=True,
                retry_on_timeout=True,
                retry_on_error=[RedisConnectionError, TimeoutError],
            )

            # Test the connection
            try:
                _sync_redis_client.ping()
                logger.info("Sync Redis connection established successfully")
            except (RedisConnectionError, TimeoutError, ResponseError) as e:
                raise DatabaseError(
                    "Failed to connect to Redis",
                    operation="ping",
                    details={"error": str(e), "connection_type": "sync"},
                ) from e
            except Exception as e:
                raise DatabaseError(
                    "Unexpected error during Redis connection test",
                    operation="ping",
                    details={"error": str(e), "connection_type": "sync"},
                ) from e

        except ConfigurationError:
            # Re-raise configuration errors as-is
            raise
        except Exception as e:
            logger.error("Failed to create sync Redis client", error=str(e))
            raise DatabaseError(
                "Failed to create Redis client",
                operation="create_client",
                details={"error": str(e), "connection_type": "sync"},
            ) from e

    return _sync_redis_client


async def get_async_redis_dependency() -> AsyncGenerator[AsyncRedis, None]:
    """
    FastAPI dependency for async Redis client.

    Yields:
        AsyncRedis: Async Redis client

    Raises:
        DatabaseError: If Redis connection fails
    """
    from src.core.logging import get_logger

    logger = get_logger("storage.redis")

    try:
        pool = await get_async_redis()
        client = AsyncRedis(connection_pool=pool)

        logger.debug(
            "Redis session started",
            extra={"component": "redis_client", "event": "session_start"},
        )
        yield client
    except Exception as e:
        logger.error(
            "Redis session error",
            extra={
                "component": "redis_client",
                "event": "session_error",
                "error": str(e),
            },
        )
        raise DatabaseError(
            "Failed to create Redis session",
            operation="get_dependency",
            details={"error": str(e)},
        ) from e
    finally:
        # Connection pool cleanup is handled automatically
        logger.debug(
            "Redis session ended",
            extra={"component": "redis_client", "event": "session_end"},
        )


def get_sync_redis_dependency() -> Generator[SyncRedis, None, None]:
    """
    Dependency for sync Redis client (for Celery workers).

    Yields:
        SyncRedis: Synchronous Redis client
    """
    client = get_sync_redis()

    try:
        logger.debug(
            "Sync Redis session started",
            extra={"component": "redis_client", "event": "sync_session_start"},
        )
        yield client
    except Exception as e:
        logger.error(
            "Sync Redis session error",
            extra={
                "component": "redis_client",
                "event": "sync_session_error",
                "error": str(e),
            },
        )
        raise
    finally:
        logger.debug(
            "Sync Redis session ended",
            extra={"component": "redis_client", "event": "sync_session_end"},
        )


async def close_redis_connections():
    """
    Close Redis connections gracefully.

    Should be called during application shutdown.
    """
    from src.core.logging import get_logger

    logger = get_logger("storage.redis")
    global _async_redis_client, _sync_redis_client, _async_redis_pool

    # Close async connection pool
    if _async_redis_pool:
        logger.info(
            "Closing async Redis connection pool",
            extra={"component": "redis_client", "event": "async_pool_close"},
        )
        try:
            await _async_redis_pool.disconnect()
        except Exception as e:
            logger.error("Error closing async Redis pool", error=str(e))
        finally:
            _async_redis_pool = None

    # Reset async client reference
    if _async_redis_client:
        _async_redis_client = None

    # Close sync client
    if _sync_redis_client:
        logger.info(
            "Closing sync Redis connection",
            extra={"component": "redis_client", "event": "sync_close"},
        )
        try:
            _sync_redis_client.close()
        except Exception as e:
            logger.error("Error closing sync Redis client", error=str(e))
        finally:
            _sync_redis_client = None


# Type annotations for dependency injection
AsyncRedisClient = Annotated[AsyncRedis, "Async Redis client dependency"]
SyncRedisClient = Annotated[SyncRedis, "Sync Redis client dependency"]
