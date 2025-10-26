"""
Enums for the notifications module.

Defines notification channels (limited to supported channels), statuses,
template types, and other enumerated values used throughout the notification
system. Only Email and Telegram are currently supported.

Note: These enums are now centralized in src.storage.enums to prevent circular imports.
This file re-exports them for backward compatibility.
"""

from src.storage.enums import (
    DeliveryErrorType,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    TemplateType,
)

__all__ = [
    "NotificationChannel",
    "NotificationStatus",
    "TemplateType",
    "NotificationPriority",
    "DeliveryErrorType",
]
