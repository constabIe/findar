"""
Notifier module for sending alerts.

This module handles notification delivery through various channels
when suspicious transactions are detected.

Responsibilities:
- Send alerts via multiple channels (Email, Telegram)
- Queue notifications for async delivery
- Handle notification failures and retries
- Track notification status
- Support notification templates
- Template-based message generation
- Fault-tolerant delivery with retry logic
- Integration with reporting metrics
"""

from .enums import (
    DeliveryErrorType,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    TemplateType,
)
from src.storage.models import (
    NotificationChannelConfig,
    NotificationDelivery,
    NotificationDeliveryAttempt,
    NotificationTemplate,
)
from .repository import NotificationRepository
from .routes import router
from .schemas import (
    NotificationChannelConfigCreate,
    NotificationChannelConfigResponse,
    NotificationChannelsResponse,
    NotificationChannelsUpdate,
    NotificationDeliveryCreate,
    NotificationDeliveryListResponse,
    NotificationDeliveryResponse,
    NotificationSendRequest,
    NotificationSendResponse,
    NotificationStatsResponse,
    NotificationTemplateCreate,
    NotificationTemplateListResponse,
    NotificationTemplateResponse,
    NotificationTemplateUpdate,
    TemplateFieldsUpdate,
    UserNotificationTemplateResponse,
    UserNotificationTemplatesResponse,
)
from .senders import BaseSender, EmailSender, TelegramSender
from .service import NotificationService

__all__ = [
    # Enums
    "NotificationChannel",
    "NotificationStatus",
    "TemplateType",
    "NotificationPriority",
    "DeliveryErrorType",
    # Models
    "NotificationTemplate",
    "NotificationChannelConfig",
    "NotificationDelivery",
    "NotificationDeliveryAttempt",
    # Schemas
    "NotificationTemplateCreate",
    "NotificationTemplateUpdate",
    "NotificationTemplateResponse",
    "NotificationTemplateListResponse",
    "NotificationChannelConfigCreate",
    "NotificationChannelConfigResponse",
    "NotificationDeliveryCreate",
    "NotificationDeliveryResponse",
    "NotificationDeliveryListResponse",
    "NotificationSendRequest",
    "NotificationSendResponse",
    "NotificationStatsResponse",
    "TemplateFieldsUpdate",
    "UserNotificationTemplateResponse",
    "UserNotificationTemplatesResponse",
    "NotificationChannelsResponse",
    "NotificationChannelsUpdate",
    # Senders
    "BaseSender",
    "EmailSender",
    "TelegramSender",
    # Services
    "NotificationService",
    "NotificationRepository",
    # Routes
    "router",
]
