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

from src.modules.reporting.metrics import (
    increment_rule_evaluated_counter,
    increment_rule_matched_counter,
    observe_rule_execution_time,
)

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

    Rules are stored in Redis as:
    - SET 'active_rules:all' contains rule IDs
    - STRING 'rule:<rule_id>' contains rule JSON data

    If cache is empty or expired, returns empty list (caller should load from DB).

    Args:
        redis_client: Async Redis client

    Returns:
        List of rule dictionaries from cache
    """
    try:
        # Get all active rule IDs from SET
        cached_rules_key = ACTIVE_RULES_KEY
        rule_ids = await redis_client.smembers(cached_rules_key)  # type: ignore

        if not rule_ids:
            logger.warning("No active rules found in cache", event="cache_miss")
            return []

        # Fetch each rule's data from cache
        rules_list = []
        for rule_id_bytes in rule_ids:
            rule_id = None
            try:
                rule_id = (
                    rule_id_bytes.decode("utf-8")
                    if isinstance(rule_id_bytes, bytes)
                    else str(rule_id_bytes)
                )
                rule_cache_key = f"{RULE_CACHE_KEY_PREFIX}{rule_id}"

                # Get rule data
                rule_data = await redis_client.get(rule_cache_key)

                if rule_data:
                    rule_dict = json.loads(rule_data)
                    rules_list.append(rule_dict)
                else:
                    logger.warning(
                        f"Rule {rule_id} in active set but not in cache",
                        rule_id=rule_id,
                        event="cache_inconsistency",
                    )
            except Exception as e:
                logger.error(
                    f"Failed to load rule from cache: {e}",
                    rule_id=rule_id or "unknown",
                    error=str(e),
                )
                continue

        logger.info(
            f"Retrieved {len(rules_list)} active rules from cache",
            event="cache_hit",
            count=len(rules_list),
            total_ids=len(rule_ids),
        )

        return rules_list

    except Exception as e:
        logger.error(
            f"Failed to get cached rules: {e}",
            event="cache_error",
            error=str(e),
        )
        return []


async def get_rule_by_name(
    redis_client: Redis, rule_name: str
) -> Optional[Dict[str, Any]]:
    """
    Find a rule by its name in Redis cache.

    This function searches through all active rules in the cache to find
    a rule with the matching name. Used by composite rules to resolve
    sub-rule references.

    Args:
        redis_client: Async Redis client
        rule_name: Name of the rule to find

    Returns:
        Rule dictionary if found, None otherwise
    """
    try:
        # Get all active rule IDs from SET
        rule_ids = await redis_client.smembers(ACTIVE_RULES_KEY)  # type: ignore

        if not rule_ids:
            logger.warning(
                f"No active rules in cache when searching for '{rule_name}'",
                event="cache_empty",
                rule_name=rule_name,
            )
            return None

        # Search through each rule
        for rule_id_bytes in rule_ids:
            try:
                rule_id = (
                    rule_id_bytes.decode("utf-8")
                    if isinstance(rule_id_bytes, bytes)
                    else str(rule_id_bytes)
                )
                rule_cache_key = f"{RULE_CACHE_KEY_PREFIX}{rule_id}"

                # Get rule data
                rule_data = await redis_client.get(rule_cache_key)

                if rule_data:
                    rule_dict = json.loads(rule_data)

                    # Check if name matches
                    if rule_dict.get("name") == rule_name:
                        logger.debug(
                            f"Found rule by name: {rule_name}",
                            rule_id=rule_id,
                            rule_name=rule_name,
                        )
                        return rule_dict

            except Exception as e:
                logger.error(
                    f"Error checking rule {rule_id}: {e}",
                    rule_id=rule_id,
                    error=str(e),
                )
                continue

        logger.warning(
            f"Rule not found by name: {rule_name}",
            event="rule_not_found",
            rule_name=rule_name,
        )
        return None

    except Exception as e:
        logger.error(
            f"Failed to search for rule by name: {e}",
            event="search_error",
            rule_name=rule_name,
            error=str(e),
        )
        return None


async def evaluate_transaction(
    transaction_data: Dict[str, Any],
    rules: List[Dict[str, Any]],
    correlation_id: str,
    redis_client: Optional[Redis] = None,
    max_composite_depth: int = 5,
) -> TransactionEvaluationResult:
    """
    Evaluate a transaction against all active fraud detection rules.

    Args:
        transaction_data: Transaction data dictionary
        rules: List of active rule dictionaries
        correlation_id: Correlation ID for tracking
        redis_client: Optional async Redis client for frequency checks
        max_composite_depth: Maximum recursion depth for composite rules (default: 5)

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
                correlation_id=correlation_id,
            )

            # Evaluate based on rule type
            if rule_type == RuleType.THRESHOLD:
                result = await evaluate_threshold_rule(
                    transaction_data, rule_dict, rule_id, rule_name, redis_client
                )
            elif rule_type == RuleType.PATTERN:
                result = await evaluate_pattern_rule(
                    transaction_data, rule_dict, rule_id, rule_name, redis_client
                )
            elif rule_type == RuleType.COMPOSITE:
                result = await evaluate_composite_rule(
                    transaction_data,
                    rule_dict,
                    rule_id,
                    rule_name,
                    redis_client,
                    max_depth=max_composite_depth,
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

            # Record Prometheus metrics
            increment_rule_evaluated_counter(rule_type=rule_type.value)
            observe_rule_execution_time(
                rule_type=rule_type.value,
                duration_seconds=result.execution_time_ms / 1000.0,
            )

            # If rule matched, add to results
            if result.matched:
                matched_rules.append(result)

                # Record matched rule metric
                increment_rule_matched_counter(
                    rule_type=rule_type.value, rule_id=str(rule_id)
                )

                logger.info(
                    f"Rule MATCHED: {rule_name}",
                    event="rule_matched",
                    rule_id=str(rule_id),
                    rule_name=rule_name,
                    rule_type=rule_type.value,
                    risk_level=result.risk_level.value,
                    critical=is_critical,
                    reason=result.match_reason,
                    correlation_id=correlation_id,
                )

                # If critical rule matched, stop evaluation immediately
                if is_critical:
                    logger.warning(
                        f"CRITICAL rule matched: {rule_name} - stopping evaluation",
                        event="critical_rule_matched",
                        rule_id=str(rule_id),
                        correlation_id=correlation_id,
                    )
                    break

        except Exception as e:
            logger.error(
                f"Error evaluating rule {rule_dict.get('name', 'unknown')}: {e}",
                event="rule_evaluation_error",
                error=str(e),
                rule_id=rule_dict.get("id"),
                correlation_id=correlation_id,
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
        correlation_id=correlation_id,
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
    redis_client: Optional[Redis] = None,
) -> RuleEvaluationResult:
    """
    Evaluate a threshold-based rule against a transaction.

    Checks various thresholds like amount limits, frequency, time windows, etc.

    Args:
        transaction_data: Transaction data
        rule_dict: Rule configuration dictionary
        rule_id: Rule UUID
        rule_name: Rule name
        redis_client: Optional async Redis client for frequency checks

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

    # DEBUG: Log all values for troubleshooting
    logger.debug(
        "THRESHOLD RULE EVALUATION DEBUG",
        rule_id=str(rule_id),
        rule_name=rule_name,
        transaction_amount=amount,
        transaction_amount_type=type(amount).__name__,
        rule_max_amount=params.max_amount,
        rule_max_amount_type=type(params.max_amount).__name__
        if params.max_amount
        else None,
        rule_min_amount=params.min_amount,
        is_critical=is_critical,
        transaction_data_amount_raw=transaction_data.get("amount"),
    )

    matched = False
    match_reason = None
    risk_level = RiskLevel.LOW

    # Check amount thresholds with operator support
    if params.max_amount is not None or params.min_amount is not None:
        from .enums import ThresholdOperator

        amount_matched = False

        # Apply operator logic
        if params.operator == ThresholdOperator.GREATER_THAN:
            # amount > max_amount
            if params.max_amount is not None and amount > params.max_amount:
                amount_matched = True
                match_reason = f"Amount {amount} > {params.max_amount}"

        elif params.operator == ThresholdOperator.GREATER_EQUAL:
            # amount >= max_amount
            if params.max_amount is not None and amount >= params.max_amount:
                amount_matched = True
                match_reason = f"Amount {amount} >= {params.max_amount}"

        elif params.operator == ThresholdOperator.LESS_THAN:
            # amount < min_amount (for detecting suspiciously small transactions)
            if params.min_amount is not None and amount < params.min_amount:
                amount_matched = True
                match_reason = f"Amount {amount} < {params.min_amount}"
            elif params.max_amount is not None and amount < params.max_amount:
                amount_matched = True
                match_reason = f"Amount {amount} < {params.max_amount}"

        elif params.operator == ThresholdOperator.LESS_EQUAL:
            # amount <= min_amount
            if params.min_amount is not None and amount <= params.min_amount:
                amount_matched = True
                match_reason = f"Amount {amount} <= {params.min_amount}"
            elif params.max_amount is not None and amount <= params.max_amount:
                amount_matched = True
                match_reason = f"Amount {amount} <= {params.max_amount}"

        elif params.operator == ThresholdOperator.EQUAL:
            # amount == target
            target = (
                params.max_amount
                if params.max_amount is not None
                else params.min_amount
            )
            if target is not None and amount == target:
                amount_matched = True
                match_reason = f"Amount {amount} == {target}"

        elif params.operator == ThresholdOperator.NOT_EQUAL:
            # amount != target
            target = (
                params.max_amount
                if params.max_amount is not None
                else params.min_amount
            )
            if target is not None and amount != target:
                amount_matched = True
                match_reason = f"Amount {amount} != {target}"

        elif params.operator == ThresholdOperator.BETWEEN:
            # min_amount <= amount <= max_amount
            if params.min_amount is not None and params.max_amount is not None:
                if params.min_amount <= amount <= params.max_amount:
                    amount_matched = True
                    match_reason = f"Amount {amount} in range [{params.min_amount}, {params.max_amount}]"

        elif params.operator == ThresholdOperator.NOT_BETWEEN:
            # amount < min_amount OR amount > max_amount
            if params.min_amount is not None and params.max_amount is not None:
                if amount < params.min_amount or amount > params.max_amount:
                    amount_matched = True
                    match_reason = f"Amount {amount} outside range [{params.min_amount}, {params.max_amount}]"

        if amount_matched:
            matched = True
            risk_level = RiskLevel.HIGH if is_critical else RiskLevel.MEDIUM

            logger.info(
                "THRESHOLD RULE MATCHED: Amount check",
                rule_name=rule_name,
                amount=amount,
                operator=params.operator.value,
                max_amount=params.max_amount,
                min_amount=params.min_amount,
                match_reason=match_reason,
            )

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

    # 🆕 FREQUENCY CHECKS (using Redis)
    # Note: We check frequency REGARDLESS of other matches to track violations
    if redis_client and params.time_window is not None:
        from src.storage.redis.frequency import (
            get_to_account_count,
            get_transaction_count,
            get_unique_devices_count,
            get_unique_ips_count,
            get_unique_types_count,
            get_velocity,
        )

        try:
            # Check max_transactions_per_account
            if not matched and params.max_transactions_per_account is not None:
                current_count = await get_transaction_count(
                    redis=redis_client,
                    account_id=from_account,
                    time_window=params.time_window,
                )

                if current_count > params.max_transactions_per_account:
                    matched = True
                    match_reason = (
                        f"Transaction count {current_count} exceeds limit "
                        f"{params.max_transactions_per_account} in {params.time_window.value}"
                    )
                    risk_level = RiskLevel.HIGH if is_critical else RiskLevel.MEDIUM

                    logger.warning(
                        "FREQUENCY VIOLATION: max_transactions_per_account",
                        rule_name=rule_name,
                        from_account=from_account,
                        current_count=current_count,
                        limit=params.max_transactions_per_account,
                        time_window=params.time_window.value,
                    )

            # Check max_transactions_to_account
            if not matched and params.max_transactions_to_account is not None:
                to_account = transaction_data.get("to_account", "")
                current_count = await get_to_account_count(
                    redis=redis_client,
                    to_account_id=to_account,
                    time_window=params.time_window,
                )

                if current_count > params.max_transactions_to_account:
                    matched = True
                    match_reason = (
                        f"Transactions to account {current_count} exceeds limit "
                        f"{params.max_transactions_to_account} in {params.time_window.value}"
                    )
                    risk_level = RiskLevel.MEDIUM

                    logger.warning(
                        "FREQUENCY VIOLATION: max_transactions_to_account",
                        rule_name=rule_name,
                        to_account=to_account,
                        current_count=current_count,
                        limit=params.max_transactions_to_account,
                    )

            # Check max_velocity_amount (total amount in time window)
            if not matched and params.max_velocity_amount is not None:
                current_velocity = await get_velocity(
                    redis=redis_client,
                    account_id=from_account,
                    time_window=params.time_window,
                )

                if current_velocity > params.max_velocity_amount:
                    matched = True
                    match_reason = (
                        f"Velocity ${current_velocity:.2f} exceeds limit "
                        f"${params.max_velocity_amount:.2f} in {params.time_window.value}"
                    )
                    risk_level = RiskLevel.HIGH if is_critical else RiskLevel.MEDIUM

                    logger.warning(
                        "FREQUENCY VIOLATION: max_velocity_amount",
                        rule_name=rule_name,
                        from_account=from_account,
                        current_velocity=current_velocity,
                        limit=params.max_velocity_amount,
                    )

            # Check max_devices_per_account
            if not matched and params.max_devices_per_account is not None:
                device_count = await get_unique_devices_count(
                    redis=redis_client,
                    account_id=from_account,
                    time_window=params.time_window,
                )

                if device_count > params.max_devices_per_account:
                    matched = True
                    match_reason = (
                        f"Unique devices {device_count} exceeds limit "
                        f"{params.max_devices_per_account} in {params.time_window.value}"
                    )
                    risk_level = RiskLevel.HIGH

                    logger.warning(
                        "FREQUENCY VIOLATION: max_devices_per_account",
                        rule_name=rule_name,
                        from_account=from_account,
                        device_count=device_count,
                        limit=params.max_devices_per_account,
                    )

            # Check max_ips_per_account
            if not matched and params.max_ips_per_account is not None:
                ip_count = await get_unique_ips_count(
                    redis=redis_client,
                    account_id=from_account,
                    time_window=params.time_window,
                )

                if ip_count > params.max_ips_per_account:
                    matched = True
                    match_reason = (
                        f"Unique IPs {ip_count} exceeds limit "
                        f"{params.max_ips_per_account} in {params.time_window.value}"
                    )
                    risk_level = RiskLevel.HIGH

                    logger.warning(
                        "FREQUENCY VIOLATION: max_ips_per_account",
                        rule_name=rule_name,
                        from_account=from_account,
                        ip_count=ip_count,
                        limit=params.max_ips_per_account,
                    )

            # Check max_transaction_types
            if not matched and params.max_transaction_types is not None:
                types_count = await get_unique_types_count(
                    redis=redis_client,
                    account_id=from_account,
                    time_window=params.time_window,
                )

                if types_count > params.max_transaction_types:
                    matched = True
                    match_reason = (
                        f"Unique transaction types {types_count} exceeds limit "
                        f"{params.max_transaction_types} in {params.time_window.value}"
                    )
                    risk_level = RiskLevel.MEDIUM

                    logger.warning(
                        "FREQUENCY VIOLATION: max_transaction_types",
                        rule_name=rule_name,
                        from_account=from_account,
                        types_count=types_count,
                        limit=params.max_transaction_types,
                    )

        except Exception as e:
            logger.error(
                f"Error during frequency checks for rule {rule_name}: {e}",
                event="frequency_check_error",
                rule_name=rule_name,
                error=str(e),
            )
            # Don't fail the rule evaluation if frequency checks fail

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
    redis_client: Optional[Redis] = None,
) -> RuleEvaluationResult:
    """
    Evaluate a pattern-based rule against a transaction.

    Analyzes transaction patterns over time to detect suspicious behavior like:
    - Structuring (multiple small transactions to avoid thresholds)
    - Rapid succession (many transactions in short time)
    - Unusual recipient patterns
    - Device-based velocity patterns

    Args:
        transaction_data: Transaction data
        rule_dict: Rule configuration dictionary
        rule_id: Rule UUID
        rule_name: Rule name
        redis_client: Optional async Redis client for pattern data

    Returns:
        RuleEvaluationResult with evaluation outcome
    """
    from .schemas import PatternRuleParams

    is_critical = rule_dict.get("critical", False)
    params = PatternRuleParams(**rule_dict["params"])

    # Extract transaction fields
    from_account = transaction_data.get("from_account", "")

    # Pattern rules require Redis for historical data
    if not redis_client:
        logger.warning(
            "Pattern rule evaluation skipped - Redis client not available",
            rule_id=str(rule_id),
            rule_name=rule_name,
        )
        return RuleEvaluationResult(
            rule_id=rule_id,
            rule_name=rule_name,
            rule_type=RuleType.PATTERN,
            matched=False,
            confidence_score=0.0,
            risk_level=RiskLevel.LOW,
            match_reason="Redis not available for pattern analysis",
        )

    try:
        from src.storage.redis.pattern import (
            analyze_amount_pattern,
            analyze_device_pattern,
            analyze_recipient_pattern,
            get_transactions_in_window,
        )

        # Get historical transactions in time window
        transactions = await get_transactions_in_window(
            redis=redis_client,
            account_id=from_account,
            time_window=params.period,
        )

        matched = False
        match_reason = None
        risk_level = RiskLevel.LOW

        # Check 1: Transaction count
        if params.count is not None:
            if len(transactions) >= params.count:
                matched = True
                match_reason = f"Transaction count {len(transactions)} >= {params.count} in {params.period.value}"
                risk_level = RiskLevel.MEDIUM

                logger.info(
                    "PATTERN MATCHED: Transaction count threshold",
                    rule_name=rule_name,
                    count=len(transactions),
                    threshold=params.count,
                    period=params.period.value,
                )

        # Check 2: Amount ceiling
        if not matched and params.amount_ceiling is not None:
            amount_analysis = await analyze_amount_pattern(transactions)
            total_amount = amount_analysis["total_amount"]

            if total_amount >= params.amount_ceiling:
                matched = True
                match_reason = f"Total amount ${total_amount:.2f} >= ${params.amount_ceiling:.2f} in {params.period.value}"
                risk_level = RiskLevel.HIGH if is_critical else RiskLevel.MEDIUM

                logger.info(
                    "PATTERN MATCHED: Amount ceiling exceeded",
                    rule_name=rule_name,
                    total_amount=total_amount,
                    ceiling=params.amount_ceiling,
                    txn_count=len(transactions),
                )

        # Check 3: Same recipient pattern
        if not matched and params.same_recipient:
            recipient_analysis = await analyze_recipient_pattern(transactions)

            if not recipient_analysis["all_same_recipient"] and len(transactions) > 0:
                # Rule requires same recipient but transactions go to different recipients
                matched = True
                match_reason = (
                    f"Transactions to {recipient_analysis['unique_recipients']} different recipients "
                    f"(expected same recipient)"
                )
                risk_level = RiskLevel.MEDIUM

                logger.info(
                    "PATTERN MATCHED: Same recipient violation",
                    rule_name=rule_name,
                    unique_recipients=recipient_analysis["unique_recipients"],
                    recipients=recipient_analysis["recipients"],
                )

        # Check 4: Unique recipients limit
        if not matched and params.unique_recipients is not None:
            recipient_analysis = await analyze_recipient_pattern(transactions)

            if recipient_analysis["unique_recipients"] > params.unique_recipients:
                matched = True
                match_reason = (
                    f"Unique recipients {recipient_analysis['unique_recipients']} > "
                    f"{params.unique_recipients} in {params.period.value}"
                )
                risk_level = RiskLevel.HIGH if is_critical else RiskLevel.MEDIUM

                logger.info(
                    "PATTERN MATCHED: Too many unique recipients",
                    rule_name=rule_name,
                    unique_recipients=recipient_analysis["unique_recipients"],
                    limit=params.unique_recipients,
                )

        # Check 5: Same device pattern
        if not matched and params.same_device:
            device_analysis = await analyze_device_pattern(transactions)

            if not device_analysis["all_same_device"] and len(transactions) > 0:
                matched = True
                match_reason = (
                    f"Transactions from {device_analysis['unique_devices']} different devices "
                    f"(expected same device)"
                )
                risk_level = RiskLevel.MEDIUM

                logger.info(
                    "PATTERN MATCHED: Same device violation",
                    rule_name=rule_name,
                    unique_devices=device_analysis["unique_devices"],
                )

        # Check 6: Device velocity limit
        if not matched and params.velocity_limit is not None:
            device_analysis = await analyze_device_pattern(transactions)
            max_velocity = device_analysis["max_device_velocity"]

            if max_velocity >= params.velocity_limit:
                matched = True
                match_reason = (
                    f"Device velocity ${max_velocity:.2f} >= "
                    f"${params.velocity_limit:.2f} in {params.period.value}"
                )
                risk_level = RiskLevel.HIGH if is_critical else RiskLevel.MEDIUM

                logger.info(
                    "PATTERN MATCHED: Device velocity exceeded",
                    rule_name=rule_name,
                    max_velocity=max_velocity,
                    limit=params.velocity_limit,
                    device_velocities=device_analysis["device_velocities"],
                )

        # Set confidence score and final risk level
        confidence_score = 0.85 if matched else 0.0
        if is_critical and matched:
            risk_level = RiskLevel.CRITICAL

        if matched:
            logger.info(
                "Pattern rule MATCHED",
                rule_id=str(rule_id),
                rule_name=rule_name,
                match_reason=match_reason,
                risk_level=risk_level.value,
                transactions_analyzed=len(transactions),
            )

        return RuleEvaluationResult(
            rule_id=rule_id,
            rule_name=rule_name,
            rule_type=RuleType.PATTERN,
            matched=matched,
            confidence_score=confidence_score,
            risk_level=risk_level,
            match_reason=match_reason,
        )

    except Exception as e:
        logger.error(
            f"Error evaluating pattern rule {rule_name}: {e}",
            rule_id=str(rule_id),
            error=str(e),
            event="pattern_evaluation_error",
        )

        return RuleEvaluationResult(
            rule_id=rule_id,
            rule_name=rule_name,
            rule_type=RuleType.PATTERN,
            matched=False,
            confidence_score=0.0,
            risk_level=RiskLevel.LOW,
            error_message=f"Pattern evaluation failed: {str(e)}",
        )


async def evaluate_composite_rule(
    transaction_data: Dict[str, Any],
    rule_dict: Dict[str, Any],
    rule_id: UUID,
    rule_name: str,
    redis_client: Redis,
    max_depth: int = 5,
    current_depth: int = 0,
) -> RuleEvaluationResult:
    """
    Evaluate a composite rule (combination of other rules with AND/OR/NOT logic).

    This function recursively evaluates sub-rules (referenced by name) and applies
    logical operators:
    - AND: all sub-rules must match
    - OR: at least one sub-rule must match
    - NOT: applies NOT to all rules using OR - NOT(rule1 OR rule2 OR ...)
      Returns True if NONE of the rules match.

    Sub-rules are referenced by their unique names (not UUIDs) and are loaded from
    Redis cache using the get_rule_by_name() function. Sub-rules are evaluated
    regardless of their is_active status - composite rules work with any referenced rule.

    Aggregation strategy:
    - AND: confidence = min(all), risk = max(all)
    - OR: confidence = max(all), risk = max(all)
    - NOT: confidence = 1.0 - max(all), risk = unchanged

    Note: Circular dependency protection is not yet implemented.
    TODO: Add tracking of evaluated_rule_ids to prevent infinite recursion loops.

    Args:
        transaction_data: Transaction data
        rule_dict: Rule configuration dictionary (parameters.rules should contain rule names)
        rule_id: Rule UUID
        rule_name: Rule name
        redis_client: Async Redis client for loading sub-rules by name
        max_depth: Maximum recursion depth allowed (default: 5)
        current_depth: Current recursion depth (internal use)

    Returns:
        RuleEvaluationResult with evaluation outcome
    """
    from .enums import CompositeOperator
    from .schemas import CompositeRuleParams

    is_critical = rule_dict.get("critical", False)

    # Check recursion depth limit
    if current_depth >= max_depth:
        logger.error(
            f"Composite rule {rule_name} exceeded max depth {max_depth}",
            event="max_depth_exceeded",
            rule_id=str(rule_id),
            current_depth=current_depth,
            max_depth=max_depth,
        )
        return RuleEvaluationResult(
            rule_id=rule_id,
            rule_name=rule_name,
            rule_type=RuleType.COMPOSITE,
            matched=False,
            confidence_score=0.0,
            risk_level=RiskLevel.LOW,
            error_message=f"Max recursion depth ({max_depth}) exceeded",
        )

    try:
        # Parse composite rule parameters
        params_dict = rule_dict.get("parameters", {})
        params = CompositeRuleParams(**params_dict)

        operator = params.operator
        sub_rule_names = params.rules

        logger.debug(
            f"Evaluating composite rule: {rule_name}",
            event="composite_evaluation_start",
            rule_id=str(rule_id),
            operator=operator.value,
            sub_rules_count=len(sub_rule_names),
            sub_rule_names=sub_rule_names,
            depth=current_depth,
        )

        # Load and evaluate all sub-rules
        sub_results: List[RuleEvaluationResult] = []

        for sub_rule_name in sub_rule_names:
            # Load sub-rule by name from Redis cache
            sub_rule_dict = await get_rule_by_name(redis_client, sub_rule_name)

            if not sub_rule_dict:
                logger.warning(
                    f"Sub-rule '{sub_rule_name}' not found in cache, skipping",
                    event="sub_rule_not_found",
                    composite_rule_id=str(rule_id),
                    sub_rule_name=sub_rule_name,
                )
                # Skip only if rule doesn't exist (not found in cache)
                continue

            # Extract sub-rule metadata
            # Note: We evaluate sub-rules regardless of their is_active status
            # because composite rules should work with any referenced rule
            sub_rule_id = UUID(sub_rule_dict.get("id"))
            sub_rule_type = RuleType(sub_rule_dict.get("rule_type"))
            actual_sub_rule_name = sub_rule_dict.get("name", sub_rule_name)
            is_active = sub_rule_dict.get("is_active", False)

            logger.debug(
                f"Evaluating sub-rule '{sub_rule_name}'",
                event="sub_rule_evaluation",
                sub_rule_name=sub_rule_name,
                sub_rule_id=str(sub_rule_id),
                sub_rule_type=sub_rule_type.value,
                is_active=is_active,
            )

            # Recursively evaluate sub-rule based on type
            if sub_rule_type == RuleType.THRESHOLD:
                sub_result = await evaluate_threshold_rule(
                    transaction_data,
                    sub_rule_dict,
                    sub_rule_id,
                    actual_sub_rule_name,
                    redis_client,
                )
            elif sub_rule_type == RuleType.PATTERN:
                sub_result = await evaluate_pattern_rule(
                    transaction_data,
                    sub_rule_dict,
                    sub_rule_id,
                    actual_sub_rule_name,
                    redis_client,
                )
            elif sub_rule_type == RuleType.COMPOSITE:
                # Recursive call with incremented depth
                sub_result = await evaluate_composite_rule(
                    transaction_data,
                    sub_rule_dict,
                    sub_rule_id,
                    actual_sub_rule_name,
                    redis_client,
                    max_depth=max_depth,
                    current_depth=current_depth + 1,
                )
            elif sub_rule_type == RuleType.ML:
                sub_result = await evaluate_ml_rule(
                    transaction_data,
                    sub_rule_dict,
                    sub_rule_id,
                    actual_sub_rule_name,
                )
            else:
                logger.warning(
                    f"Unknown sub-rule type: {sub_rule_type}",
                    sub_rule_name=sub_rule_name,
                    sub_rule_type=sub_rule_type,
                )
                continue

            sub_results.append(sub_result)

        # If no sub-rules were evaluated, return no match
        if not sub_results:
            logger.warning(
                f"No valid sub-rules found for composite rule {rule_name}",
                event="no_sub_rules",
                rule_id=str(rule_id),
            )
            return RuleEvaluationResult(
                rule_id=rule_id,
                rule_name=rule_name,
                rule_type=RuleType.COMPOSITE,
                matched=False,
                confidence_score=0.0,
                risk_level=RiskLevel.LOW,
                match_reason="No valid sub-rules to evaluate",
            )

        # Apply logical operator
        matched_sub_rules = [r for r in sub_results if r.matched]
        all_confidences = [r.confidence_score for r in sub_results]
        all_risk_levels = [r.risk_level for r in sub_results]

        if operator == CompositeOperator.AND:
            # All sub-rules must match
            matched = len(matched_sub_rules) == len(sub_results)
            confidence_score = min(all_confidences) if matched else 0.0
            risk_level = max(all_risk_levels, key=lambda r: _risk_level_value(r))
            match_reason = (
                f"AND: All {len(sub_results)} sub-rules matched"
                if matched
                else f"AND: Only {len(matched_sub_rules)}/{len(sub_results)} sub-rules matched"
            )

        elif operator == CompositeOperator.OR:
            # At least one sub-rule must match
            matched = len(matched_sub_rules) > 0
            confidence_score = max(all_confidences) if matched else 0.0
            risk_level = max(all_risk_levels, key=lambda r: _risk_level_value(r))
            match_reason = (
                f"OR: {len(matched_sub_rules)}/{len(sub_results)} sub-rules matched"
                if matched
                else f"OR: None of {len(sub_results)} sub-rules matched"
            )

        elif operator == CompositeOperator.NOT:
            # NOT(rule1 OR rule2 OR ...) - True if NONE match
            matched = len(matched_sub_rules) == 0
            confidence_score = 1.0 - max(all_confidences) if matched else 0.0
            risk_level = max(all_risk_levels, key=lambda r: _risk_level_value(r))
            match_reason = (
                f"NOT: None of {len(sub_results)} sub-rules matched (as expected)"
                if matched
                else f"NOT: {len(matched_sub_rules)} sub-rules matched (violation)"
            )

        else:
            logger.error(f"Unknown composite operator: {operator}")
            matched = False
            confidence_score = 0.0
            risk_level = RiskLevel.LOW
            match_reason = f"Unknown operator: {operator}"

        logger.info(
            f"Composite rule evaluation complete: {rule_name}",
            event="composite_evaluation_complete",
            rule_id=str(rule_id),
            operator=operator.value,
            matched=matched,
            sub_results_count=len(sub_results),
            matched_count=len(matched_sub_rules),
        )

        return RuleEvaluationResult(
            rule_id=rule_id,
            rule_name=rule_name,
            rule_type=RuleType.COMPOSITE,
            matched=matched,
            confidence_score=confidence_score,
            risk_level=risk_level,
            match_reason=match_reason,
        )

    except Exception as e:
        logger.error(
            f"Error evaluating composite rule {rule_name}: {e}",
            event="composite_evaluation_error",
            rule_id=str(rule_id),
            error=str(e),
        )
        return RuleEvaluationResult(
            rule_id=rule_id,
            rule_name=rule_name,
            rule_type=RuleType.COMPOSITE,
            matched=False,
            confidence_score=0.0,
            risk_level=RiskLevel.LOW,
            error_message=f"Composite evaluation failed: {str(e)}",
        )


def _risk_level_value(risk: RiskLevel) -> int:
    """Helper function to convert RiskLevel to numeric value for comparison."""
    risk_values = {
        RiskLevel.LOW: 1,
        RiskLevel.MEDIUM: 2,
        RiskLevel.HIGH: 3,
        RiskLevel.CRITICAL: 4,
    }
    return risk_values.get(risk, 0)


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
