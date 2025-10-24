"""
FastAPI routes for the rule engine module.

Provides REST API endpoints for managing fraud detection rules:
- CRUD operations (Create, Read, Update, Delete)
- Rule activation/deactivation
- Hot reload functionality
- Rule evaluation

All endpoints include comprehensive logging with correlation IDs.
"""

from datetime import datetime
from http import HTTPStatus
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from src.core.exceptions import (
    DatabaseError,
    ValidationError,
)
from src.core.logging import get_logger
from src.modules.users.dependencies import CurrentUser
from src.storage.dependencies import AsyncDbSessionDep
from src.storage.redis.client import get_async_redis_dependency

from .enums import RuleType
from .repository import RuleRepository
from .schemas import (
    CacheStatisticsResponse,
    RuleCreateRequest,
    RuleListResponse,
    RuleResponse,
    RuleUpdateRequest,
)

# Initialize logger
logger = get_logger("rule_engine.routes")

# Create router
router = APIRouter(prefix="/rules", tags=["Rule Engine"])


async def get_rule_repository(
    db: AsyncDbSessionDep, redis_client=Depends(get_async_redis_dependency)
) -> RuleRepository:
    """Get rule repository instance with database and Redis dependencies."""
    return RuleRepository(db, redis_client)


@router.post(
    "",
    response_model=RuleResponse,
    status_code=HTTPStatus.CREATED,
    summary="Create a new fraud detection rule",
    responses={
        HTTPStatus.CREATED: {
            "description": "Rule created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "High Amount Threshold",
                        "type": "threshold",
                        "params": {"max_amount": 10000.0, "operator": "greater_than"},
                        "priority": 100,
                        "enabled": True,
                        "critical": True,
                    }
                }
            },
        },
        HTTPStatus.BAD_REQUEST: {
            "description": "Invalid rule parameters or duplicate name"
        },
        HTTPStatus.INTERNAL_SERVER_ERROR: {"description": "Database operation failed"},
    },
)
async def create_rule(
    current_user: CurrentUser,
    rule_data: RuleCreateRequest = Body(..., description="Rule creation parameters"),
    repository: RuleRepository = Depends(get_rule_repository),
) -> RuleResponse:
    """
    Create a new fraud detection rule.

    Args:
        rule_data: Rule creation request with parameters
        repository: Injected rule repository
        current_user: Current authenticated user

    Returns:
        RuleResponse: Created rule with UUID

    Raises:
        HTTPException: If validation fails or database error occurs
    """
    try:
        logger.info(
            "Creating new rule",
            rule_name=rule_data.name,
            rule_type=rule_data.type.value,
            priority=rule_data.priority,
            critical=rule_data.critical,
            created_by_user_id=str(current_user.id),
            event="rule_create_request",
        )

        # Create rule in repository with user ID
        created_rule = await repository.create_rule(
            rule_data, created_by_user_id=current_user.id
        )

        logger.info(
            "Rule created successfully",
            rule_id=str(created_rule.id),
            rule_name=created_rule.name,
            rule_type=created_rule.type.value,
            created_by_user_id=str(current_user.id),
            event="rule_created",
        )

        return RuleResponse.model_validate(created_rule)

    except ValidationError as e:
        logger.warning(
            "Rule creation validation failed",
            rule_name=rule_data.name,
            error=str(e),
            event="rule_validation_failed",
        )
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail=f"Validation error: {str(e)}"
        )
    except DatabaseError as e:
        logger.error(
            "Rule creation database error",
            rule_name=rule_data.name,
            error=str(e),
            event="rule_creation_db_error",
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="Failed to create rule"
        )
    except Exception as e:
        logger.error(
            "Unexpected error during rule creation",
            rule_name=rule_data.name,
            error=str(e),
            event="rule_creation_error",
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Unexpected error occurred",
        )


