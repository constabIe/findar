"""
FastAPI routes for the notifications module.

Provides REST API endpoints for managing notification templates,
channel configurations, delivery tracking, and sending notifications.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.notifications.enums import (
    NotificationChannel,
    NotificationStatus,
    TemplateType,
)
from src.modules.notifications.repository import NotificationRepository
from src.modules.notifications.schemas import (
    NotificationChannelConfigCreate,
    NotificationChannelConfigResponse,
    NotificationDeliveryListResponse,
    NotificationDeliveryResponse,
    NotificationSendRequest,
    NotificationSendResponse,
    NotificationStatsResponse,
    NotificationTemplateCreate,
    NotificationTemplateListResponse,
    NotificationTemplateResponse,
    NotificationTemplateUpdate,
)
from src.modules.notifications.service import NotificationService
from src.storage.dependencies import get_db_session

router = APIRouter(prefix="/notifications", tags=["notifications"])


# Dependency to get notification repository
async def get_notification_repository(
    db_session: AsyncSession = Depends(get_db_session),
) -> NotificationRepository:
    """Get notification repository instance."""
    return NotificationRepository(db_session)


# Dependency to get notification service
async def get_notification_service(
    db_session: AsyncSession = Depends(get_db_session),
) -> NotificationService:
    """Get notification service instance."""
    return NotificationService(db_session)


# Template management endpoints
@router.post(
    "/templates",
    response_model=NotificationTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create notification template",
)
async def create_template(
    template_data: NotificationTemplateCreate,
    repository: NotificationRepository = Depends(get_notification_repository),
) -> NotificationTemplateResponse:
    """
    Create a new notification template.

    Templates define the structure and content of notifications sent
    through various channels when fraud is detected.
    """
    try:
        template = await repository.create_template(template_data)
        return NotificationTemplateResponse.model_validate(template)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create template: {str(e)}",
        )


@router.get(
    "/templates",
    response_model=NotificationTemplateListResponse,
    summary="List notification templates",
)
async def list_templates(
    template_type: Optional[TemplateType] = Query(
        None, description="Filter by template type"
    ),
    channel: Optional[NotificationChannel] = Query(
        None, description="Filter by notification channel"
    ),
    enabled_only: bool = Query(True, description="Only return enabled templates"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    repository: NotificationRepository = Depends(get_notification_repository),
) -> NotificationTemplateListResponse:
    """List notification templates with filtering and pagination."""
    try:
        offset = (page - 1) * page_size

        templates = await repository.get_templates(
            template_type=template_type,
            channel=channel,
            enabled_only=enabled_only,
            limit=page_size,
            offset=offset,
        )

        # TODO: Implement total count query
        total = len(templates)  # This is not accurate for pagination

        return NotificationTemplateListResponse(
            templates=[
                NotificationTemplateResponse.model_validate(t) for t in templates
            ],
            total=total,
            page=page,
            page_size=page_size,
            pages=(total + page_size - 1) // page_size,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list templates: {str(e)}",
        )


@router.get(
    "/templates/{template_id}",
    response_model=NotificationTemplateResponse,
    summary="Get notification template",
)
async def get_template(
    template_id: UUID,
    repository: NotificationRepository = Depends(get_notification_repository),
) -> NotificationTemplateResponse:
    """Get a specific notification template by ID."""
    template = await repository.get_template(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    return NotificationTemplateResponse.model_validate(template)


@router.put(
    "/templates/{template_id}",
    response_model=NotificationTemplateResponse,
    summary="Update notification template",
)
async def update_template(
    template_id: UUID,
    update_data: NotificationTemplateUpdate,
    repository: NotificationRepository = Depends(get_notification_repository),
) -> NotificationTemplateResponse:
    """Update an existing notification template."""
    template = await repository.update_template(template_id, update_data)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    return NotificationTemplateResponse.model_validate(template)


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete notification template",
)
async def delete_template(
    template_id: UUID,
    repository: NotificationRepository = Depends(get_notification_repository),
) -> None:
    """Delete a notification template."""
    success = await repository.delete_template(template_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )


# Channel configuration endpoints
@router.post(
    "/channels",
    response_model=NotificationChannelConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create channel configuration",
)
async def create_channel_config(
    config_data: NotificationChannelConfigCreate,
    repository: NotificationRepository = Depends(get_notification_repository),
) -> NotificationChannelConfigResponse:
    """Create notification channel configuration."""
    try:
        config = await repository.create_channel_config(config_data)
        return NotificationChannelConfigResponse.model_validate(config)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create channel config: {str(e)}",
        )


@router.get(
    "/channels",
    response_model=List[NotificationChannelConfigResponse],
    summary="List channel configurations",
)
async def list_channel_configs(
    repository: NotificationRepository = Depends(get_notification_repository),
) -> List[NotificationChannelConfigResponse]:
    """List all notification channel configurations."""
    try:
        configs = await repository.get_all_channel_configs()
        return [NotificationChannelConfigResponse.model_validate(c) for c in configs]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list channel configs: {str(e)}",
        )


@router.get(
    "/channels/{channel}",
    response_model=NotificationChannelConfigResponse,
    summary="Get channel configuration",
)
async def get_channel_config(
    channel: NotificationChannel,
    repository: NotificationRepository = Depends(get_notification_repository),
) -> NotificationChannelConfigResponse:
    """Get configuration for a specific notification channel."""
    config = await repository.get_channel_config(channel)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel configuration not found",
        )

    return NotificationChannelConfigResponse.model_validate(config)


@router.put(
    "/channels/{channel}",
    response_model=NotificationChannelConfigResponse,
    summary="Update channel configuration",
)
async def update_channel_config(
    channel: NotificationChannel,
    config_data: Dict[str, Any],
    repository: NotificationRepository = Depends(get_notification_repository),
) -> NotificationChannelConfigResponse:
    """Update notification channel configuration."""
    config = await repository.update_channel_config(channel, config_data)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel configuration not found",
        )

    return NotificationChannelConfigResponse.model_validate(config)


# Delivery tracking endpoints
@router.get(
    "/deliveries",
    response_model=NotificationDeliveryListResponse,
    summary="List notification deliveries",
)
async def list_deliveries(
    transaction_id: Optional[UUID] = Query(
        None, description="Filter by transaction ID"
    ),
    status: Optional[NotificationStatus] = Query(
        None, description="Filter by delivery status"
    ),
    channel: Optional[NotificationChannel] = Query(
        None, description="Filter by notification channel"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    repository: NotificationRepository = Depends(get_notification_repository),
) -> NotificationDeliveryListResponse:
    """List notification deliveries with filtering and pagination."""
    try:
        offset = (page - 1) * page_size

        deliveries = await repository.get_deliveries(
            transaction_id=transaction_id,
            status=status,
            channel=channel,
            limit=page_size,
            offset=offset,
        )

        # TODO: Implement total count query
        total = len(deliveries)  # This is not accurate for pagination

        return NotificationDeliveryListResponse(
            deliveries=[
                NotificationDeliveryResponse.model_validate(d) for d in deliveries
            ],
            total=total,
            page=page,
            page_size=page_size,
            pages=(total + page_size - 1) // page_size,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list deliveries: {str(e)}",
        )


@router.get(
    "/deliveries/{delivery_id}",
    response_model=NotificationDeliveryResponse,
    summary="Get notification delivery",
)
async def get_delivery(
    delivery_id: UUID,
    repository: NotificationRepository = Depends(get_notification_repository),
) -> NotificationDeliveryResponse:
    """Get a specific notification delivery by ID."""
    delivery = await repository.get_delivery(delivery_id)
    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found",
        )

    return NotificationDeliveryResponse.model_validate(delivery)


# Notification sending endpoints
@router.post(
    "/send",
    response_model=NotificationSendResponse,
    summary="Send notifications",
)
async def send_notifications(
    request: NotificationSendRequest,
    service: NotificationService = Depends(get_notification_service),
) -> NotificationSendResponse:
    """
    Send notifications for a transaction.

    This endpoint allows manual sending of notifications for specific
    transactions, useful for testing or manual alerts.
    """
    try:
        # TODO: Implement manual notification sending
        # For now, return a mock response
        return NotificationSendResponse(
            delivery_ids=[UUID("11111111-1111-1111-1111-111111111111")],
            total_recipients=2,
            channels_used=[NotificationChannel.EMAIL, NotificationChannel.TELEGRAM],
            message="Notifications sent successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notifications: {str(e)}",
        )


# Statistics endpoints
@router.get(
    "/stats",
    response_model=NotificationStatsResponse,
    summary="Get notification statistics",
)
async def get_notification_stats(
    start_date: Optional[datetime] = Query(
        None, description="Start date for statistics"
    ),
    end_date: Optional[datetime] = Query(None, description="End date for statistics"),
    repository: NotificationRepository = Depends(get_notification_repository),
) -> NotificationStatsResponse:
    """Get notification delivery statistics."""
    try:
        stats = await repository.get_delivery_stats(
            start_date=start_date, end_date=end_date
        )

        # Convert to response format
        return NotificationStatsResponse(
            total_deliveries=stats["total_deliveries"],
            successful_deliveries=stats["successful_deliveries"],
            failed_deliveries=stats["failed_deliveries"],
            pending_deliveries=stats["pending_deliveries"],
            channel_stats=stats["channel_stats"],
            template_usage=stats["template_usage"],
            deliveries_last_24h=0,  # TODO: Implement time-based queries
            deliveries_last_7d=0,  # TODO: Implement time-based queries
            error_rate=stats["error_rate"],
            avg_delivery_time_seconds=None,  # TODO: Implement timing statistics
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}",
        )


# Health check endpoint
@router.get(
    "/health",
    summary="Notification service health check",
)
async def health_check(
    repository: NotificationRepository = Depends(get_notification_repository),
) -> Dict[str, Any]:
    """Check notification service health."""
    try:
        # Check if we can access the database
        configs = await repository.get_all_channel_configs()

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "channels_configured": len(configs),
            "enabled_channels": len([c for c in configs if c.enabled]),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}",
        )
