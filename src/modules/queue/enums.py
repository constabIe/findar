"""
Enumerations for the queue processing module.

Defines status types and other constants used for transaction processing
and task management in the Celery-based queue system.

Note: These enums are now centralized in src.storage.enums to prevent circular imports.
This file re-exports them for backward compatibility.
"""

from src.storage.enums import ErrorType, TaskPriority, TaskStatus

__all__ = [
    "TaskStatus",
    "TaskPriority",
    "ErrorType",
]