@router.get(
    "/{rule_id}",
    response_model=RuleResponse,
    summary="Get a specific rule by ID",
    responses={
        HTTPStatus.OK: {"description": "Rule found"},
        HTTPStatus.NOT_FOUND: {"description": "Rule not found"},
        HTTPStatus.INTERNAL_SERVER_ERROR: {"description": "Database error"},
    },
)
async def get_rule(
    rule_id: UUID, repository: RuleRepository = Depends(get_rule_repository)
) -> RuleResponse:
    """
    Retrieve a specific fraud detection rule by its UUID.

    Args:
        rule_id: UUID of the rule to retrieve
        repository: Injected rule repository

    Returns:
        RuleResponse: Rule details

    Raises:
        HTTPException: If rule not found or database error occurs
    """
    try:
        logger.debug("Retrieving rule", rule_id=str(rule_id), event="rule_get_request")

        rule = await repository.get_rule_by_id(rule_id)

        if not rule:
            logger.warning(
                "Rule not found", rule_id=str(rule_id), event="rule_not_found"
            )
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Rule with ID {rule_id} not found",
            )

        logger.debug(
            "Rule retrieved successfully",
            rule_id=str(rule_id),
            rule_name=rule.name,
            event="rule_retrieved",
        )

        return RuleResponse.model_validate(rule)

    except HTTPException:
        raise
    except DatabaseError as e:
        logger.error(
            "Rule retrieval database error",
            rule_id=str(rule_id),
            error=str(e),
            event="rule_get_db_error",
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve rule",
        )
    except Exception as e:
        logger.error(
            "Unexpected error during rule retrieval",
            rule_id=str(rule_id),
            error=str(e),
            event="rule_get_error",
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Unexpected error occurred",
        )


@router.get(
    "",
    response_model=RuleListResponse,
    summary="List all rules with filtering and pagination",
    responses={
        HTTPStatus.OK: {"description": "List of rules"},
        HTTPStatus.BAD_REQUEST: {"description": "Invalid filter parameters"},
        HTTPStatus.INTERNAL_SERVER_ERROR: {"description": "Database error"},
    },
)
async def list_rules(
    skip: int = Query(0, ge=0, description="Number of rules to skip"),
    limit: int = Query(
        50, ge=1, le=100, description="Maximum number of rules to return"
    ),
    enabled_only: bool = Query(False, description="Return only enabled rules"),
    rule_type: Optional[RuleType] = Query(None, description="Filter by rule type"),
    repository: RuleRepository = Depends(get_rule_repository),
) -> RuleListResponse:
    """
    List fraud detection rules with pagination and filtering.

    Args:
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        enabled_only: Filter to only enabled rules
        rule_type: Filter by specific rule type
        repository: Injected rule repository

    Returns:
        RuleListResponse: List of rules with total count

    Raises:
        HTTPException: If invalid parameters or database error occurs
    """
    try:
        logger.debug(
            "Listing rules",
            skip=skip,
            limit=limit,
            enabled_only=enabled_only,
            rule_type=rule_type.value if rule_type else None,
            event="rule_list_request",
        )

        rules, total = await repository.get_all_rules(
            skip=skip, limit=limit, enabled_only=enabled_only, rule_type=rule_type
        )

        logger.debug(
            "Rules listed successfully",
            total=total,
            returned=len(rules),
            skip=skip,
            limit=limit,
            event="rules_listed",
        )

        # Calculate pagination info
        pages = (total + limit - 1) // limit if total > 0 else 0
        page = (skip // limit) + 1 if skip > 0 else 1

        return RuleListResponse(
            rules=[RuleResponse.model_validate(rule) for rule in rules],
            total=total,
            page=page,
            page_size=limit,
            pages=pages,
        )

    except ValidationError as e:
        logger.warning(
            "Rules listing validation failed",
            error=str(e),
            event="rules_list_validation_failed",
        )
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail=f"Invalid parameters: {str(e)}"
        )
    except DatabaseError as e:
        logger.error(
            "Rules listing database error", error=str(e), event="rules_list_db_error"
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="Failed to list rules"
        )
    except Exception as e:
        logger.error(
            "Unexpected error during rules listing",
            error=str(e),
            event="rules_list_error",
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Unexpected error occurred",
        )


@router.get(
    "/type/{rule_type}",
    response_model=List[RuleResponse],
    summary="Get all rules of a specific type",
    responses={
        HTTPStatus.OK: {"description": "List of rules by type"},
        HTTPStatus.INTERNAL_SERVER_ERROR: {"description": "Database error"},
    },
)
async def get_rules_by_type(
    rule_type: RuleType, repository: RuleRepository = Depends(get_rule_repository)
) -> List[RuleResponse]:
    """
    Get all fraud detection rules of a specific type.

    Args:
        rule_type: Type of rules to retrieve
        repository: Injected rule repository

    Returns:
        List[RuleResponse]: List of rules matching the type

    Raises:
        HTTPException: If database error occurs
    """
    try:
        logger.debug(
            "Retrieving rules by type",
            rule_type=rule_type.value,
            event="rules_by_type_request",
        )

        rules = await repository.get_rules_by_type(rule_type)

        logger.debug(
            "Rules by type retrieved successfully",
            rule_type=rule_type.value,
            count=len(rules),
            event="rules_by_type_retrieved",
        )

        return [RuleResponse.model_validate(rule) for rule in rules]

    except DatabaseError as e:
        logger.error(
            "Rules by type retrieval database error",
            rule_type=rule_type.value,
            error=str(e),
            event="rules_by_type_db_error",
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve rules",
        )
    except Exception as e:
        logger.error(
            "Unexpected error during rules by type retrieval",
            rule_type=rule_type.value,
            error=str(e),
            event="rules_by_type_error",
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Unexpected error occurred",
        )


