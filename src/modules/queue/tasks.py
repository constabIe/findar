"""
Celery tasks for asynchronous transaction processing.

Defines tasks for processing transactions through the fraud detection pipeline:
1. Receive transaction from queue
2. Evaluate with rule engine
3. Update transaction status
4. Send notifications
5. Track metrics and errors
"""

import socket
import traceback
from time import time
from typing import Any, Dict
from uuid import UUID

from celery import Task
from celery.exceptions import MaxRetriesExceededError
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import DatabaseError, RuleEvaluationError
from src.modules.reporting.metrics import (
    increment_completed_counter,
    increment_error_counter,
    increment_failed_counter,
    increment_retry_counter,
    increment_submitted_counter,
    increment_task_counter,
    observe_db_write_time,
    observe_notification_time,
    observe_processing_time,
    observe_rule_engine_time,
)
from src.storage.sql.engine import get_async_session_maker

from .celery_config import celery_app
from .enums import ErrorType, TaskStatus
from .repository import QueueRepository

# Get async session maker from storage module
AsyncSessionLocal = get_async_session_maker()


class TransactionProcessingTask(Task):
    """
    Base task class with custom error handling and retry logic.
    """

    autoretry_for = (DatabaseError, RuleEvaluationError, Exception)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True  # Exponential backoff
    retry_backoff_max = 600  # Max 10 minutes
    retry_jitter = True  # Add randomness to avoid thundering herd

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Handle task failure.
        
        Args:
            exc: Exception that caused failure
            task_id: Unique task ID
            args: Task args
            kwargs: Task kwargs
            einfo: Exception info
        """
        logger.error(
            f"Task {task_id} failed: {exc}\n{einfo}"
        )
        increment_error_counter(error_type=type(exc).__name__)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """
        Handle task retry.
        
        Args:
            exc: Exception that caused retry
            task_id: Unique task ID
            args: Task args
            kwargs: Task kwargs
            einfo: Exception info
        """
        logger.warning(
            f"Task {task_id} retrying due to: {exc}"
        )
        increment_retry_counter()

    def on_success(self, retval, task_id, args, kwargs):
        """
        Handle task success.
        
        Args:
            retval: Return value
            task_id: Unique task ID
            args: Task args
            kwargs: Task kwargs
        """
        logger.debug(f"Task {task_id} completed successfully")
        increment_completed_counter()


@celery_app.task(
    bind=True,
    base=TransactionProcessingTask,
    name="queue.process_transaction",
    queue="transactions",
)
def process_transaction(
    self,
    transaction_data: Dict[str, Any],
    correlation_id: str,
    queue_task_id: str,
) -> Dict[str, Any]:
    """
    Process a transaction through the fraud detection pipeline.
    
    This task:
    1. Marks task as processing
    2. Receives FULL transaction data from Redis (no DB fetch needed!)
    3. Evaluates transaction with rule engine
    4. Updates transaction status based on evaluation
    5. Sends notifications if suspicious
    6. Records metrics
    
    Args:
        transaction_data: COMPLETE transaction data from Redis queue
        correlation_id: Correlation ID for tracking
        queue_task_id: Queue task ID for status updates
        
    Returns:
        Dict with processing results
        
    Raises:
        Retry: If processing fails and retries available
        MaxRetriesExceededError: If all retries exhausted
    """
    import asyncio

    # Get worker info
    worker_id = self.request.id
    worker_hostname = socket.gethostname()

    # Extract transaction_id from data
    transaction_id = transaction_data.get("id")

    logger.info(
        f"Processing transaction {transaction_id} "
        f"(correlation_id={correlation_id}, worker={worker_hostname})"
    )

    increment_submitted_counter()
    increment_task_counter(TaskStatus.PROCESSING.value)

    start_time = time()

    try:
        # Run async processing in event loop
        result = asyncio.run(
            _process_transaction_async(
                transaction_data=transaction_data,
                correlation_id=correlation_id,
                queue_task_id=UUID(queue_task_id),
                worker_id=worker_id,
                worker_hostname=worker_hostname,
            )
        )

        # Record metrics
        processing_time_ms = int((time() - start_time) * 1000)
        observe_processing_time((time() - start_time))

        increment_task_counter(TaskStatus.COMPLETED.value)

        logger.info(
            f"Transaction {transaction_id} processed successfully "
            f"in {processing_time_ms}ms"
        )

        return result

    except Exception as exc:
        processing_time_ms = int((time() - start_time) * 1000)

        # Determine error type
        error_type = _map_exception_to_error_type(exc)

        logger.error(
            f"Error processing transaction {transaction_id}: {exc}\n"
            f"{traceback.format_exc()}"
        )

        # Try to mark task as failed in database
        try:
            asyncio.run(
                _mark_task_failed(
                    queue_task_id=UUID(queue_task_id),
                    error_type=error_type,
                    error_message=str(exc),
                    retry=self.request.retries < self.max_retries,
                )
            )
        except Exception as db_exc:
            logger.error(f"Failed to update task status: {db_exc}")

        # Increment error metrics
        increment_failed_counter(error_type=error_type.value)
        increment_task_counter(TaskStatus.FAILED.value)

        # Retry if possible
        if self.request.retries < self.max_retries:
            increment_task_counter(TaskStatus.RETRY.value)
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        else:
            raise MaxRetriesExceededError(
                f"Task failed after {self.max_retries} retries: {exc}"
            )


async def _process_transaction_async(
    transaction_data: Dict[str, Any],
    correlation_id: str,
    queue_task_id: UUID,
    worker_id: str,
    worker_hostname: str,
) -> Dict[str, Any]:
    """
    Async implementation of transaction processing.
    
    Args:
        transaction_data: COMPLETE transaction data from Redis (no DB fetch!)
        correlation_id: Correlation ID
        queue_task_id: Queue task UUID
        worker_id: Celery worker ID
        worker_hostname: Worker hostname
        
    Returns:
        Processing results dictionary
    """
    async with AsyncSessionLocal() as session:
        repo = QueueRepository(session)

        # Mark task as processing
        await repo.mark_started(
            task_id=queue_task_id,
            worker_id=worker_id,
            worker_hostname=worker_hostname,
        )

        # ✅ Transaction data already received from Redis - no DB fetch needed!
        transaction_id = UUID(transaction_data["id"])

        # Evaluate with rule engine
        rule_engine_start = time()
        evaluation_result = await _evaluate_transaction(transaction_data)
        rule_engine_time_ms = int((time() - rule_engine_start) * 1000)
        observe_rule_engine_time((time() - rule_engine_start))

        # Update transaction status in DB (async write)
        db_write_start = time()
        await _update_transaction_status(
            session,
            transaction_id,
            evaluation_result
        )
        db_write_time_ms = int((time() - db_write_start) * 1000)
        observe_db_write_time((time() - db_write_start))

        # Send notifications if suspicious
        notification_time_ms = 0
        if evaluation_result.get("is_suspicious", False):
            notification_start = time()
            await _send_notifications(transaction_data, evaluation_result)
            notification_time_ms = int((time() - notification_start) * 1000)
            observe_notification_time((time() - notification_start))

        # Mark task as completed
        total_time_ms = rule_engine_time_ms + db_write_time_ms + notification_time_ms
        await repo.mark_completed(
            task_id=queue_task_id,
            processing_time_ms=total_time_ms,
            rule_engine_time_ms=rule_engine_time_ms,
            db_write_time_ms=db_write_time_ms,
            notification_time_ms=notification_time_ms,
        )

        return {
            "transaction_id": str(transaction_id),
            "correlation_id": correlation_id,
            "is_suspicious": evaluation_result.get("is_suspicious", False),
            "risk_score": evaluation_result.get("risk_score", 0),
            "triggered_rules": evaluation_result.get("triggered_rules", []),
            "processing_time_ms": total_time_ms,
        }


async def _evaluate_transaction(
    transaction: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluate transaction with rule engine.
    
    TODO: Implement integration with rule_engine module.
    For now, returns mock evaluation.
    
    Args:
        transaction: Complete transaction data from Redis
        
    Returns:
        Evaluation results
    """
    # STUB: This will call actual rule engine
    logger.debug(f"Evaluating transaction {transaction.get('id')}")

    # Mock evaluation logic
    amount = transaction.get("amount", 0)
    is_suspicious = amount > 5000  # Simple threshold rule

    return {
        "is_suspicious": is_suspicious,
        "risk_score": min(amount / 100, 100),  # Score 0-100
        "triggered_rules": ["high_amount_rule"] if is_suspicious else [],
        "evaluation_details": {
            "amount_threshold_exceeded": is_suspicious,
        },
    }


