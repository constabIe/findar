"""
Service layer for reporting module.

Provides business logic for generating reports, aggregating statistics,
and exporting data in various formats.
"""

import csv
import io
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.modules.rule_engine.enums import RuleType, TransactionStatus, TransactionType

from .repository import ReportingRepository
from .schemas import (
    ProcessingMetrics,
    RulePerformance,
    RuleReportResponse,
    RuleStatistics,
    RuleTypeStatistics,
    StatusBreakdown,
    TransactionReportResponse,
    TransactionStatistics,
    TypeBreakdown,
)

logger = get_logger("reporting.service")


class ReportingService:
    """
    Service for generating reports and statistics.

    Coordinates between repository layer and API layer, applying
    business logic and data formatting.
    """

    def __init__(self, repository: ReportingRepository):
        """
        Initialize reporting service.

        Args:
            repository: Repository for database operations
        """
        self.repository = repository

    async def generate_transaction_report(
        self,
        request_id: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        status: Optional[TransactionStatus] = None,
        transaction_type: Optional[TransactionType] = None,
    ) -> TransactionReportResponse:
        """
        Generate comprehensive transaction report.

        Args:
            request_id: Request tracking ID for logging
            date_from: Start date filter
            date_to: End date filter
            status: Filter by transaction status
            transaction_type: Filter by transaction type

        Returns:
            TransactionReportResponse with aggregated statistics
        """
        logger.info(
            "Generating transaction report",
            event="generate_transaction_report_start",
            request_id=request_id,
            date_from=date_from,
            date_to=date_to,
            status=status,
            transaction_type=transaction_type,
        )

        # Get transaction statistics
        stats = await self.repository.get_transaction_statistics(
            date_from=date_from,
            date_to=date_to,
            status=status,
            transaction_type=transaction_type,
        )

        # Get processing metrics
        processing_metrics_data = await self.repository.get_processing_metrics(
            date_from=date_from, date_to=date_to
        )

        # Build status breakdown
        status_breakdown = StatusBreakdown(
            pending=stats["by_status"].get("pending", 0),
            processed=stats["by_status"].get("processed", 0),
            alerted=stats["by_status"].get("alerted", 0),
            reviewed=stats["by_status"].get("reviewed", 0),
            rejected=stats["by_status"].get("rejected", 0),
        )

        # Build type breakdown
        type_breakdown = TypeBreakdown(
            transfer=stats["by_type"].get("transfer", 0),
            payment=stats["by_type"].get("payment", 0),
            withdrawal=stats["by_type"].get("withdrawal", 0),
            deposit=stats["by_type"].get("deposit", 0),
        )

        # Build processing metrics
        processing_metrics = ProcessingMetrics(
            average_time_seconds=processing_metrics_data["average_time"],
            median_time_seconds=processing_metrics_data["median_time"],
            p95_time_seconds=processing_metrics_data["p95_time"],
            p99_time_seconds=processing_metrics_data["p99_time"],
            min_time_seconds=processing_metrics_data["min_time"],
            max_time_seconds=processing_metrics_data["max_time"],
        )

        # Build final statistics
        transaction_statistics = TransactionStatistics(
            total_transactions=stats["total_count"],
            by_status=status_breakdown,
            by_type=type_breakdown,
            processing_metrics=processing_metrics,
            date_from=date_from,
            date_to=date_to,
        )

        logger.info(
            "Transaction report generated",
            event="generate_transaction_report_complete",
            request_id=request_id,
            total_transactions=stats["total_count"],
        )

        return TransactionReportResponse(
            request_id=request_id,
            statistics=transaction_statistics,
        )

    async def generate_rule_report(
        self,
        request_id: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        rule_type: Optional[RuleType] = None,
        rule_id: Optional[str] = None,
    ) -> RuleReportResponse:
        """
        Generate comprehensive rule statistics report.

        Args:
            request_id: Request tracking ID for logging
            date_from: Start date filter
            date_to: End date filter
            rule_type: Filter by rule type
            rule_id: Filter by specific rule ID

        Returns:
            RuleReportResponse with aggregated statistics
        """
        logger.info(
            "Generating rule report",
            event="generate_rule_report_start",
            request_id=request_id,
            date_from=date_from,
            date_to=date_to,
            rule_type=rule_type,
            rule_id=rule_id,
        )

        # Get rule statistics from repository
        from uuid import UUID

        rule_uuid = UUID(rule_id) if rule_id else None

        stats = await self.repository.get_rule_statistics(
            date_from=date_from,
            date_to=date_to,
            rule_type=rule_type,
            rule_id=rule_uuid,
        )

        # Calculate overall match rate
        total_evals = stats["total_evaluations"]
        total_matches = stats["total_matches"]
        overall_match_rate = (
            (total_matches / total_evals * 100) if total_evals > 0 else 0.0
        )

        # Build rule type statistics
        by_rule_type = [
            RuleTypeStatistics(
                rule_type=item["rule_type"],
                total_evaluations=item["evaluations"],
                total_matches=item["matches"],
                match_rate=item["match_rate"],
                average_execution_time_ms=item["avg_execution_time_ms"],
            )
            for item in stats["by_rule_type"]
        ]

        # Build top rules list
        top_rules = [
            RulePerformance(
                rule_id=item["rule_id"],
                rule_name=item["rule_name"],
                rule_type=item["rule_type"],
                evaluations=item["evaluations"],
                matches=item["matches"],
                match_rate=item["match_rate"],
                avg_execution_time_ms=item["avg_execution_time_ms"],
            )
            for item in stats["top_rules"]
        ]

        # Build final statistics
        rule_statistics = RuleStatistics(
            total_evaluations=total_evals,
            total_matches=total_matches,
            overall_match_rate=overall_match_rate,
            by_rule_type=by_rule_type,
            top_rules=top_rules,
            date_from=date_from,
            date_to=date_to,
        )

        logger.info(
            "Rule report generated",
            event="generate_rule_report_complete",
            request_id=request_id,
            total_evaluations=total_evals,
            total_matches=total_matches,
        )

        return RuleReportResponse(
            request_id=request_id,
            statistics=rule_statistics,
        )

    async def export_transactions_to_csv(
        self,
        request_id: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        status: Optional[TransactionStatus] = None,
    ) -> str:
        """
        Export transactions to CSV format.

        Args:
            request_id: Request tracking ID for logging
            date_from: Start date filter
            date_to: End date filter
            status: Filter by transaction status

        Returns:
            CSV content as string
        """
        logger.info(
            "Exporting transactions to CSV",
            event="export_transactions_csv_start",
            request_id=request_id,
            date_from=date_from,
            date_to=date_to,
            status=status,
        )

        # Get transactions from repository
        transactions = await self.repository.get_transactions_for_export(
            date_from=date_from,
            date_to=date_to,
            status=status,
        )

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "transaction_id",
                "timestamp",
                "amount",
                "currency",
                "from_account",
                "to_account",
                "type",
                "status",
                "correlation_id",
                "merchant_id",
                "location",
                "description",
            ]
        )

        # Write data rows
        for txn in transactions:
            writer.writerow(
                [
                    str(txn.id),
                    txn.timestamp.isoformat() if txn.timestamp else "",
                    txn.amount,
                    txn.currency,
                    txn.from_account,
                    txn.to_account,
                    txn.type.value if txn.type else "",
                    txn.status.value if txn.status else "",
                    txn.correlation_id,
                    txn.merchant_id or "",
                    txn.location or "",
                    txn.description or "",
                ]
            )

        csv_content = output.getvalue()
        output.close()

        logger.info(
            "Transactions exported to CSV",
            event="export_transactions_csv_complete",
            request_id=request_id,
            count=len(transactions),
        )

        return csv_content

    async def export_rule_executions_to_csv(
        self,
        request_id: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        rule_type: Optional[RuleType] = None,
    ) -> str:
        """
        Export rule executions to CSV format.

        Args:
            request_id: Request tracking ID for logging
            date_from: Start date filter
            date_to: End date filter
            rule_type: Filter by rule type

        Returns:
            CSV content as string
        """
        logger.info(
            "Exporting rule executions to CSV",
            event="export_rule_executions_csv_start",
            request_id=request_id,
            date_from=date_from,
            date_to=date_to,
            rule_type=rule_type,
        )

        # Get rule executions from repository
        executions = await self.repository.get_rule_executions_for_export(
            date_from=date_from,
            date_to=date_to,
            rule_type=rule_type,
        )

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "execution_id",
                "rule_id",
                "rule_name",
                "rule_type",
                "transaction_id",
                "correlation_id",
                "matched",
                "confidence_score",
                "execution_time_ms",
                "executed_at",
            ]
        )

        # Write data rows
        for execution, rule in executions:
            writer.writerow(
                [
                    str(execution.id),
                    str(execution.rule_id),
                    rule.name,
                    rule.type.value if rule.type else "",
                    str(execution.transaction_id),
                    execution.correlation_id,
                    execution.matched,
                    execution.confidence_score or "",
                    execution.execution_time_ms,
                    execution.executed_at.isoformat() if execution.executed_at else "",
                ]
            )

        csv_content = output.getvalue()
        output.close()

        logger.info(
            "Rule executions exported to CSV",
            event="export_rule_executions_csv_complete",
            request_id=request_id,
            count=len(executions),
        )

        return csv_content


# Dependency function for FastAPI
async def get_reporting_service(session: AsyncSession) -> ReportingService:
    """
    Create and return ReportingService instance.

    Args:
        session: Async database session

    Returns:
        ReportingService instance
    """
    repository = ReportingRepository(session)
    return ReportingService(repository)