@router.put(
    "/{rule_id}",
    response_model=RuleResponse,
    summary="Update an existing rule",
    responses={
        HTTPStatus.OK: {"description": "Rule updated successfully"},
        HTTPStatus.NOT_FOUND: {"description": "Rule not found"},
        HTTPStatus.BAD_REQUEST: {"description": "Invalid rule parameters"},
        HTTPStatus.INTERNAL_SERVER_ERROR: {"description": "Database error"},
    },
)
async def update_rule(
    rule_id: UUID,
    rule_data: RuleUpdateRequest = Body(..., description="Rule update parameters"),
    repository: RuleRepository = Depends(get_rule_repository),
) -> RuleResponse:
    """
    Update an existing fraud detection rule.

    Updates both database and Redis cache if the rule is active.

    Args:
        rule_id: UUID of the rule to update
        rule_data: Rule update request with new parameters
        repository: Injected rule repository

    Returns:
        RuleResponse: Updated rule details

    Raises:
        HTTPException: If rule not found, validation fails, or database error occurs
    """
    try:
        logger.info("Updating rule", rule_id=str(rule_id), event="rule_update_request")

        # Update rule in repository
        updated_rule = await repository.update_rule(rule_id, rule_data)

        logger.info(
            "Rule updated successfully",
            rule_id=str(rule_id),
            rule_name=updated_rule.name,
            event="rule_updated",
        )

        return RuleResponse.model_validate(updated_rule)

    except ValidationError as e:
        logger.warning(
            "Rule update validation failed",
            rule_id=str(rule_id),
            error=str(e),
            event="rule_update_validation_failed",
        )
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail=f"Validation error: {str(e)}"
        )
    except DatabaseError as e:
        if "not found" in str(e).lower():
            logger.warning(
                "Rule not found for update",
                rule_id=str(rule_id),
                event="rule_not_found_for_update",
            )
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Rule with ID {rule_id} not found",
            )
        else:
            logger.error(
                "Rule update database error",
                rule_id=str(rule_id),
                error=str(e),
                event="rule_update_db_error",
            )
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Failed to update rule",
            )
    except Exception as e:
        logger.error(
            "Unexpected error during rule update",
            rule_id=str(rule_id),
            error=str(e),
            event="rule_update_error",
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Unexpected error occurred",
        )


@router.delete(
    "/{rule_id}",
    status_code=HTTPStatus.NO_CONTENT,
    summary="Delete a rule",
    responses={
        HTTPStatus.NO_CONTENT: {"description": "Rule deleted successfully"},
        HTTPStatus.NOT_FOUND: {"description": "Rule not found"},
        HTTPStatus.INTERNAL_SERVER_ERROR: {"description": "Database error"},
    },
)
async def delete_rule(
    rule_id: UUID, repository: RuleRepository = Depends(get_rule_repository)
) -> None:
    """
    Delete a fraud detection rule.

    Removes from both database and Redis cache.

    Args:
        rule_id: UUID of the rule to delete
        repository: Injected rule repository

    Raises:
        HTTPException: If rule not found or database error occurs
    """
    try:
        logger.info("Deleting rule", rule_id=str(rule_id), event="rule_delete_request")

        # Delete rule from repository
        deleted = await repository.delete_rule(rule_id)

        if not deleted:
            logger.warning(
                "Rule not found for deletion",
                rule_id=str(rule_id),
                event="rule_not_found_for_delete",
            )
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Rule with ID {rule_id} not found",
            )

        logger.info(
            "Rule deleted successfully", rule_id=str(rule_id), event="rule_deleted"
        )

    except HTTPException:
        raise
    except DatabaseError as e:
        logger.error(
            "Rule deletion database error",
            rule_id=str(rule_id),
            error=str(e),
            event="rule_deletion_db_error",
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="Failed to delete rule"
        )
    except Exception as e:
        logger.error(
            "Unexpected error during rule deletion",
            rule_id=str(rule_id),
            error=str(e),
            event="rule_deletion_error",
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Unexpected error occurred",
        )


