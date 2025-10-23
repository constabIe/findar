"""
FastAPI routes for reporting module.

Provides REST API endpoints for generating reports, viewing statistics,
and exporting data in CSV format.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.modules.rule_engine.enums import RuleType, TransactionStatus, TransactionType
from src.storage.dependencies import get_db_session

from .schemas import RuleReportResponse, TransactionReportResponse
from .service import ReportingService, get_reporting_service

logger = get_logger("reporting.routes")

router = APIRouter()


@router.get(
    "/reports/transactions",
    response_model=TransactionReportResponse,
    summary="Get transaction statistics report",
    description="Generate aggregated statistics report for transactions with optional filters",
)
async def get_transaction_report(
    date_from: Optional[datetime] = Query(
        None, description="Start date for filtering (ISO format)"
    ),
    date_to: Optional[datetime] = Query(
        None, description="End date for filtering (ISO format)"
    ),
    status: Optional[TransactionStatus] = Query(
        None, description="Filter by transaction status"
    ),
    transaction_type: Optional[TransactionType] = Query(
        None, description="Filter by transaction type", alias="type"
    ),
    session: AsyncSession = Depends(get_db_session),
) -> TransactionReportResponse:
    """
    Generate transaction statistics report.

    Returns aggregated statistics including:
    - Total count of transactions
    - Breakdown by status (pending, processed, alerted, reviewed, rejected)
    - Breakdown by type (transfer, payment, withdrawal, deposit)
    - Processing time metrics (average, median, p95, p99)

    Args:
        date_from: Start date filter (optional)
        date_to: End date filter (optional)
        status: Filter by status (optional)
        transaction_type: Filter by type (optional)
        session: Database session (injected)

    Returns:
        TransactionReportResponse with statistics
    """
    # Generate request ID for tracking
    request_id = str(uuid4())

    logger.info(
        "Transaction report requested",
        event="transaction_report_request",
        request_id=request_id,
        date_from=date_from,
        date_to=date_to,
        status=status,
        transaction_type=transaction_type,
    )

    # Get service and generate report
    service = await get_reporting_service(session)
    report = await service.generate_transaction_report(
        request_id=request_id,
        date_from=date_from,
        date_to=date_to,
        status=status,
        transaction_type=transaction_type,
    )

    logger.info(
        "Transaction report generated",
        event="transaction_report_response",
        request_id=request_id,
        total_transactions=report.statistics.total_transactions,
    )

    return report


@router.get(
    "/reports/rules",
    response_model=RuleReportResponse,
    summary="Get rule statistics report",
    description="Generate aggregated statistics report for rule evaluations and performance",
)
async def get_rule_report(
    date_from: Optional[datetime] = Query(
        None, description="Start date for filtering (ISO format)"
    ),
    date_to: Optional[datetime] = Query(
        None, description="End date for filtering (ISO format)"
    ),
    rule_type: Optional[RuleType] = Query(None, description="Filter by rule type"),
    rule_id: Optional[str] = Query(None, description="Filter by specific rule ID (UUID)"),
    session: AsyncSession = Depends(get_db_session),
) -> RuleReportResponse:
    """
    Generate rule statistics report.

    Returns aggregated statistics including:
    - Total evaluations and matches
    - Overall match rate
    - Statistics grouped by rule type
    - Top performing rules (by match count)

    Args:
        date_from: Start date filter (optional)
        date_to: End date filter (optional)
        rule_type: Filter by rule type (optional)
        rule_id: Filter by specific rule ID (optional)
        session: Database session (injected)

    Returns:
        RuleReportResponse with statistics
    """
    # Generate request ID for tracking
    request_id = str(uuid4())

    logger.info(
        "Rule report requested",
        event="rule_report_request",
        request_id=request_id,
        date_from=date_from,
        date_to=date_to,
        rule_type=rule_type,
        rule_id=rule_id,
    )

    # Get service and generate report
    service = await get_reporting_service(session)
    report = await service.generate_rule_report(
        request_id=request_id,
        date_from=date_from,
        date_to=date_to,
        rule_type=rule_type,
        rule_id=rule_id,
    )

    logger.info(
        "Rule report generated",
        event="rule_report_response",
        request_id=request_id,
        total_evaluations=report.statistics.total_evaluations,
        total_matches=report.statistics.total_matches,
    )

    return report


@router.get(
    "/reports/export/csv",
    response_class=StreamingResponse,
    summary="Export data to CSV",
    description="Export transactions or rule executions data in CSV format",
)
async def export_to_csv(
    entity_type: str = Query(
        ...,
        description="Type of entity to export: 'transactions' or 'rules'",
        regex="^(transactions|rules)$",
    ),
    date_from: Optional[datetime] = Query(
        None, description="Start date for filtering (ISO format)"
    ),
    date_to: Optional[datetime] = Query(
        None, description="End date for filtering (ISO format)"
    ),
    status: Optional[TransactionStatus] = Query(
        None, description="Filter by transaction status (for transactions)"
    ),
    rule_type: Optional[RuleType] = Query(
        None, description="Filter by rule type (for rules)"
    ),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """
    Export data to CSV format.

    Supports exporting:
    - Transactions: with filters by date and status
    - Rule executions: with filters by date and rule type

    Args:
        entity_type: Type of entity ('transactions' or 'rules')
        date_from: Start date filter (optional)
        date_to: End date filter (optional)
        status: Transaction status filter (optional, for transactions)
        rule_type: Rule type filter (optional, for rules)
        session: Database session (injected)

    Returns:
        StreamingResponse with CSV file
    """
    # Generate request ID for tracking
    request_id = str(uuid4())

    logger.info(
        "CSV export requested",
        event="csv_export_request",
        request_id=request_id,
        entity_type=entity_type,
        date_from=date_from,
        date_to=date_to,
        status=status,
        rule_type=rule_type,
    )

    # Get service
    service = await get_reporting_service(session)

    # Generate CSV based on entity type
    if entity_type == "transactions":
        csv_content = await service.export_transactions_to_csv(
            request_id=request_id,
            date_from=date_from,
            date_to=date_to,
            status=status,
        )
        filename = f"transactions_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    else:  # entity_type == "rules"
        csv_content = await service.export_rule_executions_to_csv(
            request_id=request_id,
            date_from=date_from,
            date_to=date_to,
            rule_type=rule_type,
        )
        filename = f"rule_executions_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    logger.info(
        "CSV export completed",
        event="csv_export_response",
        request_id=request_id,
        entity_type=entity_type,
        filename=filename,
    )

    # Return as streaming response
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