async def _update_transaction_status(
    session: AsyncSession,
    transaction_id: UUID,
    evaluation_result: Dict[str, Any]
) -> None:
    """
    Update transaction status in database (async write).
    
    TODO: Implement when transaction module is ready.
    
    Args:
        session: Database session
        transaction_id: Transaction UUID
        evaluation_result: Evaluation results
    """
    # STUB: This will update actual transaction record in DB
    logger.debug(
        f"Updating transaction {transaction_id} status: "
        f"suspicious={evaluation_result.get('is_suspicious')}"
    )
    # Will set status to EVALUATED, SUSPICIOUS, or CLEARED
    pass


async def _send_notifications(
    transaction: Dict[str, Any],
    evaluation_result: Dict[str, Any]
) -> None:
    """
    Send notifications for suspicious transactions.
    
    TODO: Implement integration with notifications module.
    
    Args:
        transaction: Transaction data from Redis
        evaluation_result: Evaluation results
    """
    # STUB: This will send actual notifications
    logger.info(
        f"Sending notification for suspicious transaction "
        f"{transaction.get('id')}"
    )
    # Will call notifications module to send alerts
    pass


async def _mark_task_failed(
    queue_task_id: UUID,
    error_type: ErrorType,
    error_message: str,
    retry: bool = False,
) -> None:
    """
    Mark task as failed in database.
    
    Args:
        queue_task_id: Queue task UUID
        error_type: Type of error
        error_message: Error message
        retry: Whether task will be retried
    """
    async with AsyncSessionLocal() as session:
        repo = QueueRepository(session)
        await repo.mark_failed(
            task_id=queue_task_id,
            error_type=error_type,
            error_message=error_message,
            error_traceback=traceback.format_exc(),
            retry=retry,
        )


