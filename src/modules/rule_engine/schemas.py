"""
Pydantic schemas for the rule engine module.

Contains input/output schemas for API requests, rule parameters, evaluation results,
and other data structures used in the fraud detection rule engine.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from .enums import (
    CacheStatus,
    CompositeOperator,
    RiskLevel,
    RuleMatchStatus,
    RuleType,
    ThresholdOperator,
    TimeWindow,
)


class ThresholdRuleParams(BaseModel):
    """
    Parameters for threshold-based fraud detection rules.

    Examples of threshold rules:
    - Transaction amount exceeds limit
    - Number of transactions from account exceeds frequency limit
    - Transaction count to specific account exceeds limit
    - Number of different transaction types from same sender
    - Transaction outside of allowed time window
    """

    # Amount thresholds
    max_amount: Optional[float] = Field(
        None, description="Maximum transaction amount allowed"
    )
    min_amount: Optional[float] = Field(
        None, description="Minimum transaction amount allowed"
    )

    # Comparison operator for numeric thresholds
    operator: ThresholdOperator = Field(
        ThresholdOperator.GREATER_THAN, description="Comparison operator"
    )

    # Time-based thresholds
    time_window: Optional[TimeWindow] = Field(
        None, description="Time window for frequency checks"
    )
    allowed_hours_start: Optional[int] = Field(
        None, ge=0, le=23, description="Start of allowed transaction hours (0-23)"
    )
    allowed_hours_end: Optional[int] = Field(
        None, ge=0, le=23, description="End of allowed transaction hours (0-23)"
    )

    # Geographic thresholds
    allowed_locations: Optional[List[str]] = Field(
        None, description="List of allowed transaction locations"
    )

    # Device/IP thresholds
    max_devices_per_account: Optional[int] = Field(
        None, description="Max unique devices per account in time window"
    )
    max_ips_per_account: Optional[int] = Field(
        None, description="Max unique IPs per account in time window"
    )

    # Velocity thresholds
    max_velocity_amount: Optional[float] = Field(
        None,
        description="Maximum total amount in time window (limit of sum transfer in period)",
    )

    # Frequency thresholds (within time window)
    max_transaction_types: Optional[int] = Field(
        None, description="Max different transaction types per account"
    )
    max_transactions_per_account: Optional[int] = Field(
        None, description="Max transactions from same account"
    )
    max_transactions_to_account: Optional[int] = Field(
        None, description="Max transactions to same account"
    )
    max_transactions_per_ip: Optional[int] = Field(
        None, description="Max transactions from same IP address"
    )

    @field_validator("allowed_hours_end")
    @classmethod
    def validate_time_range(cls, v, info):
        """Validate that end hour is after start hour."""
        # In Pydantic v2, use info.data to access other field values
        start = info.data.get("allowed_hours_start")
        if start is not None and v is not None and v <= start:
            raise ValueError(
                "allowed_hours_end must be greater than allowed_hours_start"
            )
        return v


class PatternRuleParams(BaseModel):
    """
    Parameters for pattern-based fraud detection rules.

    Pattern rules analyze the dynamics of transactions to detect suspicious patterns,
    such as rapid small transactions (structuring/smurfing), unusual sequences,
    or patterns of behavior across multiple transactions.
    """

    # Required: Time window for pattern detection
    period: TimeWindow = Field(
        description="Duration of the time window for pattern analysis (required)"
    )

    # Transaction count in pattern
    count: Optional[int] = Field(
        None, ge=1, description="Number of transactions in the period"
    )

    # Amount constraints
    amount_ceiling: Optional[float] = Field(
        None, description="Maximum sum of all transactions in the period"
    )

    # Recipient patterns
    same_recipient: bool = Field(
        False, description="All transactions must be to the same recipient"
    )
    unique_recipients: Optional[int] = Field(
        None, description="Maximum number of unique recipients in the period"
    )

    # Device patterns
    same_device: bool = Field(
        False, description="All transactions must be from the same device"
    )

    # Velocity limit
    velocity_limit: Optional[float] = Field(
        None, description="Maximum sum of transactions from one device in the period"
    )


class CompositeRuleParams(BaseModel):
    """
    Parameters for composite rules that combine multiple rules with logical operators.

    Composite rules allow complex logic by combining other rules with AND, OR, NOT operations.
    
    Note: For NOT operator, the logic is applied to all rules using OR:
    NOT(rule1 OR rule2 OR ...) - returns True if NONE of the rules match.
    
    Rules are referenced by their unique names (not UUIDs).
    """

    # Logical operator
    operator: CompositeOperator = Field(
        CompositeOperator.AND, description="Logical operator (AND/OR/NOT)"
    )

    # Rule references (must be rule names)
    rules: List[str] = Field(
        min_length=1, description="List of rule names to combine"
    )

    @field_validator("rules")
    @classmethod
    def validate_rules_list(cls, v):
        """Validate that rules list is not empty and all items are non-empty strings."""
        if not v or len(v) == 0:
            raise ValueError("Rules list cannot be empty")
        
        # Check that all items are non-empty strings
        for rule_name in v:
            if not rule_name or not isinstance(rule_name, str) or not rule_name.strip():
                raise ValueError("All rule names must be non-empty strings")
        
        return v


class MLRuleParams(BaseModel):
    """
    Parameters for machine learning-based fraud detection rules.

    ML rules use trained models to assess transaction risk with confidence scores.
    The model is accessed via an endpoint URL.
    """

    # Model configuration
    model_version: str = Field(
        description="Version of the ML model to use (e.g., 'v1.0.0', 'latest')"
    )

    # Scoring threshold
    threshold: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score for positive match (0.0-1.0)",
    )

    # Endpoint configuration
    endpoint_url: str = Field(description="URL of the ML model inference endpoint")

    @field_validator("endpoint_url")
    @classmethod
    def validate_endpoint_url(cls, v):
        """Validate that endpoint URL is not empty and has valid format."""
        if not v or not v.strip():
            raise ValueError("Endpoint URL cannot be empty")

        # Basic URL validation
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("Endpoint URL must start with http:// or https://")

        return v.strip()


class RuleEvaluationRequest(BaseModel):
    """Request schema for evaluating rules against a transaction."""

    transaction_id: UUID = Field(description="ID of transaction to evaluate")
    rule_ids: Optional[List[int]] = Field(
        None, description="Specific rule IDs to evaluate (None = all active)"
    )
    correlation_id: UUID = Field(description="Correlation ID for tracking")

    # Evaluation options
    include_context: bool = Field(
        True, description="Include evaluation context in results"
    )
    include_performance: bool = Field(False, description="Include performance metrics")
    stop_on_critical_match: bool = Field(
        True, description="Stop evaluation on critical rule match"
    )


class RuleContext(BaseModel):
    """Context information for rule evaluation."""

    # Transaction context
    transaction_data: Dict[str, Any] = Field(
        description="Transaction data used in evaluation"
    )

    # Rule-specific context
    threshold_values: Optional[Dict[str, Any]] = Field(
        None, description="Calculated threshold values"
    )
    pattern_matches: Optional[List[Dict[str, Any]]] = Field(
        None, description="Pattern match details"
    )
    composite_results: Optional[Dict[int, bool]] = Field(
        None, description="Results from composite rule components"
    )
    ml_features: Optional[Dict[str, float]] = Field(
        None, description="ML model features and values"
    )

    # Historical context
    related_transactions: Optional[List[UUID]] = Field(
        None, description="Related transactions considered"
    )
    account_history: Optional[Dict[str, Any]] = Field(
        None, description="Account history summary"
    )

    # Performance context
    execution_time_ms: Optional[float] = Field(None, description="Rule execution time")


class RuleEvaluationResult(BaseModel):
    """Result of evaluating a single rule against a transaction."""

    rule_id: UUID = Field(description="ID of evaluated rule")
    rule_name: str = Field(description="Name of evaluated rule")
    rule_type: RuleType = Field(description="Type of rule")

    # Evaluation results
    match_status: RuleMatchStatus = Field(description="Rule evaluation result")
    confidence_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Confidence score (for ML rules)"
    )
    risk_level: RiskLevel = Field(description="Assessed risk level")

    # Context and explanation
    context: Optional[RuleContext] = Field(
        None, description="Detailed evaluation context"
    )
    match_reason: Optional[str] = Field(
        None, description="Human-readable explanation of match/non-match"
    )

    # Metadata
    execution_time_ms: float = Field(description="Execution time in milliseconds")
    executed_at: datetime = Field(description="Evaluation timestamp")
    error_message: Optional[str] = Field(
        None, description="Error message if evaluation failed"
    )


class TransactionEvaluationResult(BaseModel):
    """Complete evaluation result for a transaction against all rules."""

    transaction_id: UUID = Field(description="Evaluated transaction ID")
    correlation_id: UUID = Field(description="Request correlation ID")

    # Overall results
    overall_risk_level: RiskLevel = Field(description="Overall assessed risk level")
    flagged: bool = Field(description="Whether transaction should be flagged")
    should_block: bool = Field(description="Whether transaction should be blocked")

    # Individual rule results
    rule_results: List[RuleEvaluationResult] = Field(
        description="Results from individual rules"
    )

    # Summary statistics
    total_rules_evaluated: int = Field(description="Number of rules evaluated")
    rules_matched: int = Field(description="Number of rules that matched")
    critical_rules_matched: int = Field(
        description="Number of critical rules that matched"
    )

    # Performance
    total_evaluation_time_ms: float = Field(description="Total evaluation time")
    evaluated_at: datetime = Field(description="Evaluation completion timestamp")


class RuleCreateRequest(BaseModel):
    """Schema for creating a new rule."""

    name: str = Field(min_length=1, max_length=255, description="Rule name")
    type: RuleType = Field(description="Rule type")
    params: Union[
        ThresholdRuleParams, PatternRuleParams, CompositeRuleParams, MLRuleParams
    ] = Field(description="Rule parameters")
    enabled: bool = Field(True, description="Whether rule is enabled")
    priority: int = Field(0, description="Rule priority")
    critical: bool = Field(False, description="Whether rule is critical")
    description: Optional[str] = Field(
        None, max_length=1000, description="Rule description"
    )

    @field_validator("params", mode="after")
    def validate_params_match_type(cls, params, info):
        """Validate that params match the rule type."""
        rule_type = info.data.get("type")

        if rule_type == RuleType.THRESHOLD and not isinstance(
            params, ThresholdRuleParams
        ):
            raise ValueError("Threshold rules must use ThresholdRuleParams")
        elif rule_type == RuleType.PATTERN and not isinstance(
            params, PatternRuleParams
        ):
            raise ValueError("Pattern rules must use PatternRuleParams")
        elif rule_type == RuleType.COMPOSITE and not isinstance(
            params, CompositeRuleParams
        ):
            raise ValueError("Composite rules must use CompositeRuleParams")
        elif rule_type == RuleType.ML and not isinstance(params, MLRuleParams):
            raise ValueError("ML rules must use MLRuleParams")

        return params


class RuleUpdateRequest(BaseModel):
    """Schema for updating an existing rule."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Rule name"
    )
    params: Optional[
        Union[ThresholdRuleParams, PatternRuleParams, CompositeRuleParams, MLRuleParams]
    ] = Field(None, description="Rule parameters")
    enabled: Optional[bool] = Field(None, description="Whether rule is enabled")
    priority: Optional[int] = Field(None, description="Rule priority")
    critical: Optional[bool] = Field(None, description="Whether rule is critical")
    description: Optional[str] = Field(
        None, max_length=1000, description="Rule description"
    )


