"""
Celery tasks for asynchronous transaction processing.

Defines tasks for processing transactions through the fraud detection pipeline:
1. Receive transaction from queue
2. Evaluate with rule engine
3. Update transaction status
4. Send notifications
5. Track metrics and errors
"""

import asyncio
import json
import socket
import traceback
from time import time
from typing import Any, Dict, List
from uuid import UUID

from celery import Task
from celery.exceptions import MaxRetriesExceededError
from loguru import logger
from redis import Redis as SyncRedis
from sqlalchemy.ext.asyncio import AsyncSession


def get_or_create_event_loop():
    """
    Get existing event loop or create new one if needed.

    This prevents "Event loop is closed" errors in Celery workers.
    Safe to use in solo pool or gevent pool workers.

    Returns:
        Event loop instance
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        # No event loop in current thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop


def run_async(coro):
    """
    Run async coroutine safely in Celery task context.

    Uses existing event loop when possible, creates new one if needed.
    This is more reliable than asyncio.run() which always creates new loop.

    Args:
        coro: Coroutine to execute

    Returns:
        Result of coroutine execution
    """
    loop = get_or_create_event_loop()
    return loop.run_until_complete(coro)


from src.core.exceptions import DatabaseError, RuleEvaluationError
from src.modules.reporting.metrics import (
    increment_completed_counter,
    increment_error_counter,
    increment_failed_counter,
    increment_retry_counter,
    increment_submitted_counter,
    increment_task_counter,
    increment_transaction_counter,
    observe_db_write_time,
    observe_notification_time,
    observe_processing_time,
    observe_rule_engine_time,
    observe_transaction_processing_time,
)
from src.modules.rule_engine import service as rule_engine_service
from src.modules.rule_engine.enums import RiskLevel
from src.modules.rule_engine.enums import TransactionStatus as TxnStatus
from src.modules.transactions.repository import TransactionRepository
from src.storage.redis import get_async_redis_dependency
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
        logger.error(f"Task {task_id} failed: {exc}\n{einfo}")
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
        logger.warning(f"Task {task_id} retrying due to: {exc}")
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
    # Get worker info
    worker_id = self.request.id
    worker_hostname = socket.gethostname()

    # Extract transaction_id from data
    transaction_id = transaction_data.get("id")

    # Extract max_composite_depth (default to 5 if not provided)
    max_composite_depth = int(transaction_data.get("max_composite_depth", 5))

    logger.info(
        f"Processing transaction {transaction_id} "
        f"(correlation_id={correlation_id}, worker={worker_hostname})"
    )

    increment_submitted_counter()
    increment_task_counter(TaskStatus.PENDING.value)

    start_time = time()

    try:
        # Run async processing using safe event loop handler
        result = run_async(
            _process_transaction_async(
                transaction_data=transaction_data,
                correlation_id=correlation_id,
                queue_task_id=UUID(queue_task_id),
                worker_id=worker_id,
                worker_hostname=worker_hostname,
                max_composite_depth=max_composite_depth,
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
            run_async(
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
            increment_task_counter(TaskStatus.FAILED.value)
            raise self.retry(exc=exc, countdown=2**self.request.retries)
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
    max_composite_depth: int = 5,
) -> Dict[str, Any]:
    """
    Async implementation of transaction processing.

    Args:
        transaction_data: COMPLETE transaction data from Redis (no DB fetch!)
        correlation_id: Correlation ID
        queue_task_id: Queue task UUID
        worker_id: Celery worker ID
        worker_hostname: Worker hostname
        max_composite_depth: Maximum recursion depth for composite rules

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
        evaluation_result = await _evaluate_transaction(
            transaction_data, max_composite_depth=max_composite_depth
        )
        rule_engine_time_ms = int((time() - rule_engine_start) * 1000)
        observe_rule_engine_time((time() - rule_engine_start))

        # Update transaction status in DB (async write)
        db_write_start = time()
        await _update_transaction_status(session, transaction_id, evaluation_result)
        db_write_time_ms = int((time() - db_write_start) * 1000)
        observe_db_write_time((time() - db_write_start))

        # Save rule executions to Redis for later persistence
        await _save_rule_executions_to_redis(
            correlation_id=correlation_id,
            transaction_id=transaction_id,
            evaluation_result=evaluation_result,
        )

        print("WAS I HERE")

        # Trigger background task to save rule executions to PostgreSQL
        # This runs asynchronously and won't block transaction processing
        if evaluation_result.get("triggered_rules"):
            celery_app.send_task(
                "queue.save_rule_executions_to_db",
                args=[correlation_id],
                queue="rule_executions",
                countdown=5,  # Delay 5 seconds to ensure Redis write completes
            )
            logger.debug(
                f"Scheduled save_rule_executions_to_db task for {correlation_id}",
                correlation_id=correlation_id,
            )

        # Send notifications if suspicious
        notification_time_ms = 0
        if evaluation_result.get("is_suspicious", False):
            notification_start = time()
            await _send_notifications(
                transaction_data, evaluation_result, correlation_id
            )
            notification_time_ms = int((time() - notification_start) * 1000)
            observe_notification_time((time() - notification_start))

        # Mark task as completed
        total_time_ms = rule_engine_time_ms + db_write_time_ms + notification_time_ms

        # Record transaction processing time metric
        observe_transaction_processing_time(
            total_time_ms / 1000.0
        )  # Convert to seconds

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
    transaction: Dict[str, Any], max_composite_depth: int = 5
) -> Dict[str, Any]:
    """
    Evaluate transaction with rule engine.

    Args:
        transaction: Complete transaction data from Redis
        max_composite_depth: Maximum recursion depth for composite rules

    Returns:
        Evaluation results dictionary
    """
    transaction_id = transaction.get("id")
    correlation_id = transaction.get("correlation_id", "")

    logger.info(
        f"Starting rule engine evaluation for transaction {transaction_id}",
        event="rule_engine_evaluation_start",
        transaction_id=transaction_id,
        correlation_id=correlation_id,
        transaction_amount=transaction.get("amount"),
        transaction_amount_type=type(transaction.get("amount")).__name__,
    )

    try:
        # Get Redis client for fetching active rules
        redis_gen = get_async_redis_dependency()
        redis_client = await anext(redis_gen)

        # Get active rules from cache
        active_rules = await rule_engine_service.get_cached_active_rules(redis_client)

        logger.info(
            f"Retrieved {len(active_rules) if active_rules else 0} active rules from cache",
            event="active_rules_retrieved",
            transaction_id=transaction_id,
            rules_count=len(active_rules) if active_rules else 0,
        )

        if not active_rules:
            logger.warning(
                "No active rules found in cache, loading from database",
                event="no_cached_rules",
                transaction_id=transaction_id,
            )
            # TODO: Load rules from database if cache is empty
            # For now, return approved status
            return {
                "is_suspicious": False,
                "risk_score": 0,
                "risk_level": RiskLevel.LOW.value,
                "final_status": TxnStatus.APPROVED.value,
                "triggered_rules": [],
                "total_rules_evaluated": 0,
                "evaluation_details": {
                    "message": "No active rules in cache",
                },
            }

        # Evaluate transaction against all active rules
        evaluation_result = await rule_engine_service.evaluate_transaction(
            transaction_data=transaction,
            rules=active_rules,
            correlation_id=correlation_id,
            redis_client=redis_client,
            max_composite_depth=max_composite_depth,
        )

        # Store transaction data for pattern analysis (async, non-blocking)
        # This allows pattern rules to analyze historical transaction patterns
        try:
            from src.modules.rule_engine.enums import TimeWindow
            from src.storage.redis.pattern import store_transaction_for_pattern

            # Store for multiple time windows to support different pattern rules
            time_windows = [
                TimeWindow.THIRTY_MINUTES,
                TimeWindow.HOUR,
                TimeWindow.SIX_HOURS,
                TimeWindow.TWELVE_HOURS,
                TimeWindow.DAY,
            ]

            from_account = transaction.get("from_account", "")

            for window in time_windows:
                await store_transaction_for_pattern(
                    redis=redis_client,
                    account_id=from_account,
                    transaction_data=transaction,
                    time_window=window,
                )

            logger.debug(
                "Stored transaction for pattern analysis",
                transaction_id=transaction_id,
                from_account=from_account,
                windows=[w.value for w in time_windows],
            )

        except Exception as pattern_error:
            # Don't fail transaction processing if pattern storage fails
            logger.warning(
                "Failed to store transaction for pattern analysis",
                transaction_id=transaction_id,
                error=str(pattern_error),
                event="pattern_storage_failed",
            )

        # Convert to dict format expected by caller
        is_flagged = evaluation_result.final_status == TxnStatus.FLAGGED
        is_failed = evaluation_result.final_status == TxnStatus.FAILED

        result_dict = {
            "is_suspicious": is_flagged or is_failed,
            "risk_score": _risk_level_to_score(evaluation_result.risk_level),
            "risk_level": evaluation_result.risk_level.value,
            "final_status": evaluation_result.final_status.value,
            "triggered_rules": [r.to_dict() for r in evaluation_result.matched_rules],
            "total_rules_evaluated": evaluation_result.total_rules_evaluated,
            "total_execution_time_ms": evaluation_result.total_execution_time_ms,
            "has_critical_match": evaluation_result.has_critical_match,
            "evaluation_details": evaluation_result.to_dict(),
        }

        logger.info(
            f"Rule engine evaluation completed for transaction {transaction_id}",
            event="rule_engine_evaluation_complete",
            transaction_id=transaction_id,
            is_suspicious=result_dict["is_suspicious"],
            risk_level=result_dict["risk_level"],
            final_status=result_dict["final_status"],
            matched_rules_count=len(evaluation_result.matched_rules),
            triggered_rules=[r["rule_name"] for r in result_dict["triggered_rules"]],
        )

        return result_dict

    except Exception as e:
        logger.error(
            f"Rule engine evaluation failed for transaction {transaction_id}: {e}",
            event="rule_engine_evaluation_error",
            transaction_id=transaction_id,
            error=str(e),
            traceback=traceback.format_exc(),
        )

        # Return safe defaults on error
        return {
            "is_suspicious": False,
            "risk_score": 0,
            "risk_level": RiskLevel.LOW.value,
            "final_status": TxnStatus.FAILED.value,  # Mark as failed due to evaluation error
            "triggered_rules": [],
            "total_rules_evaluated": 0,
            "evaluation_details": {
                "error": str(e),
                "message": "Rule engine evaluation failed",
            },
        }