@router.post(
    "/{rule_id}/activate",
    response_model=RuleResponse,
    summary="Activate a rule (enable and cache)",
    responses={
        HTTPStatus.OK: {"description": "Rule activated successfully"},
        HTTPStatus.NOT_FOUND: {"description": "Rule not found"},
        HTTPStatus.INTERNAL_SERVER_ERROR: {"description": "Database or cache error"},
    },
)
async def activate_rule(
    rule_id: UUID, repository: RuleRepository = Depends(get_rule_repository)
) -> RuleResponse:
    """
    Activate a fraud detection rule.

    Enables the rule and adds it to the Redis cache for active rules.

    Args:
        rule_id: UUID of the rule to activate
        repository: Injected rule repository

    Returns:
        RuleResponse: Activated rule details

    Raises:
        HTTPException: If rule not found or error occurs
    """
    try:
        logger.info(
            "Activating rule", rule_id=str(rule_id), event="rule_activate_request"
        )

        activated_rule = await repository.activate_rule(rule_id)

        logger.info(
            "Rule activated successfully",
            rule_id=str(rule_id),
            rule_name=activated_rule.name,
            event="rule_activated",
        )

        return RuleResponse.model_validate(activated_rule)

    except ValidationError as e:
        logger.warning(
            "Rule activation validation failed",
            rule_id=str(rule_id),
            error=str(e),
            event="rule_activate_validation_failed",
        )
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail=f"Validation error: {str(e)}"
        )
    except DatabaseError as e:
        if "not found" in str(e).lower():
            logger.warning(
                "Rule not found for activation",
                rule_id=str(rule_id),
                event="rule_not_found_for_activate",
            )
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Rule with ID {rule_id} not found",
            )
        else:
            logger.error(
                "Rule activation error",
                rule_id=str(rule_id),
                error=str(e),
                event="rule_activate_error",
            )
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Failed to activate rule",
            )
    except Exception as e:
        logger.error(
            "Unexpected error during rule activation",
            rule_id=str(rule_id),
            error=str(e),
            event="rule_activate_unexpected_error",
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Unexpected error occurred",
        )


@router.post(
    "/{rule_id}/deactivate",
    response_model=RuleResponse,
    summary="Deactivate a rule (disable and remove from cache)",
    responses={
        HTTPStatus.OK: {"description": "Rule deactivated successfully"},
        HTTPStatus.NOT_FOUND: {"description": "Rule not found"},
        HTTPStatus.INTERNAL_SERVER_ERROR: {"description": "Database or cache error"},
    },
)
async def deactivate_rule(
    rule_id: UUID, repository: RuleRepository = Depends(get_rule_repository)
) -> RuleResponse:
    """
    Deactivate a fraud detection rule.

    Disables the rule and removes it from the Redis cache.

    Args:
        rule_id: UUID of the rule to deactivate
        repository: Injected rule repository

    Returns:
        RuleResponse: Deactivated rule details

    Raises:
        HTTPException: If rule not found or error occurs
    """
    try:
        logger.info(
            "Deactivating rule", rule_id=str(rule_id), event="rule_deactivate_request"
        )

        deactivated_rule = await repository.deactivate_rule(rule_id)

        logger.info(
            "Rule deactivated successfully",
            rule_id=str(rule_id),
            rule_name=deactivated_rule.name,
            event="rule_deactivated",
        )

        return RuleResponse.model_validate(deactivated_rule)

    except ValidationError as e:
        logger.warning(
            "Rule deactivation validation failed",
            rule_id=str(rule_id),
            error=str(e),
            event="rule_deactivate_validation_failed",
        )
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail=f"Validation error: {str(e)}"
        )
    except DatabaseError as e:
        if "not found" in str(e).lower():
            logger.warning(
                "Rule not found for deactivation",
                rule_id=str(rule_id),
                event="rule_not_found_for_deactivate",
            )
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Rule with ID {rule_id} not found",
            )
        else:
            logger.error(
                "Rule deactivation error",
                rule_id=str(rule_id),
                error=str(e),
                event="rule_deactivate_error",
            )
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Failed to deactivate rule",
            )
    except Exception as e:
        logger.error(
            "Unexpected error during rule deactivation",
            rule_id=str(rule_id),
            error=str(e),
            event="rule_deactivate_unexpected_error",
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Unexpected error occurred",
        )


