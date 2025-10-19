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
    TransactionType,
)


# Now there can problem with multiple parameters usage (e.g. just one rule was set)
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

    # Frequency thresholds (within time window)
    max_transactions_per_account: Optional[int] = Field(
        None, description="Max transactions from same account"
    )
    max_transactions_to_account: Optional[int] = Field(
        None, description="Max transactions to same account"
    )
    max_transaction_types: Optional[int] = Field(
        None, description="Max different transaction types per account"
    )

    # Time-based thresholds
    time_window: TimeWindow = Field(
        TimeWindow.HOUR, description="Time window for frequency checks"
    )
    allowed_hours_start: Optional[int] = Field(
        None, ge=0, le=23, description="Start of allowed transaction hours (0-23)"
    )
    allowed_hours_end: Optional[int] = Field(
        None, ge=0, le=23, description="End of allowed transaction hours (0-23)"
    )

    # Velocity thresholds
    max_velocity_amount: Optional[float] = Field(
        None, description="Maximum total amount in time window"
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

    # Comparison operator for numeric thresholds
    operator: ThresholdOperator = Field(
        ThresholdOperator.GREATER_THAN, description="Comparison operator"
    )

    @field_validator("allowed_hours_end")
    def validate_time_range(cls, v, values):
        """Validate that end hour is after start hour."""
        start = values.get("allowed_hours_start")
        if start is not None and v is not None and v <= start:
            raise ValueError(
                "allowed_hours_end must be greater than allowed_hours_start"
            )
        return v


class PatternRuleParams(BaseModel):
    """
    Parameters for pattern-based fraud detection rules.

    Pattern rules detect series of transactions that match suspicious patterns,
    such as rapid small transactions (structuring/smurfing) or unusual sequences.
    """

    # Pattern definition
    min_transactions: int = Field(
        3, ge=1, description="Minimum number of transactions in pattern"
    )
    max_transactions: Optional[int] = Field(
        None, description="Maximum number of transactions in pattern"
    )
    time_window: TimeWindow = Field(
        TimeWindow.HOUR, description="Time window for pattern detection"
    )

    # Amount patterns
    max_individual_amount: Optional[float] = Field(
        None, description="Maximum amount per transaction in pattern"
    )
    min_individual_amount: Optional[float] = Field(
        None, description="Minimum amount per transaction in pattern"
    )
    max_total_amount: Optional[float] = Field(
        None, description="Maximum total amount for all transactions"
    )

    # Sequence patterns
    require_sequential: bool = Field(
        False, description="Whether transactions must be sequential in time"
    )
    max_time_between_transactions: Optional[int] = Field(
        None, description="Max seconds between consecutive transactions"
    )

    # Account patterns
    same_source_account: bool = Field(
        True, description="All transactions from same source account"
    )
    same_destination_account: bool = Field(
        False, description="All transactions to same destination account"
    )
    different_destination_accounts: bool = Field(
        False, description="All transactions to different accounts"
    )

    # Transaction type patterns
    allowed_types: Optional[List[TransactionType]] = Field(
        None, description="Allowed transaction types in pattern"
    )
    require_same_type: bool = Field(
        False, description="All transactions must be same type"
    )

    # Geographic patterns
    same_location: bool = Field(
        False, description="All transactions from same location"
    )
    different_locations: bool = Field(
        False, description="All transactions from different locations"
    )

    # Structuring detection (classic money laundering pattern)
    detect_structuring: bool = Field(
        False, description="Detect structuring patterns (many small amounts)"
    )
    structuring_threshold: Optional[float] = Field(
        9999.0, description="Amount threshold for structuring detection"
    )


class CompositeRuleParams(BaseModel):
    """
    Parameters for composite rules that combine multiple rules with logical operators.

    Composite rules allow complex logic by combining other rules with AND, OR, NOT operations.
    """

    # Rule references
    rule_ids: List[int] = Field(min_items=1, description="List of rule IDs to combine")  # type: ignore

    # Logical structure
    operator: CompositeOperator = Field(
        CompositeOperator.AND, description="Primary logical operator"
    )
    expression: Optional[str] = Field(
        None,
        description="Complex boolean expression (e.g., '(rule1 AND rule2) OR NOT rule3')",
    )

    # Execution settings
    short_circuit: bool = Field(
        True,
        description="Stop evaluation on first match (for OR) or first non-match (for AND)",
    )
    require_all_success: bool = Field(
        False, description="Require all referenced rules to execute successfully"
    )

    # Scoring
    weight_mode: str = Field(
        "equal",
        description="How to weight individual rule results (equal, priority, custom)",
    )
    custom_weights: Optional[Dict[int, float]] = Field(
        None, description="Custom weights for each rule (rule_id -> weight)"
    )
    min_weighted_score: Optional[float] = Field(
        None, description="Minimum weighted score for match"
    )

    @field_validator("expression")
    def validate_expression(cls, v, values):
        """Validate boolean expression contains only referenced rule IDs."""
        if v is not None:
            rule_ids = values.get("rule_ids", [])
            # Basic validation - could be enhanced with actual parsing
            for rule_id in rule_ids:
                if f"rule{rule_id}" not in v:
                    raise ValueError(f"Expression must reference rule{rule_id}")
        return v


class MLRuleParams(BaseModel):
    """
    Parameters for machine learning-based fraud detection rules.

    ML rules use trained models to assess transaction risk with confidence scores.
    For now, this will be mocked until the ML model module is implemented.
    """

    # Model configuration
    model_name: str = Field(
        "fraud_detection_model", description="Name of ML model to use"
    )
    model_version: Optional[str] = Field(None, description="Specific model version")

    # Feature configuration
    features: List[str] = Field(
        default_factory=list, description="List of features to extract from transaction"
    )
    feature_preprocessing: Dict[str, Any] = Field(
        default_factory=dict, description="Feature preprocessing parameters"
    )

    # Scoring thresholds
    confidence_threshold: float = Field(
        0.5, ge=0.0, le=1.0, description="Minimum confidence score for positive match"
    )

    # Model execution
    timeout_ms: int = Field(
        5000, gt=0, description="Model execution timeout in milliseconds"
    )
    fallback_behavior: str = Field(
        "allow", description="Behavior when model fails (allow/deny/skip)"
    )

    # Mock configuration (temporary)
    mock_mode: bool = Field(
        True, description="Use mock predictions instead of real model"
    )
    mock_confidence_range: tuple[float, float] = Field(
        (0.1, 0.9), description="Range for mock confidence scores"
    )


class RuleEvaluationRequest(BaseModel):
    """Request schema for evaluating rules against a transaction."""

    transaction_id: UUID = Field(description="ID of transaction to evaluate")
    rule_ids: Optional[List[int]] = Field(
        None, description="Specific rule IDs to evaluate (None = all active)"
    )
    correlation_id: str = Field(description="Correlation ID for tracking")

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

    rule_id: int = Field(description="ID of evaluated rule")
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
    correlation_id: str = Field(description="Request correlation ID")

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
    tags: Optional[Dict[str, Any]] = Field(None, description="Rule tags and metadata")

    @field_validator("params")
    def validate_params_match_type(cls, params, values):
        """Validate that params match the rule type."""
        rule_type = values.get("type")
        params = values.get("params")

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

        return values


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
    tags: Optional[Dict[str, Any]] = Field(None, description="Rule tags and metadata")


class RuleResponse(BaseModel):
    """Schema for rule API responses."""

    id: int = Field(description="Rule ID")
    name: str = Field(description="Rule name")
    type: RuleType = Field(description="Rule type")
    params: Dict[str, Any] = Field(description="Rule parameters")
    enabled: bool = Field(description="Whether rule is enabled")
    priority: int = Field(description="Rule priority")
    critical: bool = Field(description="Whether rule is critical")
    description: Optional[str] = Field(description="Rule description")
    version: Optional[str] = Field(description="Rule version")
    tags: Optional[Dict[str, Any]] = Field(description="Rule tags and metadata")

    # Statistics
    execution_count: int = Field(description="Total executions")
    match_count: int = Field(description="Total matches")
    match_rate: Optional[float] = Field(None, description="Match rate percentage")

    # Timestamps
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    last_executed_at: Optional[datetime] = Field(
        None, description="Last execution timestamp"
    )


class RuleListResponse(BaseModel):
    """Schema for paginated rule list responses."""

    rules: List[RuleResponse] = Field(description="List of rules")
    total: int = Field(description="Total number of rules")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of rules per page")
    pages: int = Field(description="Total number of pages")


class CacheStatusResponse(BaseModel):
    """Schema for rule cache status."""

    rule_id: int = Field(description="Rule ID")
    cache_key: str = Field(description="Redis cache key")
    status: CacheStatus = Field(description="Cache status")
    cached_at: Optional[datetime] = Field(None, description="Cache timestamp")
    expires_at: Optional[datetime] = Field(None, description="Cache expiration")
    hit_count: int = Field(description="Number of cache hits")
    cache_version: str = Field(description="Cached version")


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
