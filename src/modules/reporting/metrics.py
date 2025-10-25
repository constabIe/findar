"""
Prometheus metrics for queue processing and transaction monitoring.

Provides counters, gauges, and histograms for tracking system performance,
queue statistics, and processing metrics.
"""

from prometheus_client import Counter, Gauge, Histogram

# Task processing counters
tasks_total = Counter(
    "queue_tasks_total",
    "Total number of tasks created",
    ["status"],  # Labels: pending, processing, completed, failed, retry
)

tasks_submitted = Counter(
    "queue_tasks_submitted_total",
    "Total number of tasks submitted to queue",
)

tasks_completed = Counter(
    "queue_tasks_completed_total",
    "Total number of successfully completed tasks",
)

tasks_failed = Counter(
    "queue_tasks_failed_total",
    "Total number of failed tasks",
    ["error_type"],  # Labels: validation_error, database_error, etc.
)

tasks_retried = Counter(
    "queue_tasks_retried_total",
    "Total number of task retry attempts",
)

# Processing time metrics
processing_time = Histogram(
    "queue_processing_duration_seconds",
    "Time spent processing tasks",
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),  # seconds
)

rule_engine_time = Histogram(
    "queue_rule_engine_duration_seconds",
    "Time spent in rule engine evaluation",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),  # seconds
)

db_write_time = Histogram(
    "queue_db_write_duration_seconds",
    "Time spent writing to database",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0),  # seconds
)

notification_time = Histogram(
    "queue_notification_duration_seconds",
    "Time spent sending notifications",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),  # seconds
)

# Queue statistics
queue_length = Gauge(
    "queue_pending_tasks",
    "Number of tasks currently pending in queue",
    ["queue_name"],  # Labels: transactions, notifications
)

queue_processing = Gauge(
    "queue_processing_tasks",
    "Number of tasks currently being processed",
)

# Worker metrics
worker_active = Gauge(
    "queue_workers_active",
    "Number of active workers",
)

# Error metrics
errors_total = Counter(
    "queue_errors_total",
    "Total number of errors by type",
    ["error_type"],
)


# Helper functions for metrics collection
def increment_task_counter(status: str) -> None:
    """
    Increment task counter for specific status.

    Args:
        status: Task status (pending, processing, completed, failed, retry)
    """
    tasks_total.labels(status=status).inc()


def increment_submitted_counter() -> None:
    """Increment submitted tasks counter."""
    tasks_submitted.inc()


def increment_completed_counter() -> None:
    """Increment completed tasks counter."""
    tasks_completed.inc()


def increment_failed_counter(error_type: str) -> None:
    """
    Increment failed tasks counter.

    Args:
        error_type: Type of error that caused failure
    """
    tasks_failed.labels(error_type=error_type).inc()


def increment_retry_counter() -> None:
    """Increment retry attempts counter."""
    tasks_retried.inc()


def observe_processing_time(duration_seconds: float) -> None:
    """
    Record processing time observation.

    Args:
        duration_seconds: Processing duration in seconds
    """
    processing_time.observe(duration_seconds)


def observe_rule_engine_time(duration_seconds: float) -> None:
    """
    Record rule engine processing time.

    Args:
        duration_seconds: Rule engine duration in seconds
    """
    rule_engine_time.observe(duration_seconds)


def observe_db_write_time(duration_seconds: float) -> None:
    """
    Record database write time.

    Args:
        duration_seconds: DB write duration in seconds
    """
    db_write_time.observe(duration_seconds)


def observe_notification_time(duration_seconds: float) -> None:
    """
    Record notification send time.

    Args:
        duration_seconds: Notification duration in seconds
    """
    notification_time.observe(duration_seconds)


def set_queue_length(queue_name: str, length: int) -> None:
    """
    Set current queue length.

    Args:
        queue_name: Name of the queue
        length: Current number of pending tasks
    """
    queue_length.labels(queue_name=queue_name).set(length)


def set_processing_count(count: int) -> None:
    """
    Set number of currently processing tasks.

    Args:
        count: Number of tasks being processed
    """
    queue_processing.set(count)


def set_active_workers(count: int) -> None:
    """
    Set number of active workers.

    Args:
        count: Number of active workers
    """
    worker_active.set(count)


def increment_error_counter(error_type: str) -> None:
    """
    Increment error counter.

    Args:
        error_type: Type of error encountered
    """
    errors_total.labels(error_type=error_type).inc()


