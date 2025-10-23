"""
Repository for reporting module database operations.

Provides async database access for aggregating statistics about transactions
and rule executions for reporting purposes.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.modules.rule_engine.enums import RuleType, TransactionStatus, TransactionType
from src.storage.models import Rule, RuleExecution, Transaction

logger = get_logger("reporting.repository")


class ReportingRepository:
    """
    Repository for generating reports and statistics.

    Handles complex aggregations and queries for transaction statistics,
    rule performance metrics, and data export functionality.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session for database operations
        """
        self.session = session

    async def get_transaction_statistics(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        status: Optional[TransactionStatus] = None,
        transaction_type: Optional[TransactionType] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregated transaction statistics.

        Args:
            date_from: Start date filter
            date_to: End date filter
            status: Filter by transaction status
            transaction_type: Filter by transaction type

        Returns:
            Dictionary containing aggregated statistics:
            - total_count: Total number of transactions
            - by_status: Dict of counts grouped by status
            - by_type: Dict of counts grouped by type
        """
        logger.info(
            "Fetching transaction statistics",
            event="get_transaction_statistics_start",
            date_from=date_from,
            date_to=date_to,
            status=status,
            transaction_type=transaction_type,
        )

        # Build base query filters
        filters = []
        if date_from:
            filters.append(Transaction.timestamp >= date_from)
        if date_to:
            filters.append(Transaction.timestamp <= date_to)
        if status:
            filters.append(Transaction.status == status)
        if transaction_type:
            filters.append(Transaction.type == transaction_type)

        # Get total count
        count_query = select(func.count(Transaction.id))  # type: ignore
        if filters:
            count_query = count_query.where(and_(*filters))

        result = await self.session.execute(count_query)
        total_count = result.scalar() or 0

        # Get counts by status
        status_query = select(
            Transaction.status,
            func.count(Transaction.id).label("count"),  # type: ignore
        ).group_by(Transaction.status)  # type: ignore
        if filters:
            status_query = status_query.where(and_(*filters))

        result = await self.session.execute(status_query)
        by_status = {str(row.status.value): row.count for row in result}

        # Get counts by type
        type_query = select(
            Transaction.type,
            func.count(Transaction.id).label("count"),  # type: ignore
        ).group_by(Transaction.type)  # type: ignore
        if filters:
            type_query = type_query.where(and_(*filters))

        result = await self.session.execute(type_query)
        by_type = {str(row.type.value): row.count for row in result}

        logger.info(
            "Transaction statistics retrieved",
            event="get_transaction_statistics_complete",
            total_count=total_count,
        )

        return {
            "total_count": total_count,
            "by_status": by_status,
            "by_type": by_type,
        }

    async def get_processing_metrics(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Dict[str, float]:
        """
        Calculate processing time metrics from queue tasks.

        Args:
            date_from: Start date filter
            date_to: End date filter

        Returns:
            Dictionary with processing time statistics:
            - average_time: Average processing time in seconds
            - median_time: Median (p50) processing time
            - p95_time: 95th percentile
            - p99_time: 99th percentile
            - min_time: Minimum time
            - max_time: Maximum time
        """
        logger.info(
            "Calculating processing metrics",
            event="get_processing_metrics_start",
            date_from=date_from,
            date_to=date_to,
        )

        # Import QueueTask here to avoid circular imports
        from src.modules.queue.models import QueueTask

        # Build query filters
        filters = [QueueTask.processing_time_ms.isnot(None)]  # type: ignore
        if date_from:
            filters.append(QueueTask.created_at >= date_from)  # type: ignore
        if date_to:
            filters.append(QueueTask.created_at <= date_to)  # type: ignore

        # Get aggregate metrics (convert ms to seconds)
        query = select(
            (func.avg(QueueTask.processing_time_ms) / 1000.0).label("avg_time"),  # type: ignore
            (func.min(QueueTask.processing_time_ms) / 1000.0).label("min_time"),  # type: ignore
            (func.max(QueueTask.processing_time_ms) / 1000.0).label("max_time"),  # type: ignore
            (
                func.percentile_cont(0.5).within_group(QueueTask.processing_time_ms)
                / 1000.0
            )  # type: ignore
            .label("median_time"),
            (
                func.percentile_cont(0.95).within_group(QueueTask.processing_time_ms)
                / 1000.0
            )  # type: ignore
            .label("p95_time"),
            (
                func.percentile_cont(0.99).within_group(QueueTask.processing_time_ms)
                / 1000.0
            )  # type: ignore
            .label("p99_time"),
        ).where(and_(*filters))

        result = await self.session.execute(query)
        row = result.one_or_none()

        if not row:
            logger.warning("No processing metrics found")
            return {
                "average_time": 0.0,
                "median_time": 0.0,
                "p95_time": 0.0,
                "p99_time": 0.0,
                "min_time": 0.0,
                "max_time": 0.0,
            }

        metrics = {
            "average_time": float(row.avg_time or 0.0),
            "median_time": float(row.median_time or 0.0),
            "p95_time": float(row.p95_time or 0.0),
            "p99_time": float(row.p99_time or 0.0),
            "min_time": float(row.min_time or 0.0),
            "max_time": float(row.max_time or 0.0),
        }

        logger.info(
            "Processing metrics calculated",
            event="get_processing_metrics_complete",
            average_time=metrics["average_time"],
        )

        return metrics

    async def get_rule_statistics(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        rule_type: Optional[RuleType] = None,
        rule_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregated rule execution statistics.

        Args:
            date_from: Start date filter
            date_to: End date filter
            rule_type: Filter by rule type
            rule_id: Filter by specific rule ID

        Returns:
            Dictionary containing rule statistics:
            - total_evaluations: Total number of evaluations
            - total_matches: Total number of matches
            - by_rule_type: Statistics grouped by rule type
            - top_rules: List of top performing rules
        """
        logger.info(
            "Fetching rule statistics",
            event="get_rule_statistics_start",
            date_from=date_from,
            date_to=date_to,
            rule_type=rule_type,
            rule_id=rule_id,
        )

        # Build filters
        filters = []
        if date_from:
            filters.append(RuleExecution.executed_at >= date_from)
        if date_to:
            filters.append(RuleExecution.executed_at <= date_to)
        if rule_id:
            filters.append(RuleExecution.rule_id == rule_id)

        # Get total counts
        total_query = select(
            func.count(RuleExecution.id).label("total"),  # type: ignore
            func.count(RuleExecution.id)
            .filter(RuleExecution.matched == True)
            .label("matched"),  # type: ignore
        )
        if filters:
            total_query = total_query.where(and_(*filters))

        result = await self.session.execute(total_query)
        totals = result.one()
        total_evaluations = totals.total or 0
        total_matches = totals.matched or 0

        # Get statistics by rule type (join with Rule table)
        type_query = (
            select(
                Rule.type,
                func.count(RuleExecution.id).label("evaluations"),
                func.count(RuleExecution.id)
                .filter(RuleExecution.matched == True)
                .label("matches"),
                func.avg(RuleExecution.execution_time_ms).label("avg_exec_time"),
            )
            .join(Rule, RuleExecution.rule_id == Rule.id)
            .group_by(Rule.type)
        )

        if filters:
            type_query = type_query.where(and_(*filters))

        if rule_type:
            type_query = type_query.where(Rule.type == rule_type)

        result = await self.session.execute(type_query)
        by_rule_type = []
        for row in result:
            evaluations = row.evaluations or 0
            matches = row.matches or 0
            match_rate = (matches / evaluations * 100) if evaluations > 0 else 0.0
            by_rule_type.append(
                {
                    "rule_type": str(row.type.value),
                    "evaluations": evaluations,
                    "matches": matches,
                    "match_rate": match_rate,
                    "avg_execution_time_ms": float(row.avg_exec_time or 0.0),
                }
            )

        # Get top performing rules (by match count)
        top_rules_query = (
            select(
                Rule.id,
                Rule.name,
                Rule.type,
                func.count(RuleExecution.id).label("evaluations"),
                func.count(RuleExecution.id)
                .filter(RuleExecution.matched == True)
                .label("matches"),
                func.avg(RuleExecution.execution_time_ms).label("avg_exec_time"),
            )
            .join(Rule, RuleExecution.rule_id == Rule.id)
            .group_by(Rule.id, Rule.name, Rule.type)
            .order_by(
                func.count(RuleExecution.id)
                .filter(RuleExecution.matched == True)
                .desc()
            )
            .limit(10)
        )

        if filters:
            top_rules_query = top_rules_query.where(and_(*filters))

        result = await self.session.execute(top_rules_query)
        top_rules = []
        for row in result:
            evaluations = row.evaluations or 0
            matches = row.matches or 0
            match_rate = (matches / evaluations * 100) if evaluations > 0 else 0.0
            top_rules.append(
                {
                    "rule_id": str(row.id),
                    "rule_name": row.name,
                    "rule_type": str(row.type.value),
                    "evaluations": evaluations,
                    "matches": matches,
                    "match_rate": match_rate,
                    "avg_execution_time_ms": float(row.avg_exec_time or 0.0),
                }
            )

        logger.info(
            "Rule statistics retrieved",
            event="get_rule_statistics_complete",
            total_evaluations=total_evaluations,
            total_matches=total_matches,
        )

        return {
            "total_evaluations": total_evaluations,
            "total_matches": total_matches,
            "by_rule_type": by_rule_type,
            "top_rules": top_rules,
        }

    async def get_transactions_for_export(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        status: Optional[TransactionStatus] = None,
        limit: int = 10000,
    ) -> List[Transaction]:
        """
        Get transactions for CSV export.

        Args:
            date_from: Start date filter
            date_to: End date filter
            status: Filter by transaction status
            limit: Maximum number of records to return

        Returns:
            List of Transaction objects
        """
        logger.info(
            "Fetching transactions for export",
            event="get_transactions_for_export_start",
            date_from=date_from,
            date_to=date_to,
            status=status,
            limit=limit,
        )

        # Build filters
        filters = []
        if date_from:
            filters.append(Transaction.timestamp >= date_from)
        if date_to:
            filters.append(Transaction.timestamp <= date_to)
        if status:
            filters.append(Transaction.status == status)

        # Build query
        query = select(Transaction).order_by(Transaction.timestamp.desc()).limit(limit)

        if filters:
            query = query.where(and_(*filters))

        result = await self.session.execute(query)
        transactions = result.scalars().all()

        logger.info(
            "Transactions fetched for export",
            event="get_transactions_for_export_complete",
            count=len(transactions),
        )

        return list(transactions)

    async def get_rule_executions_for_export(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        rule_type: Optional[RuleType] = None,
        limit: int = 10000,
    ) -> List[Tuple[RuleExecution, Rule]]:
        """
        Get rule executions with rule details for CSV export.

        Args:
            date_from: Start date filter
            date_to: End date filter
            rule_type: Filter by rule type
            limit: Maximum number of records to return

        Returns:
            List of tuples (RuleExecution, Rule)
        """
        logger.info(
            "Fetching rule executions for export",
            event="get_rule_executions_for_export_start",
            date_from=date_from,
            date_to=date_to,
            rule_type=rule_type,
            limit=limit,
        )

        # Build filters
        filters = []
        if date_from:
            filters.append(RuleExecution.executed_at >= date_from)
        if date_to:
            filters.append(RuleExecution.executed_at <= date_to)
        if rule_type:
            filters.append(Rule.type == rule_type)

        # Build query with JOIN
        query = (
            select(RuleExecution, Rule)
            .join(Rule, RuleExecution.rule_id == Rule.id)
            .order_by(RuleExecution.executed_at.desc())
            .limit(limit)
        )

        if filters:
            query = query.where(and_(*filters))

        result = await self.session.execute(query)
        executions = result.all()

        logger.info(
            "Rule executions fetched for export",
            event="get_rule_executions_for_export_complete",
            count=len(executions),
        )

        return executions
