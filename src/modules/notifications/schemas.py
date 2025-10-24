"""
Pydantic schemas for the notifications module.

Defines request/response models for notification templates, channels,
delivery tracking, and API endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .enums import NotificationChannel, NotificationStatus, TemplateType


class NotificationTemplateCreate(BaseModel):
    """Schema for creating a new notification template."""

    name: str = Field(min_length=1, max_length=255, description="Template name")
    type: TemplateType = Field(description="Template type")
    channel: NotificationChannel = Field(description="Target notification channel")

    # Template content
    subject_template: Optional[str] = Field(
        default=None, description="Subject template (for email)"
    )
    body_template: str = Field(min_length=1, description="Message body template")

    # Template configuration
    enabled: bool = Field(default=True, description="Whether template is active")
    priority: int = Field(default=0, description="Template priority")

    # Template variables configuration
    include_transaction_id: bool = Field(
        default=True, description="Include transaction ID"
    )
    include_amount: bool = Field(default=True, description="Include transaction amount")
    include_timestamp: bool = Field(
        default=True, description="Include transaction timestamp"
    )
    include_from_account: bool = Field(
        default=True, description="Include source account"
    )
    include_to_account: bool = Field(
        default=True, description="Include destination account"
    )
    include_triggered_rules: bool = Field(
        default=True, description="Include triggered rules list"
    )
    include_fraud_probability: bool = Field(
        default=True, description="Include fraud probability"
    )
    include_location: bool = Field(
        default=False, description="Include transaction location"
    )
    include_device_info: bool = Field(
        default=False, description="Include device information"
    )

    # Additional custom fields
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict, description="Additional custom template fields"
    )

    description: Optional[str] = Field(
        default=None, max_length=1000, description="Template description"
    )


class NotificationTemplateUpdate(BaseModel):
    """Schema for updating an existing notification template."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Template name"
    )
    type: Optional[TemplateType] = Field(None, description="Template type")
    channel: Optional[NotificationChannel] = Field(
        None, description="Target notification channel"
    )

    # Template content
    subject_template: Optional[str] = Field(None, description="Subject template")
    body_template: Optional[str] = Field(None, description="Message body template")

    # Template configuration
    enabled: Optional[bool] = Field(None, description="Whether template is active")
    priority: Optional[int] = Field(None, description="Template priority")

    # Template variables configuration
    include_transaction_id: Optional[bool] = Field(
        None, description="Include transaction ID"
    )
    include_amount: Optional[bool] = Field(
        None, description="Include transaction amount"
    )
    include_timestamp: Optional[bool] = Field(
        None, description="Include transaction timestamp"
    )
    include_from_account: Optional[bool] = Field(
        None, description="Include source account"
    )
    include_to_account: Optional[bool] = Field(
        None, description="Include destination account"
    )
    include_triggered_rules: Optional[bool] = Field(
        None, description="Include triggered rules list"
    )
    include_fraud_probability: Optional[bool] = Field(
        None, description="Include fraud probability"
    )
    include_location: Optional[bool] = Field(
        None, description="Include transaction location"
    )
    include_device_info: Optional[bool] = Field(
        None, description="Include device information"
    )

    # Additional custom fields
    custom_fields: Optional[Dict[str, Any]] = Field(
        None, description="Additional custom template fields"
    )

    description: Optional[str] = Field(
        None, max_length=1000, description="Template description"
    )


class NotificationTemplateResponse(BaseModel):
    """Schema for notification template API responses."""

    id: UUID = Field(description="Template ID")
    name: str = Field(description="Template name")
    type: TemplateType = Field(description="Template type")
    channel: NotificationChannel = Field(description="Target notification channel")

    # Template content
    subject_template: Optional[str] = Field(description="Subject template")
    body_template: str = Field(description="Message body template")

    # Template configuration
    enabled: bool = Field(description="Whether template is active")
    priority: int = Field(description="Template priority")

    # Template variables configuration
    include_transaction_id: bool = Field(description="Include transaction ID")
    include_amount: bool = Field(description="Include transaction amount")
    include_timestamp: bool = Field(description="Include transaction timestamp")
    include_from_account: bool = Field(description="Include source account")
    include_to_account: bool = Field(description="Include destination account")
    include_triggered_rules: bool = Field(description="Include triggered rules list")
    include_fraud_probability: bool = Field(description="Include fraud probability")
    include_location: bool = Field(description="Include transaction location")
    include_device_info: bool = Field(description="Include device information")

    # Additional custom fields
    custom_fields: Dict[str, Any] = Field(
        description="Additional custom template fields"
    )

    description: Optional[str] = Field(description="Template description")

    # Statistics
    usage_count: int = Field(description="Number of times template was used")

    # Timestamps
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    class Config:
        from_attributes = True


class NotificationChannelConfigCreate(BaseModel):
    """Schema for creating notification channel configuration."""

    channel: NotificationChannel = Field(description="Notification channel type")
    enabled: bool = Field(default=True, description="Whether channel is enabled")

    # Channel-specific configuration
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Channel-specific configuration"
    )

    # Retry configuration
    max_retries: int = Field(
        default=3, ge=0, le=10, description="Maximum retry attempts"
    )
    retry_delay_seconds: int = Field(
        default=60, ge=1, le=3600, description="Delay between retries in seconds"
    )

    # Rate limiting
    rate_limit_per_minute: Optional[int] = Field(
        default=None, ge=1, description="Maximum notifications per minute"
    )

    description: Optional[str] = Field(
        default=None, max_length=500, description="Channel description"
    )


