"""
Enums for the rule engine module.

Contains all enumeration types used in rule definitions, evaluation results,
and rule management operations.
"""

from enum import Enum


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

    QUEUED = "queued"
    PROCESSING = "processing"
    APPROVED = "approved"
    FLAGGED = "flagged"
    REJECTED = "rejected"
    FAILED = "failed"


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
