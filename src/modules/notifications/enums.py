"""
Enums for the notifications module.

Defines notification channels (limited to supported channels), statuses,
template types, and other enumerated values used throughout the notification
system. Only Email and Telegram are currently supported.
"""

from enum import Enum


class NotificationChannel(str, Enum):
    """Available notification delivery channels."""

    EMAIL = "email"
    TELEGRAM = "telegram"


class NotificationStatus(str, Enum):
    """Notification delivery status."""

    PENDING = "pending"
    SENDING = "sending"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TemplateType(str, Enum):
    """Notification template types."""

    FRAUD_ALERT = "fraud_alert"
    TRANSACTION_BLOCKED = "transaction_blocked"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RULE_MATCHED = "rule_matched"
    SYSTEM_ALERT = "system_alert"
    CUSTOM = "custom"


class NotificationPriority(int, Enum):
    """Notification priority levels."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3
    EMERGENCY = 4


class DeliveryErrorType(str, Enum):
    """Types of notification delivery errors."""

    TEMPLATE_ERROR = "template_error"
    CHANNEL_ERROR = "channel_error"
    RECIPIENT_ERROR = "recipient_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "authentication_error"
    CONFIGURATION_ERROR = "configuration_error"
    UNKNOWN_ERROR = "unknown_error"