def _risk_level_to_score(risk_level: RiskLevel) -> float:
    """Convert risk level enum to numeric score 0-100."""
    risk_scores = {
        RiskLevel.LOW: 25.0,
        RiskLevel.MEDIUM: 50.0,
        RiskLevel.HIGH: 75.0,
        RiskLevel.CRITICAL: 100.0,
    }
    return risk_scores.get(risk_level, 0.0)


async def _update_transaction_status(
    session: AsyncSession, transaction_id: UUID, evaluation_result: Dict[str, Any]
) -> None:
    """
    Update transaction status in database based on rule engine evaluation.

    Args:
        session: Database session
        transaction_id: Transaction UUID
        evaluation_result: Evaluation results from rule engine
    """
    try:
        transaction_repo = TransactionRepository(session)

        # Get final status from evaluation
        final_status_str = evaluation_result.get(
            "final_status", TxnStatus.APPROVED.value
        )
        final_status = TxnStatus(final_status_str)

        # Update transaction status
        await transaction_repo.update_status(
            transaction_id=transaction_id,
            status=final_status,
        )

        # This increments the counter for the final status
        increment_transaction_counter(status=final_status.value)

        logger.info(
            f"Updated transaction {transaction_id} status to {final_status.value}",
            event="transaction_status_updated",
            transaction_id=str(transaction_id),
            status=final_status.value,
            is_suspicious=evaluation_result.get("is_suspicious"),
            risk_level=evaluation_result.get("risk_level"),
        )

    except Exception as e:
        logger.error(
            f"Failed to update transaction {transaction_id} status: {e}",
            event="transaction_status_update_error",
            transaction_id=str(transaction_id),
            error=str(e),
        )
        raise DatabaseError(
            f"Failed to update transaction status: {e}",
            operation="update_transaction_status",
        )


