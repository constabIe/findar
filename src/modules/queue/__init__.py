"""
Queue processing module for asynchronous transaction handling.

This module provides the infrastructure for processing transactions through
a Celery-based queue system with Redis as the message broker and PostgreSQL
for result storage.

Key Components:
- Models: QueueTask for tracking processing status
- Enums: TaskStatus, ErrorType for standardized states
- Repository: QueueRepository for database operations
- Tasks: Celery tasks for async processing
- Routes: FastAPI endpoints for queue management
- Metrics: Prometheus integration for monitoring

Flow:
1. Transaction received via API
2. Task created in database and submitted to queue
3. Celery worker picks up task
4. Transaction evaluated by rule engine
5. Status updated, notifications sent
6. Metrics recorded
"""

from .celery_config import celery_app
from .enums import ErrorType, TaskPriority, TaskStatus
from .models import QueueTask
from .repository import QueueRepository
from .schemas import (
    QueueMetrics,
    TaskCreate,
    TaskResponse,
    TaskStatusResponse,
    TaskSubmitRequest,
    TaskSubmitResponse,
    TaskUpdate,
)
from .tasks import process_transaction

__all__ = [
    # Celery app
    "celery_app",
    # Models
    "QueueTask",
    # Enums
    "TaskStatus",
    "TaskPriority",
    "ErrorType",
    # Repository
    "QueueRepository",
    # Schemas
    "TaskCreate",
    "TaskUpdate",
    "TaskResponse",
    "TaskStatusResponse",
    "TaskSubmitRequest",
    "TaskSubmitResponse",
    "QueueMetrics",
    # Tasks
    "process_transaction",
]
