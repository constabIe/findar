"""
SQLModel database models for the rule engine module.

Contains the main database models for rules, transactions, and related entities
used in the fraud detection system.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlmodel import JSON, Field, SQLModel, String

from src.modules.rule_engine.enums import RuleType, TransactionStatus, TransactionType


class Transaction(SQLModel, table=True):
    """
    Basic transaction model for rule engine evaluation.

    This model represents financial transactions that will be evaluated
    against fraud detection rules. It will be enhanced later with additional
    fields and relationships.
    """

    __tablename__ = "transactions"  # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    amount: float = Field(description="Transaction amount")
    from_account: str = Field(description="Source account identifier")
    to_account: str = Field(description="Destination account identifier")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Transaction timestamp"
    )
    type: TransactionType = Field(description="Type of transaction")
    correlation_id: str = Field(description="Request correlation ID for tracking")
    status: TransactionStatus = Field(
        default=TransactionStatus.PENDING, description="Transaction processing status"
    )

    # Additional fields for rule evaluation
    currency: str = Field(default="USD", description="Transaction currency")
    description: Optional[str] = Field(
        default=None, description="Transaction description"
    )
    merchant_id: Optional[str] = Field(
        default=None, description="Merchant identifier for payments"
    )
    # merchant_type: Optional[str] = Field(default=None, description="Type/category of merchant")
    location: Optional[str] = Field(default=None, description="Transaction location")
    device_id: Optional[str] = Field(
        default=None, description="Device used for transaction"
    )
    ip_address: Optional[str] = Field(
        default=None, description="IP address of transaction origin"
    )

    # Metadata for rule engine
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Record creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Record update timestamp"
    )


class Rule(SQLModel, table=True):
    """
    Fraud detection rule model.

    Represents configurable rules for detecting suspicious transactions.
    Supports multiple rule types with flexible parameter configuration.
    """

    __tablename__ = "rules"  # type: ignore

    id: UUID = Field(
        primary_key=True, description="Rule unique identifier", default_factory=uuid4
    )
    name: str = Field(sa_column=Column(String, unique=True), description="Rule name")
    type: RuleType = Field(description="Rule type (threshold/pattern/composite/ml)")
    params: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Rule-specific parameters",
    )
    enabled: bool = Field(default=True, description="Whether rule is active")
    priority: int = Field(
        default=0, description="Rule execution priority (higher = first)"
    )
    critical: bool = Field(
        default=False, description="Critical rule for short-circuiting"
    )
    description: Optional[str] = Field(default=None, description="Rule description")

    # Metadata and tracking
    created_by: Optional[str] = Field(default=None, description="Rule creator")

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Rule creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Rule update timestamp"
    )

    # Performance tracking
    execution_count: int = Field(
        default=0, description="Number of times rule was executed"
    )
    match_count: int = Field(default=0, description="Number of times rule matched")
    last_executed_at: Optional[datetime] = Field(
        default=None, description="Last execution timestamp"
    )
    average_execution_time_ms: Optional[float] = Field(
        default=None, description="Average execution time in milliseconds"
    )


class RuleExecution(SQLModel, table=True):
    """
    Rule execution audit log.

    Tracks individual rule executions for monitoring, debugging, and compliance.
    """

    __tablename__ = "rule_executions"  # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    rule_id: UUID = Field(foreign_key="rules.id", description="Executed rule ID")
    transaction_id: UUID = Field(
        foreign_key="transactions.id", description="Evaluated transaction ID"
    )
    correlation_id: str = Field(description="Request correlation ID")

    # Execution results
    matched: bool = Field(description="Whether rule matched")
    confidence_score: Optional[float] = Field(
        default=None, description="Confidence score (0.0-1.0)"
    )
    execution_time_ms: float = Field(description="Execution time in milliseconds")

    # Context and debugging
    context: Dict[str, Any] = Field(
        default_factory=dict, sa_type=JSON, description="Rule execution context"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if execution failed"
    )

    # Timestamps
    executed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Execution timestamp"
    )


class RuleCache(SQLModel, table=True):
    """
    Cache metadata for rules stored in Redis.

    Tracks which rules are cached in Redis for hot reload functionality.
    """

    __tablename__ = "rule_cache"  # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    rule_id: UUID = Field(
        foreign_key="rules.id", unique=True, description="Cached rule ID"
    )
    cache_key: str = Field(description="Redis cache key")
    cached_at: datetime = Field(
        default_factory=datetime.utcnow, description="Cache timestamp"
    )
    expires_at: Optional[datetime] = Field(
        default=None, description="Cache expiration timestamp"
    )
    cache_version: str = Field(description="Version of cached rule")

    # Cache statistics
    hit_count: int = Field(default=0, description="Number of cache hits")
    last_accessed_at: Optional[datetime] = Field(
        default=None, description="Last cache access timestamp"
    )


# class QueueTask(SQLModel, table=True):
#     """
#     Track processing status and metrics for transaction queue tasks.

