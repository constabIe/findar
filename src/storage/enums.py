"""
Enums for database models.

Contains all enumeration types used across the application's database models.
This centralized location prevents circular imports between models and modules.
"""

from enum import Enum


# ==================== Rule Engine Enums ====================

class RuleType(str, Enum):
    """Types of fraud detection rules."""

    THRESHOLD = "threshold"
    PATTERN = "pattern"
    COMPOSITE = "composite"
    ML = "ml"


class RuleStatus(str, Enum):
    """Rule execution status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DISABLED = "disabled"
    ERROR = "error"


class TransactionStatus(str, Enum):
    """Transaction processing status."""

    PENDING = "pending"
    APPROVED = "approved"
    FLAGGED = "flagged"
    FAILED = "failed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class TransactionType(str, Enum):
    """Types of financial transactions."""

    TRANSFER = "transfer"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    PAYMENT = "payment"


class RuleMatchStatus(str, Enum):
    """Result of rule evaluation."""

    MATCHED = "matched"
    NOT_MATCHED = "not_matched"
    ERROR = "error"
    SKIPPED = "skipped"


class RiskLevel(str, Enum):
    """Risk level assessment."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThresholdOperator(str, Enum):
    """Operators for threshold comparisons."""

    GREATER_THAN = "gt"
    GREATER_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_EQUAL = "lte"
    EQUAL = "eq"
    NOT_EQUAL = "ne"
    BETWEEN = "between"
    NOT_BETWEEN = "not_between"


class TimeWindow(str, Enum):
    """Time windows for pattern and aggregation rules."""

    MINUTE = "1m"
    FIVE_MINUTES = "5m"
    TEN_MINUTES = "10m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    HOUR = "1h"
    SIX_HOURS = "6h"
    TWELVE_HOURS = "12h"
    DAY = "1d"
    WEEK = "1w"
    MONTH = "1M"


class CompositeOperator(str, Enum):
    """Logical operators for composite rules."""

    AND = "and"
    OR = "or"
    NOT = "not"
    XOR = "xor"


class CacheStatus(str, Enum):
    """Cache status for Redis stored rules."""

    CACHED = "cached"
    EXPIRED = "expired"
    MISSING = "missing"
    INVALID = "invalid"


# ==================== Queue Enums ====================

class TaskStatus(str, Enum):
    """
    Status of a queue task processing.
    """

    PENDING = "pending"  # Task created, waiting for worker
    PROCESSING = "processing"  # Task being processed by worker
    COMPLETED = "completed"  # Successfully completed
    FAILED = "failed"  # Failed after all retries


class TaskPriority(int, Enum):
    """
    Priority levels for task processing.
    Higher number = higher priority.
    """

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class ErrorType(str, Enum):
    """
    Types of errors that can occur during task processing.
    """

    VALIDATION_ERROR = "validation_error"  # Invalid transaction data
    DATABASE_ERROR = "database_error"  # DB connection/query issues
    RULE_ENGINE_ERROR = "rule_engine_error"  # Rule evaluation failure
    NOTIFICATION_ERROR = "notification_error"  # Failed to send notification
    TIMEOUT_ERROR = "timeout_error"  # Task execution timeout
    UNKNOWN_ERROR = "unknown_error"  # Unexpected errors


# ==================== Notification Enums ====================

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
