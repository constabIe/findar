"""
SQLModel database models for the queue processing module.

Contains models for tracking transaction processing tasks through
the Celery-based queue system.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, Index, text
from sqlalchemy.dialects.postgresql import JSON as PGJSON
from sqlmodel import Field, SQLModel

from .enums import ErrorType, TaskStatus


class QueueTask(SQLModel, table=True):
    """
    Track processing status and metrics for transaction queue tasks.
    
    This model stores metadata about each transaction processing task,
    including Celery task information, retry history, timing metrics,
    and error details for monitoring and debugging.
    """

    __tablename__ = "queue_tasks"  # type: ignore

    # Primary identification
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        description="Unique task identifier"
    )

    # Task correlation and tracking
    correlation_id: str = Field(
        index=True,
        unique=True,
        description="Transaction correlation ID for idempotency"
    )

    celery_task_id: Optional[str] = Field(
        default=None,
        index=True,
        description="Celery task ID for tracking in Celery"
    )

    transaction_id: Optional[UUID] = Field(
        default=None,
        index=True,
        description="Reference to the transaction being processed"
    )

    # Status tracking
    status: TaskStatus = Field(
        default=TaskStatus.PENDING,
        index=True,
        description="Current processing status"
    )

    # Retry management
    retry_count: int = Field(
        default=0,
        description="Number of retry attempts"
    )

    max_retries: int = Field(
        default=3,
        description="Maximum allowed retry attempts"
    )

    # Error tracking
    error_type: Optional[ErrorType] = Field(
        default=None,
        description="Type of error if failed"
    )

    error_message: Optional[str] = Field(
        default=None,
        description="Detailed error message"
    )

    error_traceback: Optional[str] = Field(
        default=None,
        description="Full error traceback for debugging"
    )

    # Performance metrics
    processing_time_ms: Optional[int] = Field(
        default=None,
        description="Total processing time in milliseconds"
    )

    rule_engine_time_ms: Optional[int] = Field(
        default=None,
        description="Time spent in rule engine evaluation (ms)"
    )

    db_write_time_ms: Optional[int] = Field(
        default=None,
        description="Time spent writing to database (ms)"
    )

    notification_time_ms: Optional[int] = Field(
        default=None,
        description="Time spent sending notifications (ms)"
    )

    # Worker information
    worker_id: Optional[str] = Field(
        default=None,
        description="ID of the worker that processed the task"
    )

    worker_hostname: Optional[str] = Field(
        default=None,
        description="Hostname of the worker machine"
    )

    # Additional metadata
    task_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(PGJSON),
        description="Additional flexible metadata"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Task creation timestamp",
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )

    started_at: Optional[datetime] = Field(
        default=None,
        description="When processing started"
    )

    completed_at: Optional[datetime] = Field(
        default=None,
        description="When processing completed (success or failure)"
    )

    last_retry_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp of last retry attempt"
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp",
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "onupdate": text("CURRENT_TIMESTAMP")
        }
    )

    # Define composite indexes for common queries
    __table_args__ = (
        Index("idx_queue_status_created", "status", "created_at"),
        Index("idx_queue_correlation", "correlation_id"),
        Index("idx_queue_celery_task", "celery_task_id"),
        Index("idx_queue_transaction", "transaction_id"),
    )
