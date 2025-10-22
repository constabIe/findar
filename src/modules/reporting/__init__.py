"""
Reporting module for analytics, metrics, and data export.

This module provides comprehensive reporting capabilities including:
- Prometheus metrics collection for real-time monitoring
- Transaction statistics and aggregation
- Rule performance analytics
- CSV export functionality for transactions and rule executions
- REST API endpoints for accessing reports

Key Components:
    - metrics: Prometheus metrics definitions and helper functions
    - schemas: Pydantic models for request/response validation
    - repository: Database queries for statistics aggregation
    - service: Business logic for report generation and CSV export
    - routes: FastAPI endpoints for accessing reports

Metrics Categories:
    - Transaction metrics: counts by status/type, processing time
    - Rule metrics: evaluations, matches, execution time, match rates
    - Queue metrics: task processing, worker statistics (inherited)

IDs in the system:
    - request_id: Generated for each API request to reporting endpoints (for request tracing)
    - correlation_id: Original transaction ID from database (for transaction tracing through pipeline)

Usage:
    # Import metrics for instrumentation
    from src.modules.reporting.metrics import (
        increment_transaction_counter,
        increment_rule_matched_counter,
    )
    
    # Import service for generating reports
    from src.modules.reporting.service import ReportingService
    
    # Import router for FastAPI registration
    from src.modules.reporting.routes import router
"""

from .routes import router
from .schemas import (
    RuleReportResponse,
    RuleStatistics,
    TransactionReportResponse,
    TransactionStatistics,
)
from .service import ReportingService, get_reporting_service

__all__ = [
    "router",
    "ReportingService",
    "get_reporting_service",
    "TransactionReportResponse",
    "TransactionStatistics",
    "RuleReportResponse",
    "RuleStatistics",
]