async def _send_notifications(
    transaction: Dict[str, Any], evaluation_result: Dict[str, Any], correlation_id: str
) -> None:
    """
    Send notifications for suspicious/flagged transactions.

    Args:
        transaction: Transaction data from Redis
        evaluation_result: Evaluation results from rule engine
        correlation_id: Correlation ID for tracking
    """
    try:
        transaction_id = transaction.get("id")
        triggered_rules = evaluation_result.get("triggered_rules", [])
        risk_level = evaluation_result.get("risk_level", "low")

        if not triggered_rules:
            logger.debug(
                f"No notifications needed for transaction {transaction_id} - no rules matched"
            )
            return

        logger.info(
            f"Sending fraud alert for suspicious transaction {transaction_id}",
            event="sending_fraud_alert",
            transaction_id=transaction_id,
            risk_level=risk_level,
            matched_rules_count=len(triggered_rules),
        )

        # Call notifications module
        try:
            from src.modules.notifications.service import NotificationService
            from src.storage.dependencies import get_db_session
            from src.storage.sql import get_async_session_maker


            # Get database session for notifications
            session_maker = get_async_session_maker()
            async with session_maker() as db_session:
                notification_service = NotificationService(db_session)
                delivery_ids = await notification_service.send_fraud_alert(
                    transaction, evaluation_result, correlation_id
                )

                logger.info(
                    f"Created {len(delivery_ids)} notification deliveries",
                    event="notifications_created",
                    delivery_count=len(delivery_ids),
                    correlation_id=correlation_id,
                )
        except ImportError:
            logger.warning("Notifications module not available, using fallback")
            # Fallback to console output
            _print_fraud_alert(
                transaction_id or "unknown", triggered_rules, risk_level or "low"
            )
        except Exception as e:
            logger.error(
                f"Notification service error: {e}",
                event="notification_service_error",
                correlation_id=correlation_id,
            )
            # Fallback to console output
            _print_fraud_alert(
                transaction_id or "unknown", triggered_rules, risk_level or "low"
            )

    except Exception as e:
        logger.error(
            f"Failed to send notification for transaction {transaction.get('id')}: {e}",
            event="notification_error",
            error=str(e),
        )
        # Don't raise - notification failure shouldn't fail the whole task


