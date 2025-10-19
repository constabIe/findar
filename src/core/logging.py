"""
Centralized logging system using Loguru with Loki compatibility.

This module provides structured JSON logging with flexible parameter injection,
correlation tracking, and performance monitoring for the fraud detection system.
"""

import json
import sys
import time
from contextvars import ContextVar
from functools import wraps
from typing import Optional

from loguru import logger as loguru_logger

# Context variables for correlation tracking
correlation_id_var: ContextVar[Optional[str]] = ContextVar(
    "correlation_id", default=None
)
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)

# Global configuration flag
_logging_configured = False


def configure_logging(
    log_level: str = "INFO",
    json_format: bool = True,
    enable_console: bool = True,
    enable_file: bool = True,
    file_path: str = "logs/findar.log",
    file_rotation: str = "100 MB",
    file_retention: str = "30 days",
) -> None:
    """
    Configure Loguru logging with structured JSON output for Loki.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to use JSON formatting (required for Loki)
        enable_console: Enable console output (stdout)
        enable_file: Enable file output
        file_path: Path to log file
        file_rotation: File rotation policy
        file_retention: File retention policy
    """
    global _logging_configured

    if _logging_configured:
        return

    # Remove default handler
    loguru_logger.remove()

    # JSON formatter for structured logging
    def json_formatter(record) -> str:
        """Custom JSON formatter for Loki compatibility."""
        # Base log entry
        log_entry = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "message": record["message"],
            "module": record["name"],
            "function": record["function"],
            "line": record["line"],
            "process_id": record["process"].id,
            "thread_id": record["thread"].id,
        }
        
        # Add context variables if available
        if correlation_id_var.get():
            log_entry["correlation_id"] = correlation_id_var.get()
        if request_id_var.get():
            log_entry["request_id"] = request_id_var.get()
        if user_id_var.get():
            log_entry["user_id"] = user_id_var.get()
        
        # Add extra fields from record
        if record.get("extra"):
            log_entry.update(record["extra"])
        
        # Add exception info if present
        if record.get("exception"):
            log_entry["exception"] = {
                "type": record["exception"].type.__name__ if record["exception"].type else None,
                "value": str(record["exception"].value) if record["exception"].value else None,
                "traceback": record["exception"].traceback if record["exception"].traceback else None
            }
        
        return json.dumps(log_entry, ensure_ascii=False)
    
    # Simple text formatter for development
    def text_formatter(record) -> str:
        """Simple text formatter for console output."""
        timestamp = record["time"].strftime("%Y-%m-%d %H:%M:%S")
        level = record["level"].name
        module = record["name"]
        message = record["message"]
        
        # Add correlation ID if available
        correlation = f" [{correlation_id_var.get()}]" if correlation_id_var.get() else ""
        
        # Add extra fields
        extra_str = ""
        if record.get("extra"):
            extra_items = []
            for key, value in record["extra"].items():
                if key not in ["correlation_id", "request_id", "user_id"]:  # Skip context vars
                    extra_items.append(f"{key}={value}")
            if extra_items:
                extra_str = f" | {', '.join(extra_items)}"
        
        return f"{timestamp} | {level:8} | {module:20} | {message}{correlation}{extra_str}\n"
    
    # Configure console handler
    if enable_console:
        formatter = json_formatter if json_format else text_formatter
        loguru_logger.add(
            sys.stdout,
            level=log_level,
            format=formatter,
            colorize=not json_format,
            backtrace=True,
            diagnose=True,
        )

    # Configure file handler
    if enable_file:
        loguru_logger.add(
            file_path,
            level=log_level,
            format=json_formatter,
            rotation=file_rotation,
            retention=file_retention,
            compression="gz",
            backtrace=True,
            diagnose=True,
        )

    _logging_configured = True