#     This model stores metadata about each transaction processing task,
#     including Celery task information, retry history, timing metrics,
#     and error details for monitoring and debugging.
#     """

#     __tablename__ = "queue_tasks"  # type: ignore

#     # Primary identification
#     id: UUID = Field(
#         default_factory=uuid4,
#         primary_key=True,
#         description="Unique task identifier"
#     )

#     # Task correlation and tracking
#     correlation_id: str = Field(
#         index=True,
#         unique=True,
#         description="Transaction correlation ID for idempotency"
#     )

#     celery_task_id: Optional[str] = Field(
#         default=None,
#         index=True,
#         description="Celery task ID for tracking in Celery"
#     )

#     transaction_id: Optional[UUID] = Field(
#         default=None,
#         index=True,
#         description="Reference to the transaction being processed"
#     )

#     # Status tracking
#     status: TaskStatus = Field(
#         default=TaskStatus.PENDING,
#         index=True,
#         description="Current processing status"
#     )

#     # Retry management
#     retry_count: int = Field(
#         default=0,
#         description="Number of retry attempts"
#     )

#     max_retries: int = Field(
#         default=3,
#         description="Maximum allowed retry attempts"
#     )

#     # Error tracking
#     error_type: Optional[ErrorType] = Field(
#         default=None,
#         description="Type of error if failed"
#     )

#     error_message: Optional[str] = Field(
#         default=None,
#         description="Detailed error message"
#     )

#     error_traceback: Optional[str] = Field(
#         default=None,
#         description="Full error traceback for debugging"
#     )

#     # Performance metrics
#     processing_time_ms: Optional[int] = Field(
#         default=None,
#         description="Total processing time in milliseconds"
#     )

#     rule_engine_time_ms: Optional[int] = Field(
#         default=None,
#         description="Time spent in rule engine evaluation (ms)"
#     )

#     db_write_time_ms: Optional[int] = Field(
#         default=None,
#         description="Time spent writing to database (ms)"
#     )

#     notification_time_ms: Optional[int] = Field(
#         default=None,
#         description="Time spent sending notifications (ms)"
#     )

#     # Worker information
#     worker_id: Optional[str] = Field(
#         default=None,
#         description="ID of the worker that processed the task"
#     )

#     worker_hostname: Optional[str] = Field(
#         default=None,
#         description="Hostname of the worker machine"
#     )

#     # Additional metadata
#     task_metadata: Dict[str, Any] = Field(
#         default_factory=dict,
#         sa_column=Column(PGJSON),
#         description="Additional flexible metadata"
#     )

#     # Timestamps
#     created_at: datetime = Field(
#         default_factory=datetime.utcnow,
#         description="Task creation timestamp",
#         sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
#     )

#     started_at: Optional[datetime] = Field(
#         default=None,
#         description="When processing started"
#     )

#     completed_at: Optional[datetime] = Field(
#         default=None,
#         description="When processing completed (success or failure)"
#     )

#     last_retry_at: Optional[datetime] = Field(
#         default=None,
#         description="Timestamp of last retry attempt"
#     )

#     updated_at: datetime = Field(
#         default_factory=datetime.utcnow,
#         description="Last update timestamp",
#         sa_column_kwargs={
#             "server_default": text("CURRENT_TIMESTAMP"),
#             "onupdate": text("CURRENT_TIMESTAMP")
#         }
#     )

#     # Define composite indexes for common queries
#     __table_args__ = (
#         Index("idx_queue_status_created", "status", "created_at"),
#         Index("idx_queue_correlation", "correlation_id"),
#         Index("idx_queue_celery_task", "celery_task_id"),
#         Index("idx_queue_transaction", "transaction_id"),
#     )