def _print_fraud_alert(
    transaction_id: str, matched_rules: List[Dict[str, Any]], risk_level: str
) -> None:
    """
    Print fraud alert to console (temporary stub for notifications module).

    Args:
        transaction_id: Transaction UUID
        matched_rules: List of matched rule dictionaries
        risk_level: Risk level string
    """
    print("\n" + "=" * 80)
    print("🚨 FRAUD ALERT 🚨")
    print("=" * 80)
    print(f"Transaction ID: {transaction_id}")
    print(f"Risk Level: {risk_level.upper()}")
    print(f"Matched Rules: {len(matched_rules)}")
    print("-" * 80)
    for rule in matched_rules:
        print(f"  • {rule.get('rule_name', 'Unknown Rule')}")
        print(f"    Type: {rule.get('rule_type', 'unknown')}")
        print(f"    Reason: {rule.get('match_reason', 'N/A')}")
        print(f"    Confidence: {rule.get('confidence_score', 0):.2f}")
    print("=" * 80 + "\n")


async def _save_rule_executions_to_redis(
    correlation_id: str,
    transaction_id: UUID,
    evaluation_result: Dict[str, Any],
) -> None:
    """
    Save rule execution results to Redis for later persistence to PostgreSQL.

    This allows fast async storage, with a separate Celery worker
    handling the actual database writes.

    Args:
        correlation_id: Transaction correlation ID
        transaction_id: Transaction UUID
        evaluation_result: Complete evaluation results
    """
    try:
        redis_gen = get_async_redis_dependency()
        redis_client = await anext(redis_gen)

        # Prepare rule execution data
        triggered_rules = evaluation_result.get("triggered_rules", [])

        if not triggered_rules:
            logger.debug(
                f"No rule executions to save for transaction {transaction_id}",
                transaction_id=str(transaction_id),
                correlation_id=correlation_id,
            )
            return

        # Store each rule execution in Redis
        redis_key = f"rule_executions:{correlation_id}"
        execution_data = {
            "transaction_id": str(transaction_id),
            "correlation_id": correlation_id,
            "triggered_rules": triggered_rules,
            "total_rules_evaluated": evaluation_result.get("total_rules_evaluated", 0),
            "saved_at": time(),
        }

        # Store with 1 hour TTL
        await redis_client.setex(
            redis_key,
            3600,  # 1 hour
            json.dumps(execution_data),
        )

        logger.info(
            f"Saved {len(triggered_rules)} rule executions to Redis",
            event="rule_executions_saved_to_redis",
            transaction_id=str(transaction_id),
            correlation_id=correlation_id,
            redis_key=redis_key,
            matched_rules_count=len(triggered_rules),
        )

        # TODO: Trigger Celery task to persist to PostgreSQL
        # celery_app.send_task(
        #     "queue.save_rule_executions_to_db",
        #     args=[correlation_id],
        #     queue="rule_executions",
        # )

    except Exception as e:
        logger.error(
            f"Failed to save rule executions to Redis: {e}",
            event="rule_executions_save_error",
            transaction_id=str(transaction_id),
            correlation_id=correlation_id,
            error=str(e),
        )
        # Don't raise - this is not critical for transaction processing


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


