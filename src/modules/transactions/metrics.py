from prometheus_client import Counter

transactions_enqueued_total = Counter(
    "transactions_enqueued_total",
    "Total number of transactions enqueued",
)

transactions_processed_total = Counter(
    "transactions_processed_total",
    "Total number of transactions processed",
)

transactions_failed_total = Counter(
    "transactions_failed_total",
    "Total number of transactions failed during processing",
)