class RuleResponse(BaseModel):
    """Schema for rule API responses."""

    id: UUID = Field(description="Rule ID")
    name: str = Field(description="Rule name")
    type: RuleType = Field(description="Rule type")
    params: Dict[str, Any] = Field(description="Rule parameters")
    enabled: bool = Field(description="Whether rule is enabled")
    priority: int = Field(description="Rule priority")
    critical: bool = Field(description="Whether rule is critical")
    description: Optional[str] = Field(description="Rule description")

    # User tracking
    created_by_user_id: Optional[UUID] = Field(
        None, description="ID of user who created this rule"
    )

    # Statistics
    execution_count: int = Field(description="Total executions")
    match_count: int = Field(description="Total matches")
    # match_rate: Optional[float] = Field(None, description="Match rate percentage")

    # Timestamps
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    # last_executed_at: Optional[datetime] = Field(
    #     None, description="Last execution timestamp"
    # )
    class Config:
        from_attributes = True  # replaces orm_mode=True in Pydantic v2
        use_enum_values = True  # ensures Enum.value is used, not Enum object


class RuleListResponse(BaseModel):
    """Schema for paginated rule list responses."""

    rules: List[RuleResponse] = Field(description="List of rules")
    total: int = Field(description="Total number of rules")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of rules per page")
    pages: int = Field(description="Total number of pages")


