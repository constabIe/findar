"""
Rule Engine service for evaluating transactions against fraud detection rules.

This module provides the core logic for evaluating financial transactions
against various types of fraud detection rules (threshold, pattern, composite, ML).
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger
from redis.asyncio import Redis

from .enums import (
    RiskLevel,
    RuleMatchStatus,
    RuleType,
    TransactionStatus,
)
from .schemas import ThresholdRuleParams

# Redis key patterns
RULE_CACHE_KEY_PREFIX = "rule:"
ACTIVE_RULES_KEY = "active_rules:all"


class RuleEvaluationResult:
    """Result of evaluating a single rule against a transaction."""

    def __init__(
        self,
        rule_id: UUID,
        rule_name: str,
        rule_type: RuleType,
        matched: bool,
        confidence_score: float = 0.0,
        risk_level: RiskLevel = RiskLevel.LOW,
        execution_time_ms: float = 0.0,
        match_reason: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.rule_type = rule_type
        self.matched = matched
        self.confidence_score = confidence_score
        self.risk_level = risk_level
        self.execution_time_ms = execution_time_ms
        self.match_reason = match_reason
        self.error_message = error_message
        self.status = (
            RuleMatchStatus.MATCHED if matched else RuleMatchStatus.NOT_MATCHED
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "rule_id": str(self.rule_id),
            "rule_name": self.rule_name,
            "rule_type": self.rule_type.value,
            "matched": self.matched,
            "confidence_score": self.confidence_score,
            "risk_level": self.risk_level.value,
            "execution_time_ms": self.execution_time_ms,
            "match_reason": self.match_reason,
            "error_message": self.error_message,
            "status": self.status.value,
        }


class TransactionEvaluationResult:
    """Complete result of evaluating a transaction against all rules."""

    def __init__(
        self,
        transaction_id: UUID,
        correlation_id: str,
        total_rules_evaluated: int,
        matched_rules: List[RuleEvaluationResult],
        total_execution_time_ms: float,
        final_status: TransactionStatus,
        risk_level: RiskLevel,
    ):
        self.transaction_id = transaction_id
        self.correlation_id = correlation_id
        self.total_rules_evaluated = total_rules_evaluated
        self.matched_rules = matched_rules
        self.total_execution_time_ms = total_execution_time_ms
        self.final_status = final_status
        self.risk_level = risk_level
        self.has_critical_match = any(
            r.matched and r.risk_level == RiskLevel.CRITICAL for r in matched_rules
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "transaction_id": str(self.transaction_id),
            "correlation_id": self.correlation_id,
            "total_rules_evaluated": self.total_rules_evaluated,
            "matched_rules": [r.to_dict() for r in self.matched_rules],
            "total_execution_time_ms": self.total_execution_time_ms,
            "final_status": self.final_status.value,
            "risk_level": self.risk_level.value,
            "has_critical_match": self.has_critical_match,
        }


async def get_cached_active_rules(redis_client: Redis) -> List[Dict[str, Any]]:
    """
    Get active rules from Redis cache.

    If cache is empty or expired, returns empty list (caller should load from DB).

    Args:
        redis_client: Async Redis client

    Returns:
        List of rule dictionaries from cache
    """
    try:
        # Try to get cached active rules list
        cached_rules_key = ACTIVE_RULES_KEY
        cached_data = await redis_client.get(cached_rules_key)

        if cached_data:
            rules_list = json.loads(cached_data)
            logger.info(
                f"Retrieved {len(rules_list)} active rules from cache",
                event="cache_hit",
                count=len(rules_list),
            )
            return rules_list

        logger.warning("No active rules found in cache", event="cache_miss")
        return []

    except Exception as e:
        logger.error(
            f"Failed to get cached rules: {e}",
            event="cache_error",
            error=str(e),
        )
        return []


async def evaluate_transaction(
    transaction_data: Dict[str, Any],
    rules: List[Dict[str, Any]],
    correlation_id: str,
) -> TransactionEvaluationResult:
    """
    Evaluate a transaction against all active fraud detection rules.

    Args:
        transaction_data: Transaction data dictionary
        rules: List of active rule dictionaries
        correlation_id: Correlation ID for tracking

    Returns:
        TransactionEvaluationResult with all evaluation results
    """
    start_time = datetime.utcnow()
    transaction_id = UUID(transaction_data.get("id"))
    matched_rules: List[RuleEvaluationResult] = []
    total_rules = len(rules)

    logger.info(
        f"Starting transaction evaluation: {transaction_id}",
        event="evaluation_start",
        transaction_id=str(transaction_id),
        correlation_id=correlation_id,
        total_rules=total_rules,
    )

    # Sort rules by priority (higher priority first)
    sorted_rules = sorted(rules, key=lambda r: r.get("priority", 0), reverse=True)

    for rule_dict in sorted_rules:
        try:
            rule_start = datetime.utcnow()

            # Parse rule type
            rule_type = RuleType(rule_dict["type"])
            rule_id = UUID(rule_dict["id"])
            rule_name = rule_dict["name"]
            is_critical = rule_dict.get("critical", False)

            logger.debug(
                f"Evaluating rule: {rule_name} ({rule_type.value})",
                rule_id=str(rule_id),
                rule_type=rule_type.value,
                critical=is_critical,
            )

            # Evaluate based on rule type
            if rule_type == RuleType.THRESHOLD:
                result = await evaluate_threshold_rule(
                    transaction_data, rule_dict, rule_id, rule_name
                )
            elif rule_type == RuleType.PATTERN:
                result = await evaluate_pattern_rule(
                    transaction_data, rule_dict, rule_id, rule_name
                )
            elif rule_type == RuleType.COMPOSITE:
                result = await evaluate_composite_rule(
                    transaction_data, rule_dict, rule_id, rule_name
                )
            elif rule_type == RuleType.ML:
                result = await evaluate_ml_rule(
                    transaction_data, rule_dict, rule_id, rule_name
                )
            else:
                logger.warning(f"Unknown rule type: {rule_type}")
                continue

            # Calculate execution time
            rule_end = datetime.utcnow()
            result.execution_time_ms = (rule_end - rule_start).total_seconds() * 1000

            # If rule matched, add to results
            if result.matched:
                matched_rules.append(result)

                logger.info(
                    f"Rule MATCHED: {rule_name}",
                    event="rule_matched",
                    rule_id=str(rule_id),
                    rule_name=rule_name,
                    risk_level=result.risk_level.value,
                    critical=is_critical,
                    reason=result.match_reason,
                )

                # If critical rule matched, stop evaluation immediately
                if is_critical:
                    logger.warning(
                        f"CRITICAL rule matched: {rule_name} - stopping evaluation",
                        event="critical_rule_matched",
                        rule_id=str(rule_id),
                    )
                    break

        except Exception as e:
            logger.error(
                f"Error evaluating rule {rule_dict.get('name', 'unknown')}: {e}",
                event="rule_evaluation_error",
                error=str(e),
                rule_id=rule_dict.get("id"),
            )
            # Continue with other rules
            continue

    # Calculate total execution time
    end_time = datetime.utcnow()
    total_time_ms = (end_time - start_time).total_seconds() * 1000

    # Determine final status and risk level
    final_status, risk_level = _determine_final_status(matched_rules)

    logger.info(
        f"Transaction evaluation completed: {transaction_id}",
        event="evaluation_complete",
        transaction_id=str(transaction_id),
        total_rules_evaluated=total_rules,
        matched_rules_count=len(matched_rules),
        final_status=final_status.value,
        risk_level=risk_level.value,
        total_time_ms=total_time_ms,
    )

    return TransactionEvaluationResult(
        transaction_id=transaction_id,
        correlation_id=correlation_id,
        total_rules_evaluated=total_rules,
        matched_rules=matched_rules,
        total_execution_time_ms=total_time_ms,
        final_status=final_status,
        risk_level=risk_level,
    )


async def evaluate_threshold_rule(
    transaction_data: Dict[str, Any],
    rule_dict: Dict[str, Any],
    rule_id: UUID,
    rule_name: str,
) -> RuleEvaluationResult:
    """
    Evaluate a threshold-based rule against a transaction.

    Checks various thresholds like amount limits, frequency, time windows, etc.

    Args:
        transaction_data: Transaction data
        rule_dict: Rule configuration dictionary
        rule_id: Rule UUID
        rule_name: Rule name

    Returns:
        RuleEvaluationResult with evaluation outcome
    """
    params = ThresholdRuleParams(**rule_dict["params"])
    is_critical = rule_dict.get("critical", False)

    # Extract transaction fields
    amount = float(transaction_data.get("amount", 0))
    from_account = transaction_data.get("from_account", "")
    location = transaction_data.get("location")
    timestamp = datetime.fromisoformat(
        transaction_data.get("timestamp", datetime.utcnow().isoformat())
    )

    matched = False
    match_reason = None
    risk_level = RiskLevel.LOW

    # Check amount thresholds
    if params.max_amount is not None and amount > params.max_amount:
        matched = True
        match_reason = f"Amount {amount} exceeds maximum {params.max_amount}"
        risk_level = RiskLevel.HIGH if is_critical else RiskLevel.MEDIUM

    elif params.min_amount is not None and amount < params.min_amount:
        matched = True
        match_reason = f"Amount {amount} below minimum {params.min_amount}"
        risk_level = RiskLevel.MEDIUM

    # Check time window restrictions
    if params.allowed_hours_start is not None and params.allowed_hours_end is not None:
        current_hour = timestamp.hour
        if not (params.allowed_hours_start <= current_hour < params.allowed_hours_end):
            matched = True
            match_reason = f"Transaction at hour {current_hour} outside allowed window {params.allowed_hours_start}-{params.allowed_hours_end}"
            risk_level = RiskLevel.MEDIUM

    # Check location restrictions
    if params.allowed_locations and location:
        if location not in params.allowed_locations:
            matched = True
            match_reason = f"Location '{location}' not in allowed list"
            risk_level = RiskLevel.HIGH if is_critical else RiskLevel.MEDIUM

    # TODO: Implement frequency checks (requires historical data from Redis/DB)
    # - max_transactions_per_account
    # - max_transactions_to_account
    # - max_velocity_amount
    # - max_devices_per_account
    # - max_ips_per_account

    confidence_score = 0.8 if matched else 0.0

    if is_critical and matched:
        risk_level = RiskLevel.CRITICAL

    return RuleEvaluationResult(
        rule_id=rule_id,
        rule_name=rule_name,
        rule_type=RuleType.THRESHOLD,
        matched=matched,
        confidence_score=confidence_score,
        risk_level=risk_level,
        match_reason=match_reason,
    )


async def evaluate_pattern_rule(
    transaction_data: Dict[str, Any],
    rule_dict: Dict[str, Any],
    rule_id: UUID,
    rule_name: str,
) -> RuleEvaluationResult:
    """
    Evaluate a pattern-based rule against a transaction.

    Detects suspicious patterns like structuring, rapid succession, etc.

    TODO: Implement pattern detection logic
    - Structuring (multiple small transactions to avoid thresholds)
    - Rapid succession (many transactions in short time)
    - Round-trip transfers (A→B→A)
    - Unusual sequences

    Args:
        transaction_data: Transaction data
        rule_dict: Rule configuration dictionary
        rule_id: Rule UUID
        rule_name: Rule name

    Returns:
        RuleEvaluationResult with evaluation outcome
    """
    is_critical = rule_dict.get("critical", False)

    # TODO: Implement pattern detection
    # For now, return not matched
    logger.debug(
        f"Pattern rule evaluation not fully implemented: {rule_name}",
        rule_id=str(rule_id),
    )

    return RuleEvaluationResult(
        rule_id=rule_id,
        rule_name=rule_name,
        rule_type=RuleType.PATTERN,
        matched=False,
        confidence_score=0.0,
        risk_level=RiskLevel.LOW,
        match_reason="Pattern detection not yet implemented",
    )


async def evaluate_composite_rule(
    transaction_data: Dict[str, Any],
    rule_dict: Dict[str, Any],
    rule_id: UUID,
    rule_name: str,
) -> RuleEvaluationResult:
    """
    Evaluate a composite rule (combination of other rules with AND/OR/NOT logic).

    TODO: Implement composite rule evaluation
    - Load sub-rules
    - Apply logical operators
    - Aggregate results

    Args:
        transaction_data: Transaction data
        rule_dict: Rule configuration dictionary
        rule_id: Rule UUID
        rule_name: Rule name

    Returns:
        RuleEvaluationResult with evaluation outcome
    """
    is_critical = rule_dict.get("critical", False)

    # TODO: Implement composite logic
    logger.debug(
        f"Composite rule evaluation not fully implemented: {rule_name}",
        rule_id=str(rule_id),
    )

    return RuleEvaluationResult(
        rule_id=rule_id,
        rule_name=rule_name,
        rule_type=RuleType.COMPOSITE,
        matched=False,
        confidence_score=0.0,
        risk_level=RiskLevel.LOW,
        match_reason="Composite rules not yet implemented",
    )


async def evaluate_ml_rule(
    transaction_data: Dict[str, Any],
    rule_dict: Dict[str, Any],
    rule_id: UUID,
    rule_name: str,
) -> RuleEvaluationResult:
    """
    Evaluate an ML-based rule against a transaction.

    TODO: Implement ML model integration
    - Load trained model
    - Feature extraction
    - Risk scoring
    - Threshold comparison

    Args:
        transaction_data: Transaction data
        rule_dict: Rule configuration dictionary
        rule_id: Rule UUID
        rule_name: Rule name

    Returns:
        RuleEvaluationResult with evaluation outcome
    """
    is_critical = rule_dict.get("critical", False)

    # TODO: Implement ML model inference
    logger.debug(
        f"ML rule evaluation not fully implemented: {rule_name}",
        rule_id=str(rule_id),
    )

    return RuleEvaluationResult(
        rule_id=rule_id,
        rule_name=rule_name,
        rule_type=RuleType.ML,
        matched=False,
        confidence_score=0.0,
        risk_level=RiskLevel.LOW,
        match_reason="ML rules not yet implemented",
    )


def _determine_final_status(
    matched_rules: List[RuleEvaluationResult],
) -> tuple[TransactionStatus, RiskLevel]:
    """
    Determine final transaction status and risk level based on matched rules.

    Logic:
    - If any CRITICAL rule matched → FAILED
    - If any HIGH/MEDIUM rule matched → FLAGGED
    - If no rules matched → APPROVED

    Args:
        matched_rules: List of matched rule results

    Returns:
        Tuple of (TransactionStatus, RiskLevel)
    """
    if not matched_rules:
        return TransactionStatus.APPROVED, RiskLevel.LOW

    # Check for critical risk
    has_critical = any(r.risk_level == RiskLevel.CRITICAL for r in matched_rules)
    if has_critical:
        return TransactionStatus.FAILED, RiskLevel.CRITICAL

    # Check for high risk
    has_high = any(r.risk_level == RiskLevel.HIGH for r in matched_rules)
    if has_high:
        return TransactionStatus.FLAGGED, RiskLevel.HIGH

    # Check for medium risk
    has_medium = any(r.risk_level == RiskLevel.MEDIUM for r in matched_rules)
    if has_medium:
        return TransactionStatus.FLAGGED, RiskLevel.MEDIUM

    # Low risk
    return TransactionStatus.FLAGGED, RiskLevel.LOW
