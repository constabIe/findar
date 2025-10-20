"""
Repository for queue task database operations.

Provides async database access for creating, updating, and querying
queue tasks with support for metrics calculation and idempotency checks.
"""

import traceback
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import DuplicateTaskError, TaskNotFoundError
from src.modules.queue.models import QueueTask

from .enums import ErrorType, TaskStatus
from .schemas import QueueMetrics, TaskCreate, TaskUpdate


class QueueRepository:
    """
    Repository for managing queue tasks in the database.

    Handles CRUD operations, idempotency checks, status updates,
    and metrics calculation for transaction processing tasks.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session for database operations
        """
        self.session = session

    async def create_task(
        self, task_data: TaskCreate, celery_task_id: Optional[str] = None
    ) -> QueueTask:
        """
        Create a new queue task with idempotency check.

        Args:
            task_data: Task creation data
            celery_task_id: Optional Celery task ID

        Returns:
            Created QueueTask instance

        Raises:
            DuplicateTaskError: If task with correlation_id already exists
        """
        # Check for existing task with same correlation_id (idempotency)
        existing = await self.get_by_correlation_id(task_data.correlation_id)
        if existing:
            logger.warning(
                f"Duplicate task detected: correlation_id={task_data.correlation_id}"
            )
            raise DuplicateTaskError(
                f"Task with correlation_id '{task_data.correlation_id}' already exists"
            )

        try:
            task = QueueTask(
                correlation_id=task_data.correlation_id,
                transaction_id=task_data.transaction_id,
                celery_task_id=celery_task_id,
                status=TaskStatus.PENDING,
                max_retries=task_data.max_retries,
                task_metadata=task_data.metadata,
            )

            self.session.add(task)
            await self.session.commit()
            await self.session.refresh(task)

            logger.info(
                f"Created queue task: id={task.id}, "
                f"correlation_id={task.correlation_id}"
            )

            return task

        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Database integrity error creating task: {e}")
            raise DuplicateTaskError(
                f"Task with correlation_id '{task_data.correlation_id}' already exists"
            )
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating queue task: {e}")
            raise

    async def get_by_id(self, task_id: UUID) -> Optional[QueueTask]:
        """
        Get task by ID.

        Args:
            task_id: Task UUID

        Returns:
            QueueTask if found, None otherwise
        """
        stmt = select(QueueTask).where(QueueTask.id == task_id)  # type: ignore
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_correlation_id(self, correlation_id: str) -> Optional[QueueTask]:
        """
        Get task by correlation ID (for idempotency check).

        Args:
            correlation_id: Transaction correlation ID

        Returns:
            QueueTask if found, None otherwise
        """
        stmt = select(QueueTask).where(QueueTask.correlation_id == correlation_id)  # type: ignore
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_celery_task_id(self, celery_task_id: str) -> Optional[QueueTask]:
        """
        Get task by Celery task ID.

        Args:
            celery_task_id: Celery task ID

        Returns:
            QueueTask if found, None otherwise
        """
        stmt = select(QueueTask).where(QueueTask.celery_task_id == celery_task_id)  # type: ignore
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_task(self, task_id: UUID, update_data: TaskUpdate) -> QueueTask:
        """
        Update task with new data.

        Args:
            task_id: Task UUID
            update_data: Update data

        Returns:
            Updated QueueTask

        Raises:
            TaskNotFoundError: If task not found
        """
        task = await self.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task with id {task_id} not found")

        # Update only provided fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(task, field, value)

        task.updated_at = datetime.utcnow()

        try:
            await self.session.commit()
            await self.session.refresh(task)

            logger.debug(f"Updated task {task_id}: {update_dict}")

            return task

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating task {task_id}: {e}")
            raise

    async def mark_started(
        self, task_id: UUID, worker_id: str, worker_hostname: str
    ) -> QueueTask:
        """
        Mark task as started (PROCESSING status).

        Args:
            task_id: Task UUID
            worker_id: Worker ID processing the task
            worker_hostname: Worker hostname

        Returns:
            Updated QueueTask
        """
        update_data = TaskUpdate(
            status=TaskStatus.PROCESSING,
            started_at=datetime.utcnow(),
            worker_id=worker_id,
            worker_hostname=worker_hostname,
        )
        return await self.update_task(task_id, update_data)

    async def mark_completed(
        self,
        task_id: UUID,
        processing_time_ms: int,
        rule_engine_time_ms: Optional[int] = None,
        db_write_time_ms: Optional[int] = None,
        notification_time_ms: Optional[int] = None,
    ) -> QueueTask:
        """
        Mark task as successfully completed.

        Args:
            task_id: Task UUID
            processing_time_ms: Total processing time
            rule_engine_time_ms: Rule engine processing time
            db_write_time_ms: Database write time
            notification_time_ms: Notification send time

        Returns:
            Updated QueueTask
        """
        update_data = TaskUpdate(
            status=TaskStatus.COMPLETED,
            completed_at=datetime.utcnow(),
            processing_time_ms=processing_time_ms,
            rule_engine_time_ms=rule_engine_time_ms,
            db_write_time_ms=db_write_time_ms,
            notification_time_ms=notification_time_ms,
        )
        return await self.update_task(task_id, update_data)

    async def mark_failed(
        self,
        task_id: UUID,
        error_type: ErrorType,
        error_message: str,
        error_traceback: Optional[str] = None,
        retry: bool = False,
    ) -> QueueTask:
        """
        Mark task as failed.

        Args:
            task_id: Task UUID
            error_type: Type of error
            error_message: Error message
            error_traceback: Full error traceback
            retry: Whether task will be retried

        Returns:
            Updated QueueTask
        """
        task = await self.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task with id {task_id} not found")

        new_status = TaskStatus.RETRY if retry else TaskStatus.FAILED

        update_data = TaskUpdate(
            status=new_status,
            error_type=error_type,
            error_message=error_message,
            error_traceback=error_traceback or traceback.format_exc(),
            completed_at=datetime.utcnow() if not retry else None,
            last_retry_at=datetime.utcnow() if retry else None,
        )

        # Increment retry count if retrying
        if retry:
            task.retry_count += 1

        return await self.update_task(task_id, update_data)

    async def get_tasks_by_status(
        self, status: TaskStatus, limit: int = 100
    ) -> List[QueueTask]:
        """
        Get tasks by status.

        Args:
            status: Task status to filter by
            limit: Maximum number of tasks to return

        Returns:
            List of QueueTask instances
        """
        stmt = (
            select(QueueTask)
            .where(QueueTask.status == status)  # type: ignore
            .order_by(QueueTask.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_metrics(self) -> QueueMetrics:
        """
        Calculate queue performance metrics.

        Returns:
            QueueMetrics with current statistics
        """
        # Count tasks by status
        status_counts_stmt = select(
            QueueTask.status, func.count(QueueTask.id).label("count")
        ).group_by(QueueTask.status)
        status_result = await self.session.execute(status_counts_stmt)
        status_counts = {row[0]: row[1] for row in status_result}

        # Calculate processing time statistics
        completed_stmt = select(QueueTask).where(
            QueueTask.status == TaskStatus.COMPLETED  # type: ignore
        )
        completed_result = await self.session.execute(completed_stmt)
        completed_tasks = list(completed_result.scalars().all())

        processing_times = [
            t.processing_time_ms
            for t in completed_tasks
            if t.processing_time_ms is not None
        ]

        rule_engine_times = [
            t.rule_engine_time_ms
            for t in completed_tasks
            if t.rule_engine_time_ms is not None
        ]

        # Calculate averages and percentiles
        avg_processing = (
            sum(processing_times) / len(processing_times) if processing_times else None
        )
        avg_rule_engine = (
            sum(rule_engine_times) / len(rule_engine_times)
            if rule_engine_times
            else None
        )

        p95_processing = None
        p99_processing = None
        if processing_times:
            sorted_times = sorted(processing_times)
            p95_idx = int(len(sorted_times) * 0.95)
            p99_idx = int(len(sorted_times) * 0.99)
            p95_processing = (
                sorted_times[p95_idx]
                if p95_idx < len(sorted_times)
                else sorted_times[-1]
            )
            p99_processing = (
                sorted_times[p99_idx]
                if p99_idx < len(sorted_times)
                else sorted_times[-1]
            )

        # Count total retries
        total_retries_stmt = select(func.sum(QueueTask.retry_count))
        retry_result = await self.session.execute(total_retries_stmt)
        total_retries = retry_result.scalar() or 0

        # Calculate error rate
        total = sum(status_counts.values())
        failed = status_counts.get(TaskStatus.FAILED, 0)
        error_rate = (failed / total) if total > 0 else 0.0

        return QueueMetrics(
            total_tasks=total,
            pending_tasks=status_counts.get(TaskStatus.PENDING, 0),
            processing_tasks=status_counts.get(TaskStatus.PROCESSING, 0),
            completed_tasks=status_counts.get(TaskStatus.COMPLETED, 0),
            failed_tasks=failed,
            retry_tasks=status_counts.get(TaskStatus.RETRY, 0),
            avg_processing_time_ms=avg_processing,
            avg_rule_engine_time_ms=avg_rule_engine,
            p95_processing_time_ms=p95_processing,
            p99_processing_time_ms=p99_processing,
            total_retries=int(total_retries),
            error_rate=error_rate,
        )