@celery_app.task(
    bind=True,
    name="queue.save_rule_executions_to_db",
    queue="rule_executions",
    max_retries=3,
)
def save_rule_executions_to_db(
    self,
    correlation_id: str,
) -> Dict[str, Any]:
    """
    Save rule execution results from Redis to PostgreSQL (SYNC VERSION).

    This task runs asynchronously after transaction processing to persist
    rule evaluation results for analytics and compliance.

    Uses synchronous Redis and SQLAlchemy to avoid event loop conflicts.

    Args:
        correlation_id: Transaction correlation ID used as Redis key

    Returns:
        Dict with save statistics

    Raises:
        Retry: If save fails and retries available
    """
    logger.info(
        f"Starting rule executions persistence for correlation_id={correlation_id}",
        event="save_rule_executions_start",
        correlation_id=correlation_id,
    )

    try:
        # Use synchronous implementation
        result = _save_rule_executions_to_db_sync(correlation_id)

        logger.info(
            f"Rule executions saved successfully: {result['saved_count']} records",
            event="save_rule_executions_complete",
            correlation_id=correlation_id,
            saved_count=result["saved_count"],
        )

        return result

    except Exception as exc:
        logger.error(
            f"Failed to save rule executions: {exc}",
            event="save_rule_executions_error",
            correlation_id=correlation_id,
            error=str(exc),
        )

        # Retry if possible
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))
        else:
            raise


