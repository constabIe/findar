"""
Celery tasks for asynchronous transaction processing.

This module contains Celery tasks that consume transactions from Redis Streams
and persist them to PostgreSQL, including error handling and status updates.
"""

from datetime import datetime
from typing import Any, Dict

from celery import shared_task
from redis import Redis as SyncRedis

from src.core.logging import get_logger
from src.modules.reporting.metrics import (
    transactions_failed_total,
    transactions_processed_total,
)
from src.modules.transactions.models import Transaction
from src.modules.transactions.service import STREAM_KEY
from src.storage.redis import get_sync_redis
from src.storage.sql.engine import get_async_session_maker

logger = get_logger("workers.transactions")


@shared_task(name="transactions.consume")
def consume_transactions() -> int:
    """
    Consume transactions from Redis Stream and persist to PostgreSQL.

    This Celery task:
    1. Creates Redis consumer group for reliable message processing
    2. Reads transactions from Redis Stream using consumer group
    3. Persists each transaction to PostgreSQL using async session
    4. Updates transaction status and handles errors gracefully
    5. Acknowledges processed messages and tracks metrics

    Returns:
        int: Number of transactions processed in this batch

    Raises:
        Exception: If critical system errors occur (Redis/DB connection failures)
    """
    logger.info("Starting transaction consumption task", event="consume_start")

    try:
        # Get Redis and database connections
        redis: SyncRedis = get_sync_redis()
        session_maker = get_async_session_maker()

        # Create consumer group if it doesn't exist
        try:
            redis.xgroup_create(
                name=STREAM_KEY, groupname="transactions", id="0-0", mkstream=True
            )
            logger.info("Created Redis consumer group", event="consumer_group_created")
        except Exception as e:
            msg = str(e)
            if "BUSYGROUP" not in msg:
                logger.error(
                    "Failed to create consumer group",
                    event="consumer_group_error",
                    error=msg,
                )
                raise
            logger.debug("Consumer group already exists", event="consumer_group_exists")

        processed = 0
        consumer = "worker"

        logger.info("Starting message consumption loop", event="consume_loop_start")

        # Process messages in batches
        while True:
            try:
                # Read messages from consumer group
                messages = redis.xreadgroup(
                    groupname="transactions",
                    consumername=consumer,
                    streams={STREAM_KEY: ">"},
                    count=100,
                    block=3000,  # 3 second timeout
                )

                if not messages:
                    logger.debug(
                        "No messages available, continuing", event="no_messages"
                    )
                    break

                logger.info(
                    "Received message batch",
                    event="message_batch_received",
                    count=len(messages[0][1]) if messages else 0,
                )

                # Process each message
                for _, entries in messages:
                    for entry_id, fields in entries:
                        processed += 1

                        logger.debug(
                            "Processing transaction message",
                            event="message_process_start",
                            entry_id=entry_id,
                            transaction_id=fields.get("id"),
                        )

                        try:
                            # Persist transaction to database
                            _persist_transaction(session_maker, fields)

                            # Acknowledge successful processing
                            redis.xack(STREAM_KEY, "transactions", entry_id)

                            # Update metrics
                            transactions_processed_total.labels(
                                status="processed",
                                currency=fields.get("currency", "unknown"),
                            ).inc()

                            logger.info(
                                "Transaction processed successfully",
                                event="transaction_processed",
                                transaction_id=fields.get("id"),
                                correlation_id=fields.get("correlation_id"),
                            )

                        except Exception as e:
                            # Handle processing errors
                            logger.error(
                                "Transaction processing failed",
                                event="transaction_process_error",
                                transaction_id=fields.get("id"),
                                error=str(e),
                                exc_info=True,
                            )

                            # Update failure metrics
                            transactions_failed_total.labels(
                                error_type=type(e).__name__, stage="persistence"
                            ).inc()

                            # Write failure marker to stream
                            redis.xadd(
                                STREAM_KEY,
                                {
                                    "id": fields.get("id", ""),
                                    "correlation_id": fields.get("correlation_id", ""),
                                    "status": "failed",
                                    "error": str(e),
                                    "failed_at": datetime.utcnow().isoformat(),
                                },
                                maxlen=10000,
                                approximate=True,
                            )

                            # Still acknowledge to prevent reprocessing
                            redis.xack(STREAM_KEY, "transactions", entry_id)

            except Exception as e:
                logger.error(
                    "Error in message processing loop",
                    event="consume_loop_error",
                    error=str(e),
                    exc_info=True,
                )
                break

        logger.info(
            "Transaction consumption completed",
            event="consume_complete",
            processed_count=processed,
        )

        return processed

    except Exception as e:
        logger.error(
            "Critical error in transaction consumption",
            event="consume_critical_error",
            error=str(e),
            exc_info=True,
        )
        raise


def _persist_transaction(session_maker, payload: Dict[str, Any]) -> None:
    """
    Persist a single transaction to PostgreSQL database.

    Args:
        session_maker: Async session maker for database operations
        payload: Transaction data from Redis Stream

    Raises:
        Exception: If database operations fail
    """
    import asyncio

    async def _async_persist():
        async with session_maker() as session:  # type: AsyncSession
            # Create transaction model instance
            txn = Transaction(
                id=payload.get("id"),
                amount=float(payload.get("amount", 0)),
                from_account=payload.get("from_account", ""),
                to_account=payload.get("to_account", ""),
                timestamp=datetime.fromisoformat(payload.get("timestamp"))
                if payload.get("timestamp")
                else datetime.utcnow(),
                type=payload.get("type", ""),
                correlation_id=payload.get("correlation_id", ""),
                status="processed",  # Update status to processed
                currency=payload.get("currency", "USD"),
                description=(payload.get("description") or None),
                merchant_id=(payload.get("merchant_id") or None),
                location=(payload.get("location") or None),
                device_id=(payload.get("device_id") or None),
                ip_address=(payload.get("ip_address") or None),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            # Add to session and commit
            session.add(txn)
            await session.commit()

            logger.debug(
                "Transaction persisted to database",
                event="transaction_persisted",
                transaction_id=txn.id,
            )

    # Run async database operation
    asyncio.get_event_loop().run_until_complete(_async_persist())
