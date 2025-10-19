"""
Prometheus metrics for transaction processing and fraud detection.

This module defines Prometheus counters, gauges, and histograms for monitoring
transaction processing performance, fraud detection rates, and system health.
"""

from prometheus_client import Counter, Gauge, Histogram

# Transaction processing metrics
transactions_enqueued_total = Counter(
    "transactions_enqueued_total",
    "Total number of transactions enqueued for processing",
    ["currency", "transaction_type"],
)

transactions_processed_total = Counter(
    "transactions_processed_total",
    "Total number of transactions successfully processed",
    ["status", "currency"],
)

transactions_failed_total = Counter(
    "transactions_failed_total",
    "Total number of transactions that failed during processing",
    ["error_type", "stage"],
)

# Fraud detection metrics
fraud_detections_total = Counter(
    "fraud_detections_total",
    "Total number of fraud detections",
    ["fraud_type", "rule_type", "risk_level"],
)

# Processing time metrics
transaction_processing_duration = Histogram(
    "transaction_processing_duration_seconds",
    "Time spent processing transactions",
    ["stage"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

# Queue metrics
redis_queue_size = Gauge("redis_queue_size", "Current size of Redis transaction queue")

# System health metrics
active_celery_workers = Gauge(
    "active_celery_workers", "Number of active Celery workers processing transactions"
)
