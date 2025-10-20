"""
Enumerations for the queue processing module.

Defines status types and other constants used for transaction processing
and task management in the Celery-based queue system.
"""

from enum import Enum


class TaskStatus(str, Enum):
    """
    Status of a queue task processing.
    
    Lifecycle:
    PENDING -> PROCESSING -> COMPLETED
                         -> FAILED -> RETRY -> PROCESSING
                                  -> FAILED (after max retries)
    """

    PENDING = "pending"  # Task created, waiting for worker
    PROCESSING = "processing"  # Task being processed by worker
    COMPLETED = "completed"  # Successfully completed
    FAILED = "failed"  # Failed after all retries
    RETRY = "retry"  # Scheduled for retry


class TaskPriority(int, Enum):
    """
    Priority levels for task processing.
    Higher number = higher priority.
    """

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class ErrorType(str, Enum):
    """
    Types of errors that can occur during task processing.
    """

    VALIDATION_ERROR = "validation_error"  # Invalid transaction data
    DATABASE_ERROR = "database_error"  # DB connection/query issues
    RULE_ENGINE_ERROR = "rule_engine_error"  # Rule evaluation failure
    NOTIFICATION_ERROR = "notification_error"  # Failed to send notification
    TIMEOUT_ERROR = "timeout_error"  # Task execution timeout
    UNKNOWN_ERROR = "unknown_error"  # Unexpected errors