def _map_exception_to_error_type(exc: Exception) -> ErrorType:
    """
    Map Python exception to ErrorType enum.
    
    Args:
        exc: Exception instance
        
    Returns:
        Corresponding ErrorType
    """
    exc_name = type(exc).__name__

    mapping = {
        "ValidationError": ErrorType.VALIDATION_ERROR,
        "DatabaseError": ErrorType.DATABASE_ERROR,
        "RuleEvaluationError": ErrorType.RULE_ENGINE_ERROR,
        "NotificationError": ErrorType.NOTIFICATION_ERROR,
        "TimeoutError": ErrorType.TIMEOUT_ERROR,
    }

    return mapping.get(exc_name, ErrorType.UNKNOWN_ERROR)


@celery_app.task(name="queue.cleanup_old_tasks")
def cleanup_old_tasks() -> Dict[str, Any]:
    """
    Periodic task to clean up old completed tasks.
    
    Runs daily to remove tasks older than 30 days to prevent
    database bloat while keeping recent history for debugging.
    
    Returns:
        Dict with cleanup statistics
    """

    logger.info("Starting cleanup of old queue tasks")

    # TODO: Implement cleanup logic
    # Delete completed tasks older than 30 days
    # Keep failed tasks for longer (90 days) for analysis

    logger.info("Cleanup completed")

    return {
        "deleted_count": 0,
        "status": "success",
    }
