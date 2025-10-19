"""
PostgreSQL database engine and session management.

This module provides async SQLModel-based database connection and session management
for the fraud detection system.
"""

from typing import Annotated, AsyncGenerator
from fastapi.params import Depends
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError, OperationalError, DatabaseError as SQLDatabaseError

from src.core.logging import get_logger
from src.core.exceptions import DatabaseError, ConfigurationError

logger = get_logger("storage.sql.engine")

# Global async engine and session maker instances
_async_engine = None
_async_session_maker = None

def get_database_url() -> str:
    """
    Construct the async database URL from configuration.
    
    Returns:
        str: Async database URL
    """
    try:
        from src.config import settings
        
        # Validate required database configuration
        try:
            host = settings.default.database.POSTGRES_HOST
            port = settings.default.database.POSTGRES_PORT
            database = settings.default.database.POSTGRES_DB
            user = settings.default.database.POSTGRES_USER
            password = settings.default.database.POSTGRES_PASSWORD
        except AttributeError as e:
            raise ConfigurationError(
                "Missing required database configuration",
                config_key=str(e),
                details={"missing_config": "database settings in .secrets.toml"}
            )
        
        # Build async database URL from settings
        database_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
        return database_url
        
    except ImportError as e:
        raise ConfigurationError(
            "Failed to import configuration",
            details={"import_error": str(e)}
        ) from e


def get_async_engine():
    """
    Get or create the async SQLModel database engine.
    
    Returns:
        AsyncEngine: Async SQLModel database engine instance
    """
    global _async_engine
    
    if _async_engine is None:
        from src.config import settings
        database_url = get_database_url()
        
        try:
            _async_engine = create_async_engine(
                database_url,
                echo=getattr(settings.default, 'database', {}).get('echo', False),
                pool_size=getattr(settings.default, 'database', {}).get('pool_size', 10),
                max_overflow=getattr(settings.default, 'database', {}).get('max_overflow', 20),
                pool_pre_ping=True,
                pool_recycle=3600  # Recycle connections every hour
            )
            
            logger.info("Database engine created successfully",
                        event="engine_created")
                        
        except SQLAlchemyError as e:
            raise DatabaseError(
                "Failed to create database engine",
                operation="create_engine",
                details={"database_url": database_url}
            ) from e
                
        
    return _async_engine


def get_async_session_maker():
    """
    Get or create the async session maker.
    
    Returns:
        async_sessionmaker: Async session factory
    """
    global _async_session_maker
    
    if _async_session_maker is None:
        try:
            engine = get_async_engine()
            _async_session_maker = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False, # WARNING: Can lead to bugs, read more about this parameter
            )
            print("Async session started")
            
            logger.info("Async session maker created successfully",
                       event="session_maker_created")
                       
        except Exception as e:
            raise DatabaseError(
                "Failed to create async session maker",
                operation="create_session_maker"
            ) from e
    
    return _async_session_maker


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async database session dependency for FastAPI.
    
    Yields:
        AsyncSession: Async SQLModel database session
    """
    try:
        session_maker = get_async_session_maker()
        print("Async session started")
    except Exception as e:
        raise DatabaseError(
            "Failed to get session maker",
            operation="get_session_maker"
        ) from e
    
    try:
        async with session_maker() as session:
            try:
                logger.debug("Async database session started",
                           event="async_session_start")
                print("Async session started")
                yield session
            except SQLAlchemyError as e:
                logger.error("Database session error",
                           event="async_session_error",
                           error_type=type(e).__name__,
                           error_message=str(e))
                await session.rollback()
                raise DatabaseError(
                    "Database session operation failed",
                    operation="session_operation"
                ) from e
            except Exception as e:
                logger.error("Unexpected session error",
                           event="async_session_unexpected_error", 
                           error_type=type(e).__name__,
                           error_message=str(e))
                await session.rollback()
                raise
            finally:
                logger.debug("Async database session closed",
                           event="async_session_end")
    except OperationalError as e:
        logger.error("Database connection error",
                   event="connection_error",
                   error_message=str(e))
        raise DatabaseError(
            "Database connection failed",
            operation="create_session"
        ) from e
    except Exception as e:
        logger.error("Failed to create database session",
                   event="session_creation_error",
                   error_type=type(e).__name__)
        raise DatabaseError(
            "Failed to create database session", 
            operation="create_session"
        ) from e


async def close_async_engine():
    """
    Close async database engine gracefully.
    
    Should be called during application shutdown.
    """
    global _async_engine
    
    if _async_engine:
        logger.info("Closing async database engine", extra={
            "component": "sql_engine",
            "event": "engine_close"
        })
        await _async_engine.dispose()
        _async_engine = None


# Type annotation for dependency injection
AsyncDbSession = Annotated[AsyncSession, "Async database session dependency"]
AsyncDbSession = Annotated[AsyncSession, Depends(get_async_session)]