def _save_rule_executions_to_db_sync(
    correlation_id: str,
) -> Dict[str, Any]:
    """
    Synchronous implementation of saving rule executions from Redis to PostgreSQL.

    Args:
        correlation_id: Transaction correlation ID

    Returns:
        Dict with save results
    """
    from src.config import settings
    from src.storage.models import RuleExecution

    # Get sync Redis client
    redis_client = SyncRedis(
        host=settings.redis.REDIS_HOST,
        port=settings.redis.REDIS_PORT,
        db=settings.redis.REDIS_DB,
        password=settings.redis.REDIS_PASSWORD
        if settings.redis.REDIS_PASSWORD
        else None,
        decode_responses=True,
    )

    # Read execution data from Redis
    redis_key = f"rule_executions:{correlation_id}"

    try:
        cached_data = redis_client.get(redis_key)

        if not cached_data:
            logger.warning(
                f"No rule execution data found in Redis for {correlation_id}",
                event="no_redis_data",
                correlation_id=correlation_id,
                redis_key=redis_key,
            )
            redis_client.close()
            return {
                "saved_count": 0,
                "status": "no_data",
                "correlation_id": correlation_id,
            }

        execution_data = json.loads(cached_data)
        transaction_id = UUID(execution_data["transaction_id"])
        triggered_rules = execution_data.get("triggered_rules", [])

        if not triggered_rules:
            logger.debug(f"No triggered rules to save for {correlation_id}")
            # Delete from Redis since there's nothing to save
            redis_client.delete(redis_key)
            redis_client.close()
            return {
                "saved_count": 0,
                "status": "no_rules",
                "correlation_id": correlation_id,
            }

        # Get sync database session
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        # Build sync database URL
        db_url = (
            f"postgresql://{settings.database.POSTGRES_USER}:"
            f"{settings.database.POSTGRES_PASSWORD}@"
            f"{settings.database.POSTGRES_HOST}:"
            f"{settings.database.POSTGRES_PORT}/"
            f"{settings.database.POSTGRES_DB}"
        )

        # Create sync engine and session
        sync_engine = create_engine(db_url, pool_pre_ping=True)
        SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)

        # Save to PostgreSQL
        with SyncSessionLocal() as session:
            saved_count = 0

            for rule_result in triggered_rules:
                try:
                    rule_execution = RuleExecution(
                        rule_id=UUID(rule_result["rule_id"]),
                        transaction_id=transaction_id,
                        correlation_id=correlation_id,
                        matched=rule_result.get("matched", False),
                        confidence_score=rule_result.get("confidence_score", 0.0),
                        execution_time_ms=rule_result.get("execution_time_ms", 0.0),
                        context={
                            "rule_name": rule_result.get("rule_name"),
                            "rule_type": rule_result.get("rule_type"),
                            "match_reason": rule_result.get("match_reason"),
                            "risk_level": rule_result.get("risk_level"),
                        },
                        error_message=rule_result.get("error_message"),
                    )

                    session.add(rule_execution)
                    saved_count += 1

                except Exception as e:
                    logger.error(
                        f"Error creating RuleExecution for rule {rule_result.get('rule_id')}: {e}",
                        correlation_id=correlation_id,
                    )
                    continue

            # Commit all executions
            session.commit()

            logger.info(
                f"Saved {saved_count} rule executions to database",
                event="rule_executions_persisted",
                correlation_id=correlation_id,
                saved_count=saved_count,
            )

        # Delete from Redis after successful save
        redis_client.delete(redis_key)
        redis_client.close()

        logger.debug(
            f"Deleted rule executions from Redis: {redis_key}",
            redis_key=redis_key,
        )

        # Dispose engine after use
        sync_engine.dispose()

        return {
            "saved_count": saved_count,
            "status": "success",
            "correlation_id": correlation_id,
        }

    except Exception as e:
        logger.error(
            f"Error in _save_rule_executions_to_db_sync: {e}",
            event="save_error",
            correlation_id=correlation_id,
            error=str(e),
            traceback=traceback.format_exc(),
        )
        redis_client.close()
        raise
