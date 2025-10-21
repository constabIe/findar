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
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.modules.queue.repository import QueueRepository
from src.modules.queue.schemas import TaskCreate
from src.modules.rule_engine.enums import TransactionType
from src.modules.transactions.repository import TransactionRepository

logger = get_logger("transactions.service")

# Redis Stream key for transaction queue
STREAM_KEY = "transactions:stream"
CELERY_QUEUE = "transactions.consume"


async def enqueue_transaction(
    redis_client: Redis, session: AsyncSession, data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Enqueue a transaction to Redis Stream and save to PostgreSQL.

    This function:
    1. Generates a unique transaction ID and correlation ID
    2. Saves transaction to PostgreSQL database
    3. Creates QueueTask record for tracking
    4. Adds the transaction to Redis Stream with proper formatting
    5. Triggers Celery worker to process the queue
    6. Returns transaction metadata for API response

    Args:
        redis_client: Async Redis client instance
        session: Async SQLAlchemy session for database operations
        data: Transaction data dictionary from API request

    Returns:
        Dict containing transaction_id, queued_at timestamp, and correlation_id

    Raises:
        Exception: If database, Redis, or Celery operations fail
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
        txn_id = uuid4()
        correlation_id = str(uuid4())
        now = datetime.utcnow()

        # Initialize repositories
        transaction_repo = TransactionRepository(session)
        queue_repo = QueueRepository(session)

        # 1. Create transaction in PostgreSQL
        transaction_type_str = data.get("type", "transfer")
        try:
            transaction_type = TransactionType(transaction_type_str)
        except ValueError:
            # Default to TRANSFER if type is invalid
            transaction_type = TransactionType.TRANSFER
            logger.warning(
                f"Invalid transaction type '{transaction_type_str}', defaulting to TRANSFER"
            )

        transaction = await transaction_repo.create_transaction(
            transaction_id=txn_id,
            amount=float(data.get("amount", 0)),
            from_account=str(data.get("from_account", "")),
            to_account=str(data.get("to_account", "")),
            transaction_type=transaction_type,
            correlation_id=correlation_id,
            currency=data.get("currency", "USD"),
            description=data.get("description"),
            merchant_id=data.get("merchant_id"),
            location=data.get("location"),
            device_id=data.get("device_id"),
            ip_address=data.get("ip_address"),
        )

        logger.info(
            "Transaction saved to database",
            event="transaction_db_save",
            transaction_id=str(txn_id),
            correlation_id=correlation_id,
        )

        # 2. Create QueueTask for tracking
        queue_task = await queue_repo.create_task(
            task_data=TaskCreate(
                correlation_id=correlation_id,
                transaction_id=txn_id,
                max_retries=3,
                task_metadata={"source": "api", "enqueued_at": now.isoformat()},
            )
        )

        logger.info(
            "Queue task created",
            event="queue_task_created",
            queue_task_id=str(queue_task.id),
            correlation_id=correlation_id,
        )

        # 3. Prepare payload for Redis Stream
        payload = {
            "id": str(txn_id),
            "queued_at": now.isoformat(),
            "correlation_id": correlation_id,
            "status": "queued",
            **{k: ("" if v is None else str(v)) for k, v in data.items()},
        }

        # 4. Add to Redis Stream with retention policy
        await redis_client.xadd(
            STREAM_KEY,
            fields=payload,  # type: ignore
            maxlen=10000,
            approximate=True,
        )

        logger.info(
            "Transaction enqueued to Redis Stream",
            event="redis_stream_enqueue",
            transaction_id=str(txn_id),
            correlation_id=correlation_id,
        )

        # 5. Trigger Celery worker
        try:
            from src.modules.queue.celery_config import celery_app

            celery_task = celery_app.send_task(
                "queue.process_transaction",
                args=[
                    payload,  # transaction_data
                    correlation_id,  # correlation_id
                    str(queue_task.id),  # queue_task_id
                ],
                queue="transactions",
            )

            # Update queue task with celery_task_id
            from src.modules.queue.schemas import TaskUpdate

            await queue_repo.update_task(
                task_id=queue_task.id,
                update_data=TaskUpdate(celery_task_id=celery_task.id),
            )

            logger.info(
                "Celery task triggered successfully",
                event="celery_task_triggered",
                task_name="queue.process_transaction",
                celery_task_id=celery_task.id,
                queue_task_id=str(queue_task.id),
            )

        except Exception as e:
            logger.warning(
                "Failed to trigger Celery task",
                event="celery_task_failed",
                error=str(e),
            )
            # Don't fail the enqueue if Celery trigger fails
            # The transaction is already saved and can be processed later

        # 6. Commit the database transaction
        await session.commit()

        logger.info(
            "Transaction enqueue completed successfully",
            event="enqueue_complete",
            transaction_id=str(txn_id),
            correlation_id=correlation_id,
        )

        return {
            "id": str(txn_id),
            "queued_at": now.isoformat(),
            "correlation_id": correlation_id,
        }

    except Exception as e:
        # Rollback database transaction on error
        await session.rollback()

        logger.error(
            "Transaction enqueue failed",
            event="enqueue_error",
            error=str(e),
            transaction_data=data,
        )
        raise
