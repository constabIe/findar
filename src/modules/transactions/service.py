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
from src.modules.reporting.metrics import (
    increment_transaction_by_type_counter,
    increment_transaction_counter,
)
from src.modules.rule_engine.enums import TransactionType
from src.modules.transactions.repository import TransactionRepository

logger = get_logger("transactions.service")

# Redis Stream key for transaction queue
STREAM_KEY = "transactions:stream"
CELERY_QUEUE = "transactions.consume"


async def enqueue_transaction(
    redis_client: Redis,
    session: AsyncSession,
    data: Dict[str, Any],
    max_composite_depth: int = 5,
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
        # correlation_id will be generated below
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

        # Increment Prometheus metrics
        increment_transaction_counter(status="pending")
        increment_transaction_by_type_counter(transaction_type=transaction_type.value)

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
            "max_composite_depth": str(max_composite_depth),
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


async def review_transaction(
    session: AsyncSession,
    transaction_id: str,
    new_status: str,
    comment: str | None = None,
) -> Dict[str, Any]:
    """
    Review a flagged or failed transaction and update its status.

    This function allows analysts to manually review transactions that were
    flagged or failed by the rule engine, and mark them as accepted or rejected.

    Business rules:
    - Only transactions with status FLAGGED or FAILED can be reviewed
    - New status must be either ACCEPTED or REJECTED
    - Updates reviewed_at timestamp and optional review_comment
    - Logs the review action for audit trail
    - Records metrics for monitoring

    Args:
        session: Async SQLAlchemy session for database operations
        transaction_id: UUID of the transaction to review
        new_status: New status (must be 'accepted' or 'rejected')
        comment: Optional analyst comment explaining the decision

    Returns:
        Dict containing updated transaction data

    Raises:
        HTTPException: If transaction not found, invalid status, or business rules violated
    """
    from datetime import datetime
    from uuid import UUID

    from fastapi import HTTPException, status
    from sqlalchemy import select

    from src.modules.reporting.metrics import (
        increment_transaction_review_counter,
        observe_transaction_review_duration,
    )
    from src.modules.rule_engine.enums import TransactionStatus
    from src.storage.models import Transaction

    logger.info(
        "Starting transaction review",
        event="review_start",
        transaction_id=transaction_id,
        new_status=new_status,
    )

    start_time = datetime.utcnow()

    try:
        # Parse transaction ID
        try:
            txn_uuid = UUID(transaction_id)
        except ValueError:
            logger.warning(
                "Invalid transaction ID format",
                event="review_error",
                transaction_id=transaction_id,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid transaction ID format: {transaction_id}",
            )

        # Fetch transaction from database
        result = await session.execute(
            select(Transaction).where(Transaction.id == txn_uuid)
        )
        transaction = result.scalar_one_or_none()

        if not transaction:
            logger.warning(
                "Transaction not found",
                event="review_error",
                transaction_id=transaction_id,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found",
            )

        # Validate current status (only FLAGGED or FAILED can be reviewed)
        if transaction.status not in [
            TransactionStatus.FLAGGED,
            TransactionStatus.FAILED,
        ]:
            logger.warning(
                "Transaction cannot be reviewed - invalid current status",
                event="review_error",
                transaction_id=transaction_id,
                current_status=transaction.status,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transaction with status '{transaction.status}' cannot be reviewed. "
                f"Only 'flagged' or 'failed' transactions can be reviewed.",
            )

        # Validate new status
        new_status_lower = new_status.lower()
        if new_status_lower not in ["accepted", "rejected"]:
            logger.warning(
                "Invalid new status for review",
                event="review_error",
                transaction_id=transaction_id,
                new_status=new_status,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid review status: '{new_status}'. Must be 'accepted' or 'rejected'.",
            )

        # Map to enum
        status_map = {
            "accepted": TransactionStatus.ACCEPTED,
            "rejected": TransactionStatus.REJECTED,
        }
        new_status_enum = status_map[new_status_lower]

        # Store old status for logging
        old_status = transaction.status

        # Update transaction
        transaction.status = new_status_enum
        transaction.reviewed_at = datetime.utcnow()
        transaction.review_comment = comment
        transaction.updated_at = datetime.utcnow()

        await session.commit()
        await session.refresh(transaction)

        # Calculate duration
        duration = (datetime.utcnow() - start_time).total_seconds()

        # Record metrics
        increment_transaction_review_counter(
            status=new_status_lower, success=True
        )
        observe_transaction_review_duration(duration)

        logger.info(
            "Transaction review completed successfully",
            event="review_complete",
            transaction_id=transaction_id,
            old_status=old_status,
            new_status=new_status_enum,
            reviewed_at=transaction.reviewed_at.isoformat(),
            has_comment=comment is not None,
        )

        return {
            "id": str(transaction.id),
            "status": transaction.status,
            "reviewed_at": transaction.reviewed_at,
            "review_comment": transaction.review_comment,
        }

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        increment_transaction_review_counter(
            status=new_status.lower(), success=False
        )
        raise

    except Exception as e:
        # Rollback on unexpected errors
        await session.rollback()

        increment_transaction_review_counter(
            status=new_status.lower(), success=False
        )

        logger.error(
            "Transaction review failed with unexpected error",
            event="review_error",
            transaction_id=transaction_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to review transaction: {str(e)}",
        )
