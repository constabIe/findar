"""
Pydantic schemas for the queue processing module.

Defines request/response models for API endpoints and data validation
for the transaction queue system.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .enums import ErrorType, TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    """Schema for creating a new queue task."""

    correlation_id: str = Field(
        ...,
        description="Unique correlation ID for idempotency",
        min_length=1,
        max_length=255,
    )

    transaction_id: Optional[UUID] = Field(
        default=None, description="Transaction ID to process"
    )

    priority: TaskPriority = Field(
        default=TaskPriority.NORMAL, description="Task priority level"
    )

    max_retries: int = Field(
        default=3, ge=0, le=10, description="Maximum retry attempts"
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional task metadata",
        alias="task_metadata",
    )


class TaskUpdate(BaseModel):
    """Schema for updating task status and metrics."""

    status: Optional[TaskStatus] = None
    celery_task_id: Optional[str] = None
    error_type: Optional[ErrorType] = None
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    processing_time_ms: Optional[int] = Field(default=None, ge=0)
    rule_engine_time_ms: Optional[int] = Field(default=None, ge=0)
    db_write_time_ms: Optional[int] = Field(default=None, ge=0)
    notification_time_ms: Optional[int] = Field(default=None, ge=0)
    worker_id: Optional[str] = None
    worker_hostname: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_retry_at: Optional[datetime] = None
    task_metadata: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")


class TaskResponse(BaseModel):
    """Schema for task response."""

    id: UUID
    correlation_id: str
    celery_task_id: Optional[str]
    transaction_id: Optional[UUID]
    status: TaskStatus
    retry_count: int
    max_retries: int
    error_type: Optional[ErrorType]
    error_message: Optional[str]
    processing_time_ms: Optional[int]
    rule_engine_time_ms: Optional[int]
    db_write_time_ms: Optional[int]
    notification_time_ms: Optional[int]
    worker_id: Optional[str]
    worker_hostname: Optional[str]
    task_metadata: Dict[str, Any] = Field(alias="metadata")
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class TaskStatusResponse(BaseModel):
    """Simplified status response."""

    correlation_id: str
    status: TaskStatus
    retry_count: int
    processing_time_ms: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]


class QueueMetrics(BaseModel):
    """Queue performance metrics."""

    total_tasks: int = Field(description="Total tasks created")
    pending_tasks: int = Field(description="Tasks waiting for processing")
    processing_tasks: int = Field(description="Tasks currently being processed")
    completed_tasks: int = Field(description="Successfully completed tasks")
    failed_tasks: int = Field(description="Failed tasks (after all retries)")
    retry_tasks: int = Field(description="Tasks scheduled for retry")

    avg_processing_time_ms: Optional[float] = Field(
        default=None, description="Average processing time"
    )

    avg_rule_engine_time_ms: Optional[float] = Field(
        default=None, description="Average rule engine time"
    )

    p95_processing_time_ms: Optional[float] = Field(
        default=None, description="95th percentile processing time"
    )

    p99_processing_time_ms: Optional[float] = Field(
        default=None, description="99th percentile processing time"
    )

    total_retries: int = Field(default=0, description="Total number of retry attempts")

    error_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Error rate (failed / total)"
    )


class TaskSubmitRequest(BaseModel):
    """Request to submit a transaction for processing."""

    transaction_id: UUID = Field(..., description="Transaction ID to process")

    correlation_id: str = Field(
        ..., description="Correlation ID for tracking", min_length=1, max_length=255
    )

    priority: TaskPriority = Field(
        default=TaskPriority.NORMAL, description="Processing priority"
    )


class TaskSubmitResponse(BaseModel):
    """Response after submitting a task."""

    task_id: UUID = Field(description="Queue task ID")
    correlation_id: str = Field(description="Correlation ID")
    celery_task_id: str = Field(description="Celery task ID")
    status: TaskStatus = Field(description="Initial task status")
    message: str = Field(description="Success message")