class CacheStatusResponse(BaseModel):
    """Schema for rule cache status."""

    rule_id: UUID = Field(description="Rule ID")
    cache_key: str = Field(description="Redis cache key")
    status: CacheStatus = Field(description="Cache status")
    cached_at: Optional[datetime] = Field(None, description="Cache timestamp")
    expires_at: Optional[datetime] = Field(None, description="Cache expiration")
    hit_count: int = Field(description="Number of cache hits")
    cache_version: str = Field(description="Cached version")


class CacheStatisticsResponse(BaseModel):
    """Schema for overall cache statistics."""

    active_rules_count: int = Field(description="Number of active rules in cache")
    rule_types_count: int = Field(
        description="Number of different rule type sets in cache"
    )
    priority_index_size: int = Field(description="Size of priority index")
    timestamp: str = Field(description="Timestamp when statistics were retrieved")


class HotReloadRequest(BaseModel):
    """Schema for hot reload requests."""

    rule_ids: Optional[List[int]] = Field(
        None, description="Specific rule IDs to reload (None = all)"
    )
    force_refresh: bool = Field(
        False, description="Force refresh even if cached version is current"
    )
    clear_cache: bool = Field(False, description="Clear existing cache before reload")


class HotReloadResponse(BaseModel):
    """Schema for hot reload responses."""

    reloaded_rules: List[int] = Field(description="Rule IDs that were reloaded")
    failed_rules: List[int] = Field(description="Rule IDs that failed to reload")
    cache_statistics: List[CacheStatusResponse] = Field(
        description="Updated cache statistics"
    )
    reload_time_ms: float = Field(description="Total reload time in milliseconds")
    timestamp: datetime = Field(description="Reload completion timestamp")
