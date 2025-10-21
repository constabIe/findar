"""
Repository layer for rule engine operations.

Provides CRUD operations for rules with dual storage (PostgreSQL + Redis).
Ensures consistency between database and cache during all operations.
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID

from redis import Redis as SyncRedis
from sqlalchemy import desc, select

from src.core.exceptions import (
    DatabaseError,
    ValidationError,
)
from src.core.logging import get_logger
from src.storage.dependencies import AsyncRedisDep, DbSessionDep
from src.storage.models import Rule, RuleExecution

from .enums import RuleType
from .schemas import (
    RuleCreateRequest,
    RuleUpdateRequest,
)

logger = get_logger("rule_engine.repository")

# Redis key patterns
RULE_CACHE_KEY_PREFIX = "rule:"
ACTIVE_RULES_KEY = "active_rules:all"
RULE_TYPE_KEY_PREFIX = "rules:type:"
RULE_INDEX_KEY = "rule_index"  # Sorted set of rule IDs by priority


class RuleRepository:
    """
    Repository for rule CRUD operations with dual storage management.

    Manages rules in PostgreSQL (persistent storage) and Redis (cache).
    Ensures data consistency across both storage systems.
    """

    def __init__(
        self,
        db_session: DbSessionDep,
        async_redis: AsyncRedisDep,
        sync_redis: Optional[SyncRedis] = None,
    ):
        """
        Initialize repository with database and cache clients.

        Args:
            db_session: SQLModel async database session
            async_redis: Async Redis client for cache operations
            sync_redis: Optional sync Redis client for Celery compatibility
        """
        self.db = db_session
        self.async_redis = async_redis
        self.sync_redis = sync_redis
        self.cache_ttl = 3600  # 1 hour default TTL

    async def create_rule(
        self, create_request: RuleCreateRequest, created_by: Optional[str] = None
    ) -> Rule:
        """
        Create a new fraud detection rule.

        Creates rule in PostgreSQL and adds to Redis cache if enabled.

        Args:
            create_request: Rule creation request with parameters
            created_by: User creating the rule (for audit)

        Returns:
            Created Rule instance

        Raises:
            ValidationError: If rule name already exists
            DatabaseError: If database operation fails
        """
        try:
            # Check if rule with same name exists
            existing = await self._get_rule_by_name(create_request.name)
            if existing:
                raise ValidationError(
                    f"Rule with name '{create_request.name}' already exists",
                    field="name",
                    value=create_request.name,
                )

            # Create rule instance
            rule = Rule(
                name=create_request.name,
                type=create_request.type,
                params=create_request.params.dict(),
                enabled=create_request.enabled,
                priority=create_request.priority,
                critical=create_request.critical,
                description=create_request.description,
                created_by=created_by,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            print("NEW RULE: ", rule)

            # Save to PostgreSQL
            self.db.add(rule)
            await self.db.commit()
            await self.db.refresh(rule)

            logger.info(
                "Rule created successfully",
                rule_id=rule.id,
                rule_name=rule.name,
                rule_type=rule.type,
                event="rule_created",
            )

            # Add to Redis if enabled
            if rule.enabled:
                await self.add_to_cache(rule)

            return rule

        except ValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to create rule", error=str(e), event="rule_creation_failed"
            )
            raise DatabaseError(
                "Failed to create rule",
                operation="create_rule",
                details={"error": str(e)},
            ) from e

    async def get_rule_by_id(self, rule_id: UUID) -> Optional[Rule]:
        """
        Get rule by ID from PostgreSQL.

        Args:
            rule_id: Rule ID to retrieve

        Returns:
            Rule instance or None if not found
        """
        try:
            result = await self.db.execute(
                select(Rule).where(Rule.id == rule_id)  # type: ignore
            )
            return result.scalars().first()
        except Exception as e:
            logger.error(
                "Failed to get rule",
                rule_id=str(rule_id),
                error=str(e),
                event="get_rule_failed",
            )
            raise DatabaseError(
                "Failed to retrieve rule", operation="get_rule_by_id", table="rules"
            ) from e

    async def _get_rule_by_name(self, name: str) -> Optional[Rule]:
        """
        Get rule by name (internal helper).

        Args:
            name: Rule name to search for

        Returns:
            Rule instance or None if not found
        """
        try:
            print("HW:: ", name)
            result = await self.db.execute(
                select(Rule).where(Rule.name == name)  # type: ignore
            )
            return result.scalars().first()
        except Exception as e:
            raise DatabaseError(
                "Failed to retrieve rule by name", operation="get_rule_by_name"
            ) from e

    async def get_all_rules(
        self,
        skip: int = 0,
        limit: int = 100,
        enabled_only: bool = False,
        rule_type: Optional[RuleType] = None,
    ) -> tuple[Sequence[Rule], int]:
        """
        Get all rules with optional filtering.

        Args:
            skip: Number of rules to skip (pagination)
            limit: Maximum number of rules to return
            enabled_only: Only return enabled rules
            rule_type: Filter by rule type

        Returns:
            Tuple of (rules list, total count)
        """
        try:
            query = select(Rule)

            # Apply filters
            if enabled_only:
                query = query.where(Rule.enabled == True)  # type: ignore
            if rule_type:
                query = query.where(Rule.type == rule_type)  # type: ignore

            # Get total count
            count_result = await self.db.execute(
                select(Rule).where(
                    (Rule.enabled == True) if enabled_only else True,  # type: ignore
                    (Rule.type == rule_type) if rule_type else True,  # type: ignore
                )
            )
            total = len(count_result.scalars().all())

            # Apply ordering and pagination
            query = (
                query.order_by(desc("priority"), desc("updated_at"))
                .offset(skip)
                .limit(limit)
            )

            result = await self.db.execute(query)
            rules = result.scalars().all()

            logger.debug(
                "Retrieved rules",
                count=len(rules),
                total=total,
                enabled_only=enabled_only,
                event="rules_retrieved",
            )

            return rules, total

        except Exception as e:
            logger.error(
                "Failed to get all rules", error=str(e), event="get_all_rules_failed"
            )
            raise DatabaseError(
                "Failed to retrieve rules", operation="get_all_rules"
            ) from e

    async def get_active_rules(self) -> List[Rule]:
        """
        Get all enabled rules, prioritized by execution order.

        Returns:
            List of enabled rules ordered by priority
        """
        rules, _ = await self.get_all_rules(skip=0, limit=10000, enabled_only=True)
        return list(rules)

    async def get_rules_by_type(self, rule_type: RuleType) -> Sequence[Rule]:
        """
        Get all rules of a specific type.

        Args:
            rule_type: Type of rules to retrieve

        Returns:
            List of rules matching the type
        """
        rules, _ = await self.get_all_rules(skip=0, limit=10000, rule_type=rule_type)
        return list(rules)

    async def update_rule(
        self,
        rule_id: UUID,
        update_request: RuleUpdateRequest,
        updated_by: Optional[str] = None,
    ) -> Rule:
        """
        Update an existing rule in both PostgreSQL and Redis.

        If rule is enabled, updates Redis cache. If disabled, removes from cache.

        Args:
            rule_id: Rule ID to update
            update_request: Update request with new parameters
            updated_by: User updating the rule

        Returns:
            Updated Rule instance

        Raises:
            ValidationError: If rule not found or validation fails
            DatabaseError: If database operation fails
        """
        try:
            # Get existing rule
            rule = await self.get_rule_by_id(rule_id)
            if not rule:
                raise ValidationError(
                    f"Rule with ID {rule_id} not found", field="rule_id", value=rule_id
                )

            # Check for name conflicts
            if update_request.name and update_request.name != rule.name:
                existing = await self._get_rule_by_name(update_request.name)
                if existing:
                    raise ValidationError(
                        f"Rule with name '{update_request.name}' already exists",
                        field="name",
                        value=update_request.name,
                    )

            # Update fields
            if update_request.name is not None:
                rule.name = update_request.name
            if update_request.params is not None:
                rule.params = update_request.params.dict()
            if update_request.enabled is not None:
                rule.enabled = update_request.enabled
            if update_request.priority is not None:
                rule.priority = update_request.priority
            if update_request.critical is not None:
                rule.critical = update_request.critical
            if update_request.description is not None:
                rule.description = update_request.description

            # Update timestamp
            rule.updated_at = datetime.utcnow()

            # Save to PostgreSQL
            self.db.add(rule)
            await self.db.commit()
            await self.db.refresh(rule)

            logger.info(
                "Rule updated successfully",
                rule_id=rule.id,
                rule_name=rule.name,
                event="rule_updated",
            )

            # Sync with Redis
            if rule.enabled:
                await self.add_to_cache(rule)
            else:
                await self.remove_from_cache(rule_id)

            return rule

        except ValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to update rule",
                rule_id=str(rule_id),
                error=str(e),
                event="rule_update_failed",
            )
            raise DatabaseError("Failed to update rule", operation="update_rule") from e

    async def delete_rule(self, rule_id: UUID) -> bool:
        """
        Delete a rule from both PostgreSQL and Redis.

        Args:
            rule_id: Rule ID to delete

        Returns:
            True if rule was deleted, False if not found

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            # Get rule
            rule = await self.get_rule_by_id(rule_id)
            if not rule:
                logger.warning(
                    "Rule not found for deletion",
                    rule_id=str(rule_id),
                    event="rule_not_found",
                )
                return False

            # Delete from PostgreSQL
            await self.db.delete(rule)
            await self.db.commit()

            logger.info(
                "Rule deleted from database",
                rule_id=str(rule_id),
                rule_name=rule.name,
                event="rule_deleted",
            )

            # Delete from Redis
            await self.remove_from_cache(rule_id)

            return True

        except Exception as e:
            logger.error(
                "Failed to delete rule",
                rule_id=str(rule_id),
                error=str(e),
                event="rule_deletion_failed",
            )
            raise DatabaseError("Failed to delete rule", operation="delete_rule") from e

    async def activate_rule(self, rule_id: UUID) -> Rule:
        """
        Activate a rule and add it to Redis cache.

        Args:
            rule_id: Rule ID to activate

        Returns:
            Activated Rule instance

        Raises:
            ValidationError: If rule not found
            DatabaseError: If operation fails
        """
        try:
            rule = await self.get_rule_by_id(rule_id)
            if not rule:
                raise ValidationError(
                    f"Rule with ID {rule_id} not found", field="rule_id", value=rule_id
                )

            if rule.enabled:
                logger.info(
                    "Rule already active",
                    rule_id=str(rule_id),
                    rule_name=rule.name,
                    event="rule_already_active",
                )
                return rule

            # Enable in database
            rule.enabled = True
            rule.updated_at = datetime.utcnow()
            self.db.add(rule)
            await self.db.commit()

            # Add to cache
            await self.add_to_cache(rule)

            logger.info(
                "Rule activated successfully",
                rule_id=str(rule_id),
                rule_name=rule.name,
                event="rule_activated",
            )

            return rule

        except ValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to activate rule",
                rule_id=str(rule_id),
                error=str(e),
                event="rule_activation_failed",
            )
            raise DatabaseError(
                "Failed to activate rule", operation="activate_rule"
            ) from e

    async def deactivate_rule(self, rule_id: UUID) -> Rule:
        """
        Deactivate a rule and remove it from Redis cache.

        Args:
            rule_id: Rule ID to deactivate

        Returns:
            Deactivated Rule instance

        Raises:
            ValidationError: If rule not found
            DatabaseError: If operation fails
        """
        try:
            rule = await self.get_rule_by_id(rule_id)
            if not rule:
                raise ValidationError(
                    f"Rule with ID {rule_id} not found", field="rule_id", value=rule_id
                )

            if not rule.enabled:
                logger.info(
                    "Rule already inactive",
                    rule_id=str(rule_id),
                    rule_name=rule.name,
                    event="rule_already_inactive",
                )
                return rule

            # Disable in database
            rule.enabled = False
            rule.updated_at = datetime.utcnow()
            self.db.add(rule)
            await self.db.commit()

            # Remove from cache
            await self.remove_from_cache(rule_id)

            logger.info(
                "Rule deactivated successfully",
                rule_id=str(rule_id),
                rule_name=rule.name,
                event="rule_deactivated",
            )

            return rule

        except ValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to deactivate rule",
                rule_id=str(rule_id),
                error=str(e),
                event="rule_deactivation_failed",
            )
            raise DatabaseError(
                "Failed to deactivate rule", operation="deactivate_rule"
            ) from e

    async def add_to_cache(self, rule: Rule, ttl: Optional[int] = None) -> bool:
        """
        Add or update rule in Redis cache.

        Args:
            rule: Rule instance to cache
            ttl: Time to live in seconds (default: 1 hour)

        Returns:
            True if successfully cached

        Raises:
            DatabaseError: If Redis operation fails
        """
        try:
            ttl = ttl or self.cache_ttl
            cache_key = f"{RULE_CACHE_KEY_PREFIX}{rule.id}"

            # Serialize rule to JSON
            rule_data = {
                "id": rule.id,
                "name": rule.name,
                "type": rule.type.value,
                "params": rule.params,
                "enabled": rule.enabled,
                "priority": rule.priority,
                "critical": rule.critical,
                "description": rule.description,
                "created_at": rule.created_at.isoformat(),
                "updated_at": rule.updated_at.isoformat(),
                "execution_count": rule.execution_count,
                "match_count": rule.match_count,
            }

            # Cache rule
            await self.async_redis.setex(
                cache_key, ttl, json.dumps(rule_data, default=str)
            )

            # Add to active rules list
            # POSSIBLE BUG HERE
            await self.async_redis.sadd(ACTIVE_RULES_KEY, str(rule.id))  # type: ignore

            # Add to type-specific set
            type_key = f"{RULE_TYPE_KEY_PREFIX}{rule.type.value}"
            await self.async_redis.sadd(type_key, str(rule.id))  # type: ignore

            # Update rule index (sorted set by priority)
            await self.async_redis.zadd(RULE_INDEX_KEY, {str(rule.id): rule.priority})

            logger.debug(
                "Rule added to cache",
                rule_id=rule.id,
                cache_key=cache_key,
                ttl=ttl,
                event="rule_cached",
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to add rule to cache",
                rule_id=rule.id,
                error=str(e),
                event="cache_add_failed",
            )
            raise DatabaseError(
                "Failed to cache rule",
                operation="add_to_cache",
                details={"error": str(e)},
            ) from e

    async def remove_from_cache(self, rule_id: UUID) -> bool:
        """
        Remove rule from Redis cache.

        Args:
            rule_id: Rule ID to remove

        Returns:
            True if rule was removed, False if not found

        Raises:
            DatabaseError: If Redis operation fails
        """
        try:
            cache_key = f"{RULE_CACHE_KEY_PREFIX}{rule_id}"

            # Remove from cache
            deleted = await self.async_redis.delete(cache_key)

            # Remove from active rules set
            await self.async_redis.srem(ACTIVE_RULES_KEY, str(rule_id))  # type: ignore

            # Remove from rule index
            await self.async_redis.zrem(RULE_INDEX_KEY, str(rule_id))

            logger.debug(
                "Rule removed from cache",
                rule_id=str(rule_id),
                cache_key=cache_key,
                event="rule_cache_removed",
            )

            return bool(deleted)

        except Exception as e:
            logger.error(
                "Failed to remove rule from cache",
                rule_id=str(rule_id),
                error=str(e),
                event="cache_remove_failed",
            )
            raise DatabaseError(
                "Failed to remove rule from cache", operation="remove_from_cache"
            ) from e

    async def get_from_cache(self, rule_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get rule from Redis cache.

        Args:
            rule_id: Rule ID to retrieve

        Returns:
            Rule data dictionary or None if not cached

        Raises:
            DatabaseError: If Redis operation fails
        """
        try:
            cache_key = f"{RULE_CACHE_KEY_PREFIX}{rule_id}"
            cached_data = await self.async_redis.get(cache_key)

            if not cached_data:
                logger.debug(
                    "Rule not found in cache", rule_id=str(rule_id), event="cache_miss"
                )
                return None

            rule_data = json.loads(cached_data)

            logger.debug(
                "Rule retrieved from cache", rule_id=str(rule_id), event="cache_hit"
            )

            return rule_data

        except Exception as e:
            logger.error(
                "Failed to get rule from cache",
                rule_id=str(rule_id),
                error=str(e),
                event="cache_get_failed",
            )
            raise DatabaseError(
                "Failed to retrieve rule from cache", operation="get_from_cache"
            ) from e

    async def clear_cache(self) -> int:
        """
        Clear all rules from Redis cache.

        Returns:
            Number of rules removed from cache

        Raises:
            DatabaseError: If Redis operation fails
        """
        try:
            # Get all rule IDs from active rules set
            active_rule_ids = await self.async_redis.smembers(ACTIVE_RULES_KEY)  # type: ignore

            if not active_rule_ids:
                logger.info("Cache already empty", event="cache_clear_empty")
                return 0

            # Delete all rule cache keys
            cache_keys = [
                f"{RULE_CACHE_KEY_PREFIX}{rule_id}" for rule_id in active_rule_ids
            ]

            deleted = await self.async_redis.delete(*cache_keys)

            # Clear index keys
            await self.async_redis.delete(ACTIVE_RULES_KEY)
            await self.async_redis.delete(RULE_INDEX_KEY)

            # Clear type-specific sets
            rule_types = [rt.value for rt in RuleType]
            for rule_type in rule_types:
                type_key = f"{RULE_TYPE_KEY_PREFIX}{rule_type}"
                await self.async_redis.delete(type_key)

            logger.info(
                "Cache cleared successfully",
                rules_removed=deleted,
                event="cache_cleared",
            )

            return deleted

        except Exception as e:
            logger.error(
                "Failed to clear cache", error=str(e), event="cache_clear_failed"
            )
            raise DatabaseError("Failed to clear cache", operation="clear_cache") from e

    async def refresh_cache(self, force: bool = False) -> int:
        """
        Refresh Redis cache with all active rules from database.

        Useful for hot reload and cache recovery.

        Args:
            force: Clear existing cache before refresh

        Returns:
            Number of rules added to cache

        Raises:
            DatabaseError: If operation fails
        """
        try:
            start_time = time.time()

            # Clear existing cache if forced
            if force:
                await self.clear_cache()

            # Get all enabled rules
            active_rules, _ = await self.get_all_rules(
                skip=0, limit=10000, enabled_only=True
            )

            # Add to cache
            cache_count = 0
            for rule in active_rules:
                try:
                    await self.add_to_cache(rule)
                    cache_count += 1
                except Exception as e:
                    logger.warning(
                        "Failed to cache rule during refresh",
                        rule_id=rule.id,
                        error=str(e),
                    )
                    continue

            elapsed_ms = (time.time() - start_time) * 1000

            logger.info(
                "Cache refresh completed",
                rules_refreshed=cache_count,
                elapsed_ms=round(elapsed_ms, 2),
                force=force,
                event="cache_refreshed",
            )

            return cache_count

        except Exception as e:
            logger.error(
                "Failed to refresh cache", error=str(e), event="cache_refresh_failed"
            )
            raise DatabaseError(
                "Failed to refresh cache", operation="refresh_cache"
            ) from e

    async def record_execution(
        self,
        rule_id: UUID,
        transaction_id: UUID,
        correlation_id: str,
        matched: bool,
        confidence_score: Optional[float],
        execution_time_ms: float,
        context: Dict[str, Any],
        error_message: Optional[str] = None,
    ) -> RuleExecution:
        """
        Record rule execution for audit logging and statistics.

        Args:
            rule_id: ID of executed rule
            transaction_id: ID of evaluated transaction
            correlation_id: Request correlation ID
            matched: Whether rule matched
            confidence_score: Confidence score if applicable
            execution_time_ms: Execution time in milliseconds
            context: Execution context data
            error_message: Error message if execution failed

        Returns:
            Created RuleExecution record

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            execution = RuleExecution(
                rule_id=rule_id,
                transaction_id=transaction_id,
                correlation_id=correlation_id,
                matched=matched,
                confidence_score=confidence_score,
                execution_time_ms=execution_time_ms,
                context=context,
                error_message=error_message,
                executed_at=datetime.utcnow(),
            )

            self.db.add(execution)
            await self.db.commit()
            await self.db.refresh(execution)

            # Update rule statistics
            rule = await self.get_rule_by_id(rule_id)
            if rule:
                rule.execution_count += 1
                if matched:
                    rule.match_count += 1
                rule.last_executed_at = datetime.utcnow()

                # Update average execution time
                if rule.average_execution_time_ms is None:
                    rule.average_execution_time_ms = execution_time_ms
                else:
                    rule.average_execution_time_ms = (
                        rule.average_execution_time_ms * (rule.execution_count - 1)
                        + execution_time_ms
                    ) / rule.execution_count

                self.db.add(rule)
                await self.db.commit()

            logger.debug(
                "Execution recorded",
                rule_id=rule_id,
                transaction_id=transaction_id,
                matched=matched,
                execution_time_ms=execution_time_ms,
                event="execution_recorded",
            )

            return execution

        except Exception as e:
            logger.error(
                "Failed to record execution",
                rule_id=str(rule_id),
                error=str(e),
                event="execution_record_failed",
            )
            raise DatabaseError(
                "Failed to record rule execution", operation="record_execution"
            ) from e

    # ==================== CACHE Status Operations ====================

    async def get_cache_status(self) -> Dict[str, Any]:
        """
        Get current status of the rule cache.

        Returns:
            Dict with cache status information

        Raises:
            DatabaseError: If cache operation fails
        """
        try:
            # Get active rules from cache
            active_rule_ids = await self.async_redis.smembers(ACTIVE_RULES_KEY)  # type: ignore

            # Get rule types from cache
            type_keys = await self.async_redis.keys(f"{RULE_TYPE_KEY_PREFIX}*")

            # Get priority index size
            index_size = await self.async_redis.zcard(RULE_INDEX_KEY)

            logger.debug(
                "Cache status retrieved",
                active_rules_count=len(active_rule_ids) if active_rule_ids else 0,
                rule_types_count=len(type_keys) if type_keys else 0,
                priority_index_size=index_size,
                event="cache_status_retrieved",
            )

            return {
                "active_rules_count": len(active_rule_ids) if active_rule_ids else 0,
                "rule_types_count": len(type_keys) if type_keys else 0,
                "priority_index_size": index_size,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(
                "Failed to get cache status", error=str(e), event="cache_status_failed"
            )
            raise DatabaseError(
                "Failed to get cache status", operation="get_cache_status"
            ) from e