@router.get(
    "/cache/status",
    response_model=CacheStatisticsResponse,
    summary="Get cache status information",
    responses={
        HTTPStatus.OK: {"description": "Cache status retrieved"},
        HTTPStatus.INTERNAL_SERVER_ERROR: {"description": "Cache error"},
    },
)
async def get_cache_status(
    repository: RuleRepository = Depends(get_rule_repository),
) -> CacheStatisticsResponse:
    """
    Get current status of the rule cache.

    Returns information about cached rules and cache statistics.

    Args:
        repository: Injected rule repository

    Returns:
        CacheStatusResponse: Cache status and statistics

    Raises:
        HTTPException: If cache operation fails
    """
    try:
        logger.debug("Retrieving cache status", event="cache_status_request")

        status = await repository.get_cache_status()

        logger.debug(
            "Cache status retrieved successfully", event="cache_status_retrieved"
        )

        print("SSS: ", status)

        return CacheStatisticsResponse.model_validate(status)

    except DatabaseError as e:
        logger.error(
            "Cache status retrieval error", error=str(e), event="cache_status_error"
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache status",
        )
    except Exception as e:
        logger.error(
            "Unexpected error retrieving cache status",
            error=str(e),
            event="cache_status_unexpected_error",
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Unexpected error occurred",
        )


# @router.post(
#     "/cache/clear",
#     status_code=HTTPStatus.NO_CONTENT,
#     summary="Clear all cached rules",
#     responses={
#         HTTPStatus.NO_CONTENT: {"description": "Cache cleared successfully"},
#         HTTPStatus.INTERNAL_SERVER_ERROR: {"description": "Cache error"}
#     }
# )
# async def clear_cache(
#     repository: RuleRepository = Depends(get_rule_repository)
# ) -> None:
#     """
#     Clear all rules from the Redis cache.

#     This operation does not affect the database, only removes cached entries.

#     Args:
#         repository: Injected rule repository

#     Raises:
#         HTTPException: If cache operation fails
#     """
#     try:
#         logger.warning(
#             "Clearing entire rule cache",
#             event="cache_clear_request"
#         )

#         await repository.clear_cache()

#         logger.warning(
#             "Cache cleared successfully",
#             event="cache_cleared"
#         )

#     except DatabaseError as e:
#         logger.error(
#             "Cache clear error",
#             error=str(e),
#             event="cache_clear_error"
#         )
#         raise HTTPException(
#             status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
#             detail="Failed to clear cache"
#         )
#     except Exception as e:
#         logger.error(
#             "Unexpected error clearing cache",
#             error=str(e),
#             event="cache_clear_unexpected_error"
#         )
#         raise HTTPException(
#             status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
#             detail="Unexpected error occurred"
#         )


@router.post(
    "/cache/refresh",
    summary="Hot reload - refresh cache from database",
    responses={
        HTTPStatus.OK: {
            "description": "Cache refreshed successfully",
            "content": {
                "application/json": {"example": {"success": True, "rules_loaded": 10}}
            },
        },
        HTTPStatus.INTERNAL_SERVER_ERROR: {"description": "Cache or database error"},
    },
)
async def hot_reload_rules(
    force: bool = Query(False, description="Force refresh even if cache is valid"),
    repository: RuleRepository = Depends(get_rule_repository),
) -> dict:
    """
    Hot reload fraud detection rules from database into cache.

    This allows updating rules without restarting the application.

    Args:
        force: Force refresh even if cache appears valid
        repository: Injected rule repository

    Returns:
        dict: Reload status with success flag and rules_loaded count

    Raises:
        HTTPException: If operation fails
    """
    try:
        logger.info(
            "Hot reloading rules from database", force=force, event="hot_reload_request"
        )

        rules_loaded = await repository.refresh_cache(force=force)

        logger.info(
            "Rules hot reloaded successfully",
            rules_loaded=rules_loaded,
            event="hot_reload_completed",
        )

        return {
            "success": True,
            "rules_loaded": rules_loaded,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except DatabaseError as e:
        logger.error(
            "Hot reload database error", error=str(e), event="hot_reload_db_error"
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Failed to reload rules from database",
        )
    except Exception as e:
        logger.error(
            "Unexpected error during hot reload", error=str(e), event="hot_reload_error"
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Unexpected error occurred",
        )
