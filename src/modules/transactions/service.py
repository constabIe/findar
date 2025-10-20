"""
Transaction service for Redis Stream enqueue operations.

This module handles the asynchronous enqueuing of transactions to Redis Streams
for processing by Celery workers, including correlation ID generation and
Celery task triggering.
"""

from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from redis.asyncio import Redis

from src.core.logging import get_logger

logger = get_logger("transactions.service")

# Redis Stream key for transaction queue
STREAM_KEY = "transactions:stream"
CELERY_QUEUE = "transactions.consume"


async def enqueue_transaction(
    redis_client: Redis, data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Enqueue a transaction to Redis Stream for asynchronous processing.

    This function:
    1. Generates a unique transaction ID and correlation ID
    2. Adds the transaction to Redis Stream with proper formatting
    3. Triggers Celery worker to process the queue
    4. Increments Prometheus metrics (TODO)
    5. Returns transaction metadata for API response

    Args:
        redis_client: Async Redis client instance
        data: Transaction data dictionary from API request

    Returns:
        Dict containing transaction_id, queued_at timestamp, and correlation_id

    Raises:
        Exception: If Redis operations fail or Celery task triggering fails
    """

    logger.info(
        "Starting transaction enqueue process",
        event="enqueue_start",
        amount=data.get("amount"),
        from_account=data.get("from_account"),
        to_account=data.get("to_account"),
    )

    try:
        # Generate unique identifiers
        txn_id = str(uuid4())
        correlation_id = str(uuid4())
        now = datetime.utcnow().isoformat()

        # Prepare payload for Redis Stream
        payload = {
            "id": txn_id,
            "queued_at": now,
            "correlation_id": correlation_id,
            "status": "queued",
            **{k: ("" if v is None else str(v)) for k, v in data.items()},
        }

        # Add to Redis Stream with retention policy
        await redis_client.xadd(
            STREAM_KEY,
            fields=payload, # type: ignore
            maxlen=10000,
            approximate=True,
        )

        logger.info(
            "Transaction enqueued successfully",
            event="enqueue_success",
            transaction_id=txn_id,
            correlation_id=correlation_id,
        )

        # Increment Prometheus metrics
        # transactions_enqueued_total.inc()

        # Trigger Celery worker
        """
        TODO: Use with queue module which is not implemented yet
        try:
            from src.workers import celery_app

            celery_app.send_task("transactions.consume")
            logger.debug(
                "Celery task triggered successfully",
                event="celery_task_triggered",
                task_name="transactions.consume",
            )
        except Exception as e:
            logger.warning(
                "Failed to trigger Celery task",
                event="celery_task_failed",
                error=str(e),
            )
            # Don't fail the enqueue if Celery trigger fails
        """

        return {"id": txn_id, "queued_at": now, "correlation_id": correlation_id}

    except Exception as e:
        logger.error(
            "Transaction enqueue failed",
            event="enqueue_error",
            error=str(e),
            transaction_data=data,
        )
        raise