# Transaction counters by status
transactions_total = Counter(
    "transactions_total",
    "Total number of transactions by status",
    ["status"],  # Labels: pending, processed, alerted, reviewed, rejected
)

# Transaction counters by type
transactions_by_type = Counter(
    "transactions_by_type_total",
    "Total number of transactions by type",
    ["type"],  # Labels: transfer, payment, withdrawal, deposit
)

# Transaction processing time
transaction_processing_duration = Histogram(
    "transaction_processing_duration_seconds",
    "Time spent processing a single transaction end-to-end",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),  # seconds
)


# Rule evaluation counters
rules_evaluated_total = Counter(
    "rules_evaluated_total",
    "Total number of rule evaluations",
    ["rule_type"],  # Labels: threshold, pattern, composite, ml
)

# Rule match counters
rules_matched_total = Counter(
    "rules_matched_total",
    "Total number of rule matches (when rule fired)",
    ["rule_type", "rule_id"],  # Labels: rule_type, rule_id
)

# Rule execution time by type
rule_execution_duration = Histogram(
    "rule_execution_duration_seconds",
    "Time spent executing a single rule",
    ["rule_type"],  # Labels: threshold, pattern, composite, ml
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),  # seconds
)

# Rule match rate gauge (for monitoring dashboard)
rule_match_rate = Gauge(
    "rule_match_rate",
    "Current match rate for each rule (matches/evaluations)",
    ["rule_id", "rule_type"],
)

# Transaction review metrics
transaction_reviews_total = Counter(
    "transaction_reviews_total",
    "Total number of transaction reviews by analysts",
    ["status", "success"],  # status: accepted/rejected, success: true/false
)

transaction_review_duration = Histogram(
    "transaction_review_duration_seconds",
    "Time spent processing transaction review",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),  # seconds
)


def increment_transaction_counter(status: str) -> None:
    """
    Increment transaction counter for specific status.

    Args:
        status: Transaction status (pending, processed, alerted, reviewed, rejected)
    """
    transactions_total.labels(status=status).inc()


def increment_transaction_by_type_counter(transaction_type: str) -> None:
    """
    Increment transaction counter by type.

    Args:
        transaction_type: Type of transaction (transfer, payment, withdrawal, deposit)
    """
    transactions_by_type.labels(type=transaction_type).inc()


def observe_transaction_processing_time(duration_seconds: float) -> None:
    """
    Record transaction processing time observation.

    Args:
        duration_seconds: Total processing duration in seconds
    """
    transaction_processing_duration.observe(duration_seconds)


def increment_rule_evaluated_counter(rule_type: str) -> None:
    """
    Increment counter when a rule is evaluated.

    Args:
        rule_type: Type of rule (threshold, pattern, composite, ml)
    """
    rules_evaluated_total.labels(rule_type=rule_type).inc()


def increment_rule_matched_counter(rule_type: str, rule_id: str) -> None:
    """
    Increment counter when a rule matches (fires).

    Args:
        rule_type: Type of rule (threshold, pattern, composite, ml)
        rule_id: Unique identifier of the rule
    """
    rules_matched_total.labels(rule_type=rule_type, rule_id=rule_id).inc()


def observe_rule_execution_time(rule_type: str, duration_seconds: float) -> None:
    """
    Record rule execution time observation.

    Args:
        rule_type: Type of rule (threshold, pattern, composite, ml)
        duration_seconds: Rule execution duration in seconds
    """
    rule_execution_duration.labels(rule_type=rule_type).observe(duration_seconds)


def update_rule_match_rate(rule_id: str, rule_type: str, match_rate: float) -> None:
    """
    Update rule match rate gauge.

    Args:
        rule_id: Unique identifier of the rule
        rule_type: Type of rule (threshold, pattern, composite, ml)
        match_rate: Match rate as a float (0.0 to 1.0)
    """
    rule_match_rate.labels(rule_id=rule_id, rule_type=rule_type).set(match_rate)


def increment_transaction_review_counter(status: str, success: bool) -> None:
    """
    Increment transaction review counter.

    Args:
        status: Review status (accepted or rejected)
        success: Whether the review operation was successful
    """
    transaction_reviews_total.labels(status=status, success=str(success).lower()).inc()


def observe_transaction_review_duration(duration_seconds: float) -> None:
    """
    Record transaction review processing time.

    Args:
        duration_seconds: Review processing duration in seconds
    """
    transaction_review_duration.observe(duration_seconds)
