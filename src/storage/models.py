"""
SQLModel database models for the entire application.

Contains all database models including users, transactions, rules,
notifications, queue tasks, and related entities used across the system.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Column, Index, text
from sqlalchemy.dialects.postgresql import JSON as PGJSON
from sqlmodel import Field, SQLModel, String

from src.storage.enums import (
    ErrorType,
    NotificationChannel,
    NotificationStatus,
    RuleType,
    TaskStatus,
    TemplateType,
    TransactionStatus,
    TransactionType,
)


class User(SQLModel, table=True):
    """
    User model for admin panel authentication.

    Represents users who can access the admin panel, create rules,
    and manage the fraud detection system.
    """

    __tablename__ = "users"  # type: ignore

    id: UUID = Field(
        default_factory=uuid4, primary_key=True, description="User unique identifier"
    )
    email: str = Field(
        sa_column=Column(String, unique=True, index=True),
        description="User email (used for login)",
    )
    hashed_password: str = Field(description="Bcrypt hashed password")
    telegram_alias: str = Field(
        sa_column=Column(String, unique=True, index=True),
        description="Telegram username/alias (without @)",
    )
    telegram_id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger, index=True),
        description="Telegram user ID (filled when user starts bot)",
    )

    # Notification settings and template associations
    email_template_id: Optional[UUID] = Field(
        default=None,
        foreign_key="notification_templates.id",
        description="Email notification template ID",
    )
    telegram_template_id: Optional[UUID] = Field(
        default=None,
        foreign_key="notification_templates.id",
        description="Telegram notification template ID",
    )

    email_notifications_enabled: bool = Field(
        default=True, description="Whether email notifications are enabled"
    )
    telegram_notifications_enabled: bool = Field(
        default=True, description="Whether Telegram notifications are enabled"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="User registration timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="User data update timestamp"
    )


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

    # Review fields for manual analyst decisions
    reviewed_at: Optional[datetime] = Field(
        default=None, description="Timestamp when transaction was reviewed by analyst"
    )
    review_comment: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Analyst comment explaining the review decision",
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
        sa_column=Column(PGJSON),
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
    created_by_user_id: Optional[UUID] = Field(
        default=None,
        foreign_key="users.id",
        description="ID of user who created this rule",
    )

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
        default_factory=dict,
        sa_column=Column(PGJSON),
        description="Rule execution context",
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
        default_factory=uuid4, primary_key=True, description="Unique task identifier"
    )

    # Task correlation and tracking
    correlation_id: str = Field(
        index=True,
        unique=True,
        description="Transaction correlation ID for idempotency",
    )

    celery_task_id: Optional[str] = Field(
        default=None, index=True, description="Celery task ID for tracking in Celery"
    )

    transaction_id: Optional[UUID] = Field(
        default=None,
        index=True,
        description="Reference to the transaction being processed",
    )

    # Status tracking
    status: TaskStatus = Field(
        default=TaskStatus.PENDING, index=True, description="Current processing status"
    )

    # Retry management
    retry_count: int = Field(default=0, description="Number of retry attempts")

    max_retries: int = Field(default=3, description="Maximum allowed retry attempts")

    # Error tracking
    error_type: Optional[ErrorType] = Field(
        default=None, description="Type of error if failed"
    )

    error_message: Optional[str] = Field(
        default=None, description="Detailed error message"
    )

    error_traceback: Optional[str] = Field(
        default=None, description="Full error traceback for debugging"
    )

    # Performance metrics
    processing_time_ms: Optional[int] = Field(
        default=None, description="Total processing time in milliseconds"
    )

    rule_engine_time_ms: Optional[int] = Field(
        default=None, description="Time spent in rule engine evaluation (ms)"
    )

    db_write_time_ms: Optional[int] = Field(
        default=None, description="Time spent writing to database (ms)"
    )

    notification_time_ms: Optional[int] = Field(
        default=None, description="Time spent sending notifications (ms)"
    )

    # Worker information
    worker_id: Optional[str] = Field(
        default=None, description="ID of the worker that processed the task"
    )

    worker_hostname: Optional[str] = Field(
        default=None, description="Hostname of the worker machine"
    )

    # Additional metadata
    task_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(PGJSON),
        description="Additional flexible metadata",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Task creation timestamp",
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")},
    )

    started_at: Optional[datetime] = Field(
        default=None, description="When processing started"
    )

    completed_at: Optional[datetime] = Field(
        default=None, description="When processing completed (success or failure)"
    )

    last_retry_at: Optional[datetime] = Field(
        default=None, description="Timestamp of last retry attempt"
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp",
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "onupdate": text("CURRENT_TIMESTAMP"),
        },
    )

    # Define composite indexes for common queries
    __table_args__ = (
        Index("idx_queue_status_created", "status", "created_at"),
        Index("idx_queue_correlation", "correlation_id"),
        Index("idx_queue_celery_task", "celery_task_id"),
        Index("idx_queue_transaction", "transaction_id"),
    )


class NotificationTemplate(SQLModel, table=True):
    """
    Notification template model for customizable message generation.

    Templates define the structure and content of notifications sent
    through various channels when fraud is detected.
    """

    __tablename__ = "notification_templates"  # type: ignore

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        description="Template unique identifier",
    )

    name: str = Field(index=True, description="Template name")

    type: TemplateType = Field(description="Template type")

    channel: NotificationChannel = Field(description="Target notification channel")

    # Template content
    subject_template: Optional[str] = Field(
        default=None, description="Subject template (for email)"
    )

    body_template: str = Field(description="Message body template")

    # Template configuration
    enabled: bool = Field(
        default=True, index=True, description="Whether template is active"
    )

    priority: int = Field(default=0, description="Template priority")

    # Template variables configuration (fields to show in notification)
    show_transaction_id: bool = Field(
        default=True, description="Show transaction ID in notification"
    )
    show_amount: bool = Field(
        default=True, description="Show transaction amount in notification"
    )
    show_timestamp: bool = Field(
        default=True, description="Show transaction timestamp in notification"
    )
    show_from_account: bool = Field(
        default=True, description="Show source account in notification"
    )
    show_to_account: bool = Field(
        default=True, description="Show destination account in notification"
    )
    show_triggered_rules: bool = Field(
        default=True, description="Show triggered rules list in notification"
    )
    show_fraud_probability: bool = Field(
        default=True, description="Show fraud probability in notification"
    )
    show_location: bool = Field(
        default=True, description="Show transaction location in notification"
    )
    show_device_info: bool = Field(
        default=True, description="Show device information in notification"
    )

    # Additional custom fields
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(PGJSON),
        description="Additional custom template fields",
    )

    description: Optional[str] = Field(default=None, description="Template description")

    # Usage statistics
    usage_count: int = Field(default=0, description="Number of times template was used")

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Template creation timestamp",
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")},
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Template update timestamp",
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "onupdate": text("CURRENT_TIMESTAMP"),
        },
    )

    # Define indexes for common queries
    __table_args__ = (
        Index("idx_template_channel_enabled", "channel", "enabled"),
        Index("idx_template_type", "type"),
        Index("idx_template_priority", "priority"),
    )


class NotificationChannelConfig(SQLModel, table=True):
    """
    Configuration for notification channels.

    Stores channel-specific settings, credentials, and delivery
    configuration for each notification channel.
    """

    __tablename__ = "notification_channel_configs"  # type: ignore

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        description="Configuration unique identifier",
    )

    channel: NotificationChannel = Field(
        unique=True, index=True, description="Notification channel type"
    )

    enabled: bool = Field(
        default=True, index=True, description="Whether channel is enabled"
    )

    # Channel-specific configuration (encrypted in production)
    config: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(PGJSON),
        description="Channel-specific configuration",
    )

    # Retry configuration
    max_retries: int = Field(default=3, description="Maximum retry attempts")

    retry_delay_seconds: int = Field(
        default=60, description="Delay between retries in seconds"
    )

    # Rate limiting
    rate_limit_per_minute: Optional[int] = Field(
        default=None, description="Maximum notifications per minute"
    )

    description: Optional[str] = Field(default=None, description="Channel description")

    # Statistics
    total_sent: int = Field(default=0, description="Total notifications sent")

    total_failed: int = Field(default=0, description="Total notifications failed")

    last_used_at: Optional[datetime] = Field(
        default=None, description="Last usage timestamp"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Configuration creation timestamp",
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")},
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Configuration update timestamp",
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "onupdate": text("CURRENT_TIMESTAMP"),
        },
    )


class NotificationDelivery(SQLModel, table=True):
    """
    Notification delivery tracking model.

    Tracks individual notification deliveries, their status,
    retry attempts, and delivery results for monitoring and auditing.
    """

    __tablename__ = "notification_deliveries"  # type: ignore

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        description="Delivery unique identifier",
    )

    transaction_id: UUID = Field(index=True, description="Related transaction ID")

    template_id: UUID = Field(
        foreign_key="notification_templates.id",
        index=True,
        description="Template used for notification",
    )

    channel: NotificationChannel = Field(index=True, description="Delivery channel")

    # Delivery content
    subject: Optional[str] = Field(default=None, description="Notification subject")

    body: str = Field(description="Notification body")

    # Recipients
    recipients: List[str] = Field(
        default_factory=list,
        sa_column=Column(PGJSON),
        description="List of recipient addresses/IDs",
    )

    # Delivery status
    status: NotificationStatus = Field(
        default=NotificationStatus.PENDING, index=True, description="Delivery status"
    )

    attempts: int = Field(default=0, description="Number of delivery attempts")

    max_attempts: int = Field(default=3, description="Maximum allowed attempts")

    # Delivery results
    delivered_at: Optional[datetime] = Field(
        default=None, description="Successful delivery timestamp"
    )

    failed_at: Optional[datetime] = Field(
        default=None, description="Final failure timestamp"
    )

    error_message: Optional[str] = Field(
        default=None, description="Error message if failed"
    )

    # Delivery configuration
    priority: int = Field(default=0, description="Delivery priority")

    scheduled_at: Optional[datetime] = Field(
        default=None, description="Scheduled delivery time"
    )

    # Additional metadata (renamed to avoid SQLAlchemy reserved attribute name)
    metadata_: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(PGJSON),
        description="Additional delivery metadata",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Delivery creation timestamp",
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")},
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Delivery update timestamp",
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "onupdate": text("CURRENT_TIMESTAMP"),
        },
    )

    # Define indexes for common queries
    __table_args__ = (
        Index("idx_delivery_status_created", "status", "created_at"),
        Index("idx_delivery_transaction", "transaction_id"),
        Index("idx_delivery_channel_status", "channel", "status"),
        Index("idx_delivery_scheduled", "scheduled_at"),
    )


class NotificationDeliveryAttempt(SQLModel, table=True):
    """
    Individual delivery attempt tracking.

    Tracks each attempt to deliver a notification, including
    timing, errors, and response details for debugging and monitoring.
    """

    __tablename__ = "notification_delivery_attempts"  # type: ignore

    id: UUID = Field(
        default_factory=uuid4, primary_key=True, description="Attempt unique identifier"
    )

    delivery_id: UUID = Field(
        foreign_key="notification_deliveries.id",
        index=True,
        description="Related delivery ID",
    )

    attempt_number: int = Field(description="Attempt number (1-based)")

    # Attempt timing
    started_at: datetime = Field(
        default_factory=datetime.utcnow, description="Attempt start timestamp"
    )

    completed_at: Optional[datetime] = Field(
        default=None, description="Attempt completion timestamp"
    )

    duration_ms: Optional[int] = Field(
        default=None, description="Attempt duration in milliseconds"
    )

    # Attempt results
    success: bool = Field(description="Whether attempt was successful")

    error_message: Optional[str] = Field(
        default=None, description="Error message if failed"
    )

    error_code: Optional[str] = Field(default=None, description="Error code if failed")

    # Response details
    response_status: Optional[str] = Field(
        default=None, description="HTTP response status or channel-specific status"
    )

    response_body: Optional[str] = Field(
        default=None, description="Response body or channel-specific response"
    )

    # Additional metadata (renamed to avoid SQLAlchemy reserved attribute name)
    metadata_: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(PGJSON),
        description="Additional attempt metadata",
    )

    # Define indexes for common queries
    __table_args__ = (
        Index("idx_attempt_delivery", "delivery_id"),
        Index("idx_attempt_started", "started_at"),
        Index("idx_attempt_success", "success"),
    )