class LoggerAdapter:
    """
    Custom logger adapter that provides structured logging with flexible parameters.

    This adapter allows for easy injection of contextual information and maintains
    compatibility with Loki's structured logging requirements.
    """

    def __init__(self, name: str):
        """
        Initialize logger adapter with component name.

        Args:
            name: Component name (e.g., "storage.sql", "transaction.service")
        """
        self.name = name
        self.logger = loguru_logger.bind(component=name)

    def _log(self, level: str, message: str, **kwargs) -> None:
        """
        Internal logging method with flexible parameter injection.

        Args:
            level: Log level (debug, info, warning, error, critical)
            message: Log message
            **kwargs: Additional parameters to include in structured log
        """
        # Extract standard parameters
        extra = kwargs.pop("extra", {})
        exc_info = kwargs.pop("exc_info", None)

        # Merge additional kwargs into extra
        extra.update(kwargs)

        # Add component name
        extra["component"] = self.name

        # Bind extra parameters to logger
        bound_logger = self.logger.bind(**extra)

        # Log with appropriate level
        if level == "debug":
            bound_logger.debug(message, exc_info=exc_info)
        elif level == "info":
            bound_logger.info(message, exc_info=exc_info)
        elif level == "warning":
            bound_logger.warning(message, exc_info=exc_info)
        elif level == "error":
            bound_logger.error(message, exc_info=exc_info)
        elif level == "critical":
            bound_logger.critical(message, exc_info=exc_info)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with optional parameters."""
        self._log("debug", message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message with optional parameters."""
        self._log("info", message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with optional parameters."""
        self._log("warning", message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message with optional parameters."""
        self._log("error", message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with optional parameters."""
        self._log("critical", message, **kwargs)

    def exception(self, message: str, **kwargs) -> None:
        """Log exception with traceback."""
        kwargs["exc_info"] = True
        self._log("error", message, **kwargs)


def get_logger(name: str) -> LoggerAdapter:
    """
    Get a component-specific logger with structured logging capabilities.

    This function provides the main interface for getting loggers throughout
    the application. Each logger is bound to a component name and provides
    flexible parameter injection for structured logging.

    Args:
        name: Component name (e.g., "storage.sql", "transaction.service", "queue.worker")

    Returns:
        LoggerAdapter: Configured logger adapter with structured logging

    Example:
        >>> logger = get_logger("transaction.service")
        >>> logger.info("Processing transaction",
        ...              transaction_id="tx_123",
        ...              amount=1000.0,
        ...              event="transaction_start")
    """
    # Ensure logging is configured
    if not _logging_configured:
        try:
            # Lazy import to avoid circular dependencies
            from src.config import settings

            configure_logging(
                log_level=settings.get("default.logging.level", "INFO"),
                json_format=settings.get("default.logging.json_format", True),
            )
        except (ImportError, AttributeError):
            # Fallback to default configuration if settings unavailable
            configure_logging()

    return LoggerAdapter(name)


# Context management utilities
def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for request tracking."""
    correlation_id_var.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID."""
    return correlation_id_var.get()


def set_request_id(request_id: str) -> None:
    """Set request ID for HTTP request tracking."""
    request_id_var.set(request_id)


def get_request_id() -> Optional[str]:
    """Get current request ID."""
    return request_id_var.get()


def set_user_id(user_id: str) -> None:
    """Set user ID for user action tracking."""
    user_id_var.set(user_id)


def get_user_id() -> Optional[str]:
    """Get current user ID."""
    return user_id_var.get()


def clear_context() -> None:
    """Clear all context variables."""
    correlation_id_var.set(None)
    request_id_var.set(None)
    user_id_var.set(None)


# Performance monitoring decorators
def log_performance(
    logger_name: Optional[str] = None, log_args: bool = False, log_result: bool = False
):
    """
    Decorator for logging function performance metrics.

    Args:
        logger_name: Custom logger name, defaults to module name
        log_args: Whether to log function arguments
        log_result: Whether to log function result

    Example:
        >>> @log_performance("transaction.service", log_args=True)
        ... async def process_transaction(transaction_id: str, amount: float):
        ...     # Function implementation
        ...     return result
    """

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(logger_name or f"{func.__module__}.{func.__name__}")
            start_time = time.time()

            # Log function start
            log_data = {
                "event": "function_start",
                "function": func.__name__,
                "module": func.__module__,
            }

            if log_args:
                log_data["args"] = str(args)
                log_data["kwargs"] = str(kwargs)

            logger.debug("Function execution started", **log_data)

            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time

                # Log successful completion
                success_data = {
                    "event": "function_success",
                    "function": func.__name__,
                    "execution_time_ms": round(execution_time * 1000, 2),
                }

                if log_result:
                    success_data["result"] = str(result)

                logger.info("Function executed successfully", **success_data)
                return result

            except Exception as e:
                execution_time = time.time() - start_time

                # Log error
                error_data = {
                    "event": "function_error",
                    "function": func.__name__,
                    "execution_time_ms": round(execution_time * 1000, 2),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }

                logger.error("Function execution failed", **error_data)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(logger_name or f"{func.__module__}.{func.__name__}")
            start_time = time.time()

            # Log function start
            log_data = {
                "event": "function_start",
                "function": func.__name__,
                "module": func.__module__,
            }

            if log_args:
                log_data["args"] = str(args)
                log_data["kwargs"] = str(kwargs)

            logger.debug("Function execution started", **log_data)

            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                # Log successful completion
                success_data = {
                    "event": "function_success",
                    "function": func.__name__,
                    "execution_time_ms": round(execution_time * 1000, 2),
                }

                if log_result:
                    success_data["result"] = str(result)

                logger.info("Function executed successfully", **success_data)
                return result

            except Exception as e:
                execution_time = time.time() - start_time

                # Log error
                error_data = {
                    "event": "function_error",
                    "function": func.__name__,
                    "execution_time_ms": round(execution_time * 1000, 2),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }

                logger.error("Function execution failed", **error_data)
                raise

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def log_database_operation(operation_type: str):
    """
    Decorator specifically for logging database operations.

    Args:
        operation_type: Type of operation (SELECT, INSERT, UPDATE, DELETE)

    Example:
        >>> @log_database_operation("SELECT")
        ... async def get_transactions(db: AsyncSession, user_id: str):
        ...     return await db.execute(select(Transaction))
    """

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger("database.operation")
            start_time = time.time()

            logger.debug(
                "Database operation started",
                event="db_operation_start",
                operation_type=operation_type,
                function=func.__name__,
            )

            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time

                logger.info(
                    "Database operation completed",
                    event="db_operation_success",
                    operation_type=operation_type,
                    function=func.__name__,
                    execution_time_ms=round(execution_time * 1000, 2),
                )
                return result

            except Exception as e:
                execution_time = time.time() - start_time

                logger.error(
                    "Database operation failed",
                    event="db_operation_error",
                    operation_type=operation_type,
                    function=func.__name__,
                    execution_time_ms=round(execution_time * 1000, 2),
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger("database.operation")
            start_time = time.time()

            logger.debug(
                "Database operation started",
                event="db_operation_start",
                operation_type=operation_type,
                function=func.__name__,
            )

            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                logger.info(
                    "Database operation completed",
                    event="db_operation_success",
                    operation_type=operation_type,
                    function=func.__name__,
                    execution_time_ms=round(execution_time * 1000, 2),
                )
                return result

            except Exception as e:
                execution_time = time.time() - start_time

                logger.error(
                    "Database operation failed",
                    event="db_operation_error",
                    operation_type=operation_type,
                    function=func.__name__,
                    execution_time_ms=round(execution_time * 1000, 2),
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                raise

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Initialize logging on module import
def init_logging() -> None:
    """Initialize logging configuration from settings."""
    try:
        from src.config import settings

        configure_logging(
            log_level=settings.get("logging.level", "INFO"),
            json_format=settings.get("logging.json_format", True),
            enable_console=settings.get("logging.enable_console", True),
            enable_file=settings.get("logging.enable_file", False),
            file_path=settings.get("logging.file_path", "logs/findar.log"),
        )
    except ImportError:
        # Fallback configuration if settings not available
        configure_logging()
