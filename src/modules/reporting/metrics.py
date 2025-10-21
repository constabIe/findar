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