class NotificationChannelConfigResponse(BaseModel):
    """Schema for notification channel configuration responses."""

    id: UUID = Field(description="Configuration ID")
    channel: NotificationChannel = Field(description="Notification channel type")
    enabled: bool = Field(description="Whether channel is enabled")

    # Channel-specific configuration (masked for security)
    config: Dict[str, Any] = Field(description="Channel-specific configuration")

    # Retry configuration
    max_retries: int = Field(description="Maximum retry attempts")
    retry_delay_seconds: int = Field(description="Delay between retries in seconds")

    # Rate limiting
    rate_limit_per_minute: Optional[int] = Field(
        description="Maximum notifications per minute"
    )

    description: Optional[str] = Field(description="Channel description")

    # Statistics
    total_sent: int = Field(description="Total notifications sent")
    total_failed: int = Field(description="Total notifications failed")
    last_used_at: Optional[datetime] = Field(description="Last usage timestamp")

    # Timestamps
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    class Config:
        from_attributes = True


class NotificationDeliveryCreate(BaseModel):
    """Schema for creating a notification delivery record."""

    transaction_id: UUID = Field(description="Related transaction ID")
    template_id: Optional[UUID] = Field(default=None, description="Template used for notification")
    channel: NotificationChannel = Field(description="Delivery channel")

    # Delivery content
    subject: Optional[str] = Field(default=None, description="Notification subject")
    body: str = Field(description="Notification body")

    # Recipients
    recipients: List[str] = Field(
        min_items=1, description="List of recipient addresses/IDs"
    )

    # Delivery configuration
    priority: int = Field(default=0, description="Delivery priority")
    scheduled_at: Optional[datetime] = Field(
        default=None, description="Scheduled delivery time"
    )

    # Additional metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional delivery metadata"
    )


class NotificationDeliveryResponse(BaseModel):
    """Schema for notification delivery responses."""

    id: UUID = Field(description="Delivery ID")
    transaction_id: UUID = Field(description="Related transaction ID")
    template_id: UUID = Field(description="Template used for notification")
    channel: NotificationChannel = Field(description="Delivery channel")

    # Delivery content
    subject: Optional[str] = Field(description="Notification subject")
    body: str = Field(description="Notification body")

    # Recipients
    recipients: List[str] = Field(description="List of recipient addresses/IDs")

    # Delivery status
    status: NotificationStatus = Field(description="Delivery status")
    attempts: int = Field(description="Number of delivery attempts")
    max_attempts: int = Field(description="Maximum allowed attempts")

    # Delivery results
    delivered_at: Optional[datetime] = Field(
        description="Successful delivery timestamp"
    )
    failed_at: Optional[datetime] = Field(description="Final failure timestamp")
    error_message: Optional[str] = Field(description="Error message if failed")

    # Delivery configuration
    priority: int = Field(description="Delivery priority")
    scheduled_at: Optional[datetime] = Field(description="Scheduled delivery time")

    # Additional metadata
    metadata: Dict[str, Any] = Field(description="Additional delivery metadata")

    # Timestamps
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    class Config:
        from_attributes = True


class NotificationSendRequest(BaseModel):
    """Schema for sending notifications via API."""

    transaction_id: UUID = Field(description="Transaction ID to notify about")
    template_ids: Optional[List[UUID]] = Field(
        default=None, description="Specific templates to use (None = all enabled)"
    )
    channels: Optional[List[NotificationChannel]] = Field(
        default=None, description="Specific channels to use (None = all enabled)"
    )
    recipients: Optional[Dict[NotificationChannel, List[str]]] = Field(
        default=None, description="Channel-specific recipients override"
    )
    priority: int = Field(default=0, description="Notification priority")
    scheduled_at: Optional[datetime] = Field(
        default=None, description="Scheduled delivery time"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class NotificationSendResponse(BaseModel):
    """Schema for notification send responses."""

    delivery_ids: List[UUID] = Field(description="Created delivery record IDs")
    total_recipients: int = Field(description="Total number of recipients")
    channels_used: List[NotificationChannel] = Field(
        description="Channels used for delivery"
    )
    message: str = Field(description="Success message")


class NotificationStatsResponse(BaseModel):
    """Schema for notification statistics."""

    total_deliveries: int = Field(description="Total notification deliveries")
    successful_deliveries: int = Field(
        description="Successfully delivered notifications"
    )
    failed_deliveries: int = Field(description="Failed notification deliveries")
    pending_deliveries: int = Field(description="Pending notification deliveries")

    # Channel-specific stats
    channel_stats: Dict[NotificationChannel, Dict[str, int]] = Field(
        description="Statistics per channel"
    )

    # Template usage stats
    template_usage: Dict[UUID, int] = Field(description="Template usage counts")

    # Time-based stats
    deliveries_last_24h: int = Field(description="Deliveries in last 24 hours")
    deliveries_last_7d: int = Field(description="Deliveries in last 7 days")

    # Error rates
    error_rate: float = Field(description="Overall error rate")
    avg_delivery_time_seconds: Optional[float] = Field(
        description="Average delivery time in seconds"
    )


class NotificationTemplateListResponse(BaseModel):
    """Schema for paginated template list responses."""

    templates: List[NotificationTemplateResponse] = Field(
        description="List of templates"
    )
    total: int = Field(description="Total number of templates")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of templates per page")
    pages: int = Field(description="Total number of pages")


class NotificationDeliveryListResponse(BaseModel):
    """Schema for paginated delivery list responses."""

    deliveries: List[NotificationDeliveryResponse] = Field(
        description="List of deliveries"
    )
    total: int = Field(description="Total number of deliveries")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of deliveries per page")
    pages: int = Field(description="Total number of pages")
