"""
SQLModel database models for the notifications module.

Contains models for notification templates, channel configurations,
delivery tracking, and related entities used in the notification system.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, Index, text
from sqlalchemy.dialects.postgresql import JSON as PGJSON
from sqlmodel import Field, SQLModel

from .enums import NotificationChannel, NotificationStatus, TemplateType


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
