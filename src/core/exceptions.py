"""
Custom exceptions for the fraud detection system.

This module defines all custom exceptions used throughout the application,
providing structured error handling with correlation tracking and proper logging.
"""

import uuid
from typing import Any, Dict, Optional


class AppBaseException(Exception):
    """
    Base exception class for all application-specific exceptions.

    Provides common functionality for correlation tracking, error codes,
    and structured error information for the fraud detection system.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        correlation_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize base exception.

        Args:
            message: Human-readable error message
            error_code: Application-specific error code
            correlation_id: Request correlation ID for tracking
            details: Additional context information
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.correlation_id = correlation_id
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for API responses.

        Returns:
            Dict containing error information
        """
        return {
            "error": self.error_code,
            "message": self.message,
            "correlation_id": self.correlation_id,
            "details": self.details,
        }


# ==================== Core Module Exceptions ====================


class ValidationError(AppBaseException):
    """
    Exception raised when input validation fails.

    Used for request validation, data validation, and business rule validation.
    """

    def __init__(
        self,
        message: str = "Validation failed",
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        if field:
            self.details["field"] = field
        if value is not None:
            self.details["invalid_value"] = str(value)


class DatabaseError(AppBaseException):
    """
    Exception raised when database operations fail.

    Used for connection issues, query failures, and transaction problems.
    """

    def __init__(
        self,
        message: str = "Database operation failed",
        operation: Optional[str] = None,
        table: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        if operation:
            self.details["operation"] = operation
        if table:
            self.details["table"] = table


class RuleEvaluationError(AppBaseException):
    """
    Exception raised when fraud detection rule evaluation fails.

    Used for rule engine errors, rule configuration issues, and evaluation problems.
    """

    def __init__(
        self,
        message: str = "Rule evaluation failed",
        rule_name: Optional[str] = None,
        rule_type: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        if rule_name:
            self.details["rule_name"] = rule_name
        if rule_type:
            self.details["rule_type"] = rule_type


class NotificationError(AppBaseException):
    """
    Exception raised when notification delivery fails.

    Used for email and telegram notification channel failures.
    """

    def __init__(
        self,
        message: str = "Notification delivery failed",
        channel: Optional[str] = None,
        recipient: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        if channel:
            self.details["channel"] = channel
        if recipient:
            self.details["recipient"] = recipient


class MLModelError(AppBaseException):
    """
    Exception raised when machine learning model operations fail.

    Used for model loading, prediction, and ML pipeline errors.
    """

    def __init__(
        self,
        message: str = "ML model operation failed",
        model_name: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        if model_name:
            self.details["model_name"] = model_name
        if operation:
            self.details["operation"] = operation


class TransactionError(AppBaseException):
    """Base exception for transaction-related errors."""

    def __init__(
        self,
        message: str = "Transaction operation failed",
        transaction_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        if transaction_id:
            self.details["transaction_id"] = transaction_id


class TransactionNotFoundError(TransactionError):
    """Exception raised when a transaction is not found."""

    def __init__(self, transaction_id: str, **kwargs):
        super().__init__(
            f"Transaction not found: {transaction_id}",
            transaction_id=transaction_id,
            error_code="TRANSACTION_NOT_FOUND",
            **kwargs,
        )


class TransactionValidationError(ValidationError):
    """Exception raised when transaction validation fails."""

    def __init__(
        self,
        message: str = "Transaction validation failed",
        transaction_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        if transaction_id:
            self.details["transaction_id"] = transaction_id


class DuplicateTransactionError(TransactionError):
    """Exception raised when a duplicate transaction is detected."""

    def __init__(self, transaction_id: str, **kwargs):
        super().__init__(
            f"Duplicate transaction detected: {transaction_id}",
            transaction_id=transaction_id,
            error_code="DUPLICATE_TRANSACTION",
            **kwargs,
        )


class QueueError(AppBaseException):
    """Base exception for queue-related errors."""

    def __init__(
        self,
        message: str = "Queue operation failed",
        queue_name: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        if queue_name:
            self.details["queue_name"] = queue_name


class TaskExecutionError(QueueError):
    """Exception raised when Celery task execution fails."""

    def __init__(
        self,
        message: str = "Task execution failed",
        task_name: Optional[str] = None,
        task_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        if task_name:
            self.details["task_name"] = task_name
        if task_id:
            self.details["task_id"] = task_id


class QueueConnectionError(QueueError):
    """Exception raised when queue connection fails."""

    def __init__(self, message: str = "Queue connection failed", **kwargs):
        super().__init__(message, error_code="QUEUE_CONNECTION_ERROR", **kwargs)


class AuthenticationError(AppBaseException):
    """Exception raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, error_code="AUTHENTICATION_FAILED", **kwargs)


class AuthorizationError(AppBaseException):
    """Exception raised when authorization fails."""

    def __init__(
        self,
        message: str = "Access denied",
        required_permission: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, error_code="ACCESS_DENIED", **kwargs)
        if required_permission:
            self.details["required_permission"] = required_permission


# ==================== Rate Limiting Exceptions ====================


class RateLimitExceededError(AppBaseException):
    """Exception raised when rate limits are exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        limit: Optional[int] = None,
        window: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, error_code="RATE_LIMIT_EXCEEDED", **kwargs)
        if limit:
            self.details["limit"] = limit
        if window:
            self.details["window"] = window


# ==================== External Service Exceptions ====================


class ExternalServiceError(AppBaseException):
    """Exception raised when external service calls fail."""

    def __init__(
        self,
        message: str = "External service error",
        service_name: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        if service_name:
            self.details["service_name"] = service_name
        if status_code:
            self.details["status_code"] = status_code


class ServiceUnavailableError(ExternalServiceError):
    """Exception raised when external service is unavailable."""

    def __init__(self, service_name: str, **kwargs):
        super().__init__(
            f"Service unavailable: {service_name}",
            service_name=service_name,
            error_code="SERVICE_UNAVAILABLE",
            **kwargs,
        )


class ConfigurationError(AppBaseException):
    """Exception raised when configuration is invalid or missing."""

    def __init__(
        self,
        message: str = "Configuration error",
        config_key: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, error_code="CONFIGURATION_ERROR", **kwargs)
        if config_key:
            self.details["config_key"] = config_key


class FraudDetectionError(AppBaseException):
    """Exception raised during fraud detection processing."""

    def __init__(
        self,
        message: str = "Fraud detection error",
        detection_type: Optional[str] = None,
        confidence_score: Optional[float] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        if detection_type:
            self.details["detection_type"] = detection_type
        if confidence_score is not None:
            self.details["confidence_score"] = confidence_score


class InsufficientDataError(AppBaseException):
    """Exception raised when insufficient data is available for processing."""

    def __init__(
        self,
        message: str = "Insufficient data for processing",
        required_fields: Optional[list] = None,
        **kwargs,
    ):
        super().__init__(message, error_code="INSUFFICIENT_DATA", **kwargs)
        if required_fields:
            self.details["required_fields"] = required_fields


class MetricsError(AppBaseException):
    """Exception raised when metrics collection or export fails."""

    def __init__(
        self,
        message: str = "Metrics operation failed",
        metric_name: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        if metric_name:
            self.details["metric_name"] = metric_name


class ReportGenerationError(AppBaseException):
    """Exception raised when report generation fails."""

    def __init__(
        self,
        message: str = "Report generation failed",
        report_type: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        if report_type:
            self.details["report_type"] = report_type


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for error tracking."""
    return str(uuid.uuid4())


def get_exception_by_code(error_code: str) -> type[AppBaseException]:
    """
    Get exception class by error code.

    Args:
        error_code: Error code to look up

    Returns:
        Exception class matching the error code

    Raises:
        ValueError: If error code is not found
    """
    exception_map = {
        "VALIDATION_ERROR": ValidationError,
        "DATABASE_ERROR": DatabaseError,
        "RULE_EVALUATION_ERROR": RuleEvaluationError,
        "NOTIFICATION_ERROR": NotificationError,
        "ML_MODEL_ERROR": MLModelError,
        "TRANSACTION_NOT_FOUND": TransactionNotFoundError,
        "DUPLICATE_TRANSACTION": DuplicateTransactionError,
        "QUEUE_CONNECTION_ERROR": QueueConnectionError,
        "AUTHENTICATION_FAILED": AuthenticationError,
        "ACCESS_DENIED": AuthorizationError,
        "RATE_LIMIT_EXCEEDED": RateLimitExceededError,
        "SERVICE_UNAVAILABLE": ServiceUnavailableError,
        "CONFIGURATION_ERROR": ConfigurationError,
        "INSUFFICIENT_DATA": InsufficientDataError,
        "DUPLICATE_TASK": DuplicateTaskError,
        "TASK_NOT_FOUND": TaskNotFoundError,
    }

    if error_code not in exception_map:
        raise ValueError(f"Unknown error code: {error_code}")

    return exception_map[error_code]


class DuplicateTaskError(AppBaseException):
    """
    Exception raised when attempting to create a duplicate queue task.

    This ensures idempotency - tasks with the same correlation_id
    cannot be created multiple times.
    """

    def __init__(
        self,
        message: str,
        correlation_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="DUPLICATE_TASK",
            correlation_id=correlation_id,
            details=details,
        )


class TaskNotFoundError(AppBaseException):
    """
    Exception raised when a queue task is not found.
    """

    def __init__(
        self,
        message: str,
        task_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if task_id:
            details["task_id"] = task_id

        super().__init__(
            message=message,
            error_code="TASK_NOT_FOUND",
            correlation_id=correlation_id,
            details=details,
        )
