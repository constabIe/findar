"""
Pydantic schemas for reporting module.

Defines request and response models for transaction reports, rule statistics,
and CSV export functionality.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from src.modules.rule_engine.enums import RuleType, TransactionStatus, TransactionType


class TransactionReportRequest(BaseModel):
    """Request parameters for transaction report generation."""

    date_from: Optional[datetime] = Field(
        None, description="Start date for filtering transactions"
    )
    date_to: Optional[datetime] = Field(
        None, description="End date for filtering transactions"
    )
    status: Optional[TransactionStatus] = Field(
        None, description="Filter by transaction status"
    )
    transaction_type: Optional[TransactionType] = Field(
        None, description="Filter by transaction type"
    )


class RuleReportRequest(BaseModel):
    """Request parameters for rule statistics report."""

    date_from: Optional[datetime] = Field(
        None, description="Start date for filtering rule executions"
    )
    date_to: Optional[datetime] = Field(
        None, description="End date for filtering rule executions"
    )
    rule_type: Optional[RuleType] = Field(
        None, description="Filter by rule type")
    rule_id: Optional[str] = Field(
        None, description="Filter by specific rule ID")


class ExportCSVRequest(BaseModel):
    """Request parameters for CSV export."""

    entity_type: str = Field(
        ...,
        description="Type of entity to export (transactions or rules)",
        pattern="^(transactions|rules)$",
    )
    date_from: Optional[datetime] = Field(
        None, description="Start date for filtering data"
    )
    date_to: Optional[datetime] = Field(
        None, description="End date for filtering data")
    status: Optional[TransactionStatus] = Field(
        None, description="Filter by status (for transactions)"
    )
    rule_type: Optional[RuleType] = Field(
        None, description="Filter by rule type (for rules)"
    )


class StatusBreakdown(BaseModel):
    """Breakdown of counts by status."""

    pending: int = Field(0, description="Number of pending transactions")
    processed: int = Field(0, description="Number of processed transactions")
    alerted: int = Field(0, description="Number of alerted transactions")
    reviewed: int = Field(0, description="Number of reviewed transactions")
    rejected: int = Field(0, description="Number of rejected transactions")


class TypeBreakdown(BaseModel):
    """Breakdown of counts by transaction type."""

    transfer: int = Field(0, description="Number of transfer transactions")
    payment: int = Field(0, description="Number of payment transactions")
    withdrawal: int = Field(0, description="Number of withdrawal transactions")
    deposit: int = Field(0, description="Number of deposit transactions")


class ProcessingMetrics(BaseModel):
    """Metrics related to processing time."""

    average_time_seconds: float = Field(
        0.0, description="Average processing time in seconds"
    )
    median_time_seconds: float = Field(
        0.0, description="Median (p50) processing time in seconds"
    )
    p95_time_seconds: float = Field(
        0.0, description="95th percentile processing time in seconds"
    )
    p99_time_seconds: float = Field(
        0.0, description="99th percentile processing time in seconds"
    )
    min_time_seconds: float = Field(
        0.0, description="Minimum processing time in seconds"
    )
    max_time_seconds: float = Field(
        0.0, description="Maximum processing time in seconds"
    )


class RuleTypeStatistics(BaseModel):
    """Statistics for a specific rule type."""

    rule_type: str = Field(..., description="Type of rule")
    total_evaluations: int = Field(
        0, description="Total number of evaluations")
    total_matches: int = Field(0, description="Total number of matches")
    match_rate: float = Field(
        0.0, description="Match rate (matches/evaluations)")
    average_execution_time_ms: float = Field(
        0.0, description="Average execution time in milliseconds"
    )


class RulePerformance(BaseModel):
    """Performance metrics for a specific rule."""

    rule_id: str = Field(..., description="Unique rule identifier")
    rule_name: str = Field(..., description="Rule name")
    rule_type: str = Field(..., description="Rule type")
    evaluations: int = Field(0, description="Number of evaluations")
    matches: int = Field(0, description="Number of matches")
    match_rate: float = Field(0.0, description="Match rate percentage")
    avg_execution_time_ms: float = Field(
        0.0, description="Average execution time in milliseconds"
    )


class TransactionStatistics(BaseModel):
    """Aggregated statistics about transactions."""

    total_transactions: int = Field(
        0, description="Total number of transactions")
    by_status: Optional[StatusBreakdown] = Field(
        None, description="Breakdown by status"
    )
    by_type: Optional[TypeBreakdown] = Field(
        None, description="Breakdown by type"
    )
    processing_metrics: Optional[ProcessingMetrics] = Field(
        None, description="Processing time metrics"
    )
    date_from: Optional[datetime] = Field(
        None, description="Start date of the report period"
    )
    date_to: Optional[datetime] = Field(
        None, description="End date of the report period")


class RuleStatistics(BaseModel):
    """Aggregated statistics about rule evaluations."""

    total_evaluations: int = Field(
        0, description="Total number of rule evaluations")
    total_matches: int = Field(0, description="Total number of rule matches")
    overall_match_rate: float = Field(
        0.0, description="Overall match rate across all rules"
    )
    by_rule_type: List[RuleTypeStatistics] = Field(
        default_factory=list, description="Statistics grouped by rule type"
    )
    top_rules: List[RulePerformance] = Field(
        default_factory=list, description="Top performing rules by match count"
    )
    date_from: Optional[datetime] = Field(
        None, description="Start date of the report period"
    )
    date_to: Optional[datetime] = Field(
        None, description="End date of the report period")


class TransactionReportResponse(BaseModel):
    """Complete response for transaction report request."""

    report_generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp when report was generated"
    )
    request_id: str = Field(..., description="Request tracking ID")
    statistics: TransactionStatistics = Field(
        ..., description="Transaction statistics"
    )


class RuleReportResponse(BaseModel):
    """Complete response for rule report request."""

    report_generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp when report was generated"
    )
    request_id: str = Field(..., description="Request tracking ID")
    statistics: RuleStatistics = Field(..., description="Rule statistics")


class TransactionExportRow(BaseModel):
    """Single row for transaction CSV export."""

    transaction_id: str
    timestamp: datetime
    amount: float
    from_account: str
    to_account: str
    type: str
    status: str
    currency: str
    correlation_id: str  # Original transaction correlation_id from database
    merchant_id: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None


class RuleExecutionExportRow(BaseModel):
    """Single row for rule execution CSV export."""

    execution_id: str
    rule_id: str
    rule_name: str
    rule_type: str
    transaction_id: str
    correlation_id: str  # Original transaction correlation_id from database
    matched: bool
    confidence_score: Optional[float]
    execution_time_ms: float
    executed_at: datetime
