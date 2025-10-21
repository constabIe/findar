"""
Repository for notification database operations.

Provides data access methods for notification templates, channel configurations,
delivery tracking, and related database operations.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

if TYPE_CHECKING:
    from sqlalchemy import and_, desc, func, select, update  # pragma: no cover
    from sqlalchemy.ext.asyncio import AsyncSession  # pragma: no cover
    from sqlmodel import select as sqlmodel_select  # pragma: no cover
else:
    # Runtime imports are available in the app environment; provide fallbacks for editors
    and_ = desc = func = select = update = object
    AsyncSession = Any
    sqlmodel_select = lambda *a, **k: None

from src.modules.notifications.enums import (
    NotificationChannel,
    NotificationStatus,
    TemplateType,
)
from src.modules.notifications.models import (
    NotificationChannelConfig,
    NotificationDelivery,
    NotificationDeliveryAttempt,
    NotificationTemplate,
)
from src.modules.notifications.schemas import (
    NotificationChannelConfigCreate,
    NotificationDeliveryCreate,
    NotificationTemplateCreate,
    NotificationTemplateUpdate,
)


class NotificationRepository:
    """
    Repository for notification-related database operations.

    Handles CRUD operations for templates, channel configurations,
    delivery tracking, and statistics queries.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize notification repository.

        Args:
            db_session: Database session for operations
        """
        self.db_session = db_session

    # Template operations
    async def create_template(
        self, template_data: NotificationTemplateCreate
    ) -> NotificationTemplate:
        """
        Create a new notification template.

        Args:
            template_data: Template creation data

        Returns:
            Created template
        """
        template = NotificationTemplate(
            name=template_data.name,
            type=template_data.type,
            channel=template_data.channel,
            subject_template=template_data.subject_template,
            body_template=template_data.body_template,
            enabled=template_data.enabled,
            priority=template_data.priority,
            include_transaction_id=template_data.include_transaction_id,
            include_amount=template_data.include_amount,
            include_timestamp=template_data.include_timestamp,
            include_from_account=template_data.include_from_account,
            include_to_account=template_data.include_to_account,
            include_triggered_rules=template_data.include_triggered_rules,
            include_fraud_probability=template_data.include_fraud_probability,
            include_location=template_data.include_location,
            include_device_info=template_data.include_device_info,
            custom_fields=template_data.custom_fields,
            description=template_data.description,
        )

        self.db_session.add(template)
        await self.db_session.commit()
        await self.db_session.refresh(template)

        return template

    async def get_template(self, template_id: UUID) -> Optional[NotificationTemplate]:
        """Get template by ID."""
        result = await self.db_session.execute(
            sqlmodel_select(NotificationTemplate).where(
                NotificationTemplate.id == template_id
            )
        )
        return result.scalar_one_or_none()

    async def get_templates(
        self,
        template_type: Optional[TemplateType] = None,
        channel: Optional[NotificationChannel] = None,
        enabled_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> List[NotificationTemplate]:
        """
        Get templates with filtering options.

        Args:
            template_type: Filter by template type
            channel: Filter by notification channel
            enabled_only: Only return enabled templates
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of templates
        """
        query = sqlmodel_select(NotificationTemplate)

        if template_type:
            query = query.where(NotificationTemplate.type == template_type)

        if channel:
            query = query.where(NotificationTemplate.channel == channel)

        if enabled_only:
            query = query.where(NotificationTemplate.enabled == True)

        query = query.order_by(
            desc(NotificationTemplate.priority), desc(NotificationTemplate.created_at)
        )
        query = query.limit(limit).offset(offset)

        result = await self.db_session.execute(query)
        return result.scalars().all()

    async def update_template(
        self, template_id: UUID, update_data: NotificationTemplateUpdate
    ) -> Optional[NotificationTemplate]:
        """Update template."""
        template = await self.get_template(template_id)
        if not template:
            return None

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(template, field, value)

        template.updated_at = datetime.utcnow()

        await self.db_session.commit()
        await self.db_session.refresh(template)

        return template

    async def delete_template(self, template_id: UUID) -> bool:
        """Delete template."""
        template = await self.get_template(template_id)
        if not template:
            return False

        await self.db_session.delete(template)
        await self.db_session.commit()

        return True

    async def increment_template_usage(self, template_id: UUID) -> None:
        """Increment template usage counter."""
        await self.db_session.execute(
            update(NotificationTemplate)
            .where(NotificationTemplate.id == template_id)
            .values(usage_count=NotificationTemplate.usage_count + 1)
        )
        await self.db_session.commit()

    # Channel configuration operations
    async def create_channel_config(
        self, config_data: NotificationChannelConfigCreate
    ) -> NotificationChannelConfig:
        """Create channel configuration."""
        config = NotificationChannelConfig(
            channel=config_data.channel,
            enabled=config_data.enabled,
            config=config_data.config,
            max_retries=config_data.max_retries,
            retry_delay_seconds=config_data.retry_delay_seconds,
            rate_limit_per_minute=config_data.rate_limit_per_minute,
            description=config_data.description,
        )

        self.db_session.add(config)
        await self.db_session.commit()
        await self.db_session.refresh(config)

        return config

    async def get_channel_config(
        self, channel: NotificationChannel
    ) -> Optional[NotificationChannelConfig]:
        """Get channel configuration."""
        result = await self.db_session.execute(
            sqlmodel_select(NotificationChannelConfig).where(
                NotificationChannelConfig.channel == channel
            )
        )
        return result.scalar_one_or_none()

    async def get_all_channel_configs(self) -> List[NotificationChannelConfig]:
        """Get all channel configurations."""
        result = await self.db_session.execute(
            sqlmodel_select(NotificationChannelConfig)
        )
        return result.scalars().all()

    async def update_channel_config(
        self, channel: NotificationChannel, config_data: Dict[str, Any]
    ) -> Optional[NotificationChannelConfig]:
        """Update channel configuration."""
        config = await self.get_channel_config(channel)
        if not config:
            return None

        for field, value in config_data.items():
            if hasattr(config, field):
                setattr(config, field, value)

        config.updated_at = datetime.utcnow()

        await self.db_session.commit()
        await self.db_session.refresh(config)

        return config

    # Delivery operations
    async def create_delivery(
        self, delivery_data: NotificationDeliveryCreate
    ) -> NotificationDelivery:
        """Create notification delivery record."""
        delivery = NotificationDelivery(
            transaction_id=delivery_data.transaction_id,
            template_id=delivery_data.template_id,
            channel=delivery_data.channel,
            subject=delivery_data.subject,
            body=delivery_data.body,
            recipients=delivery_data.recipients,
            priority=delivery_data.priority,
            scheduled_at=delivery_data.scheduled_at,
            metadata_=delivery_data.metadata,
            status=NotificationStatus.PENDING,
            max_attempts=3,  # Default value
        )

        self.db_session.add(delivery)
        await self.db_session.commit()
        await self.db_session.refresh(delivery)

        return delivery

    async def get_delivery(self, delivery_id: UUID) -> Optional[NotificationDelivery]:
        """Get delivery by ID."""
        result = await self.db_session.execute(
            sqlmodel_select(NotificationDelivery).where(
                NotificationDelivery.id == delivery_id
            )
        )
        return result.scalar_one_or_none()

    async def get_deliveries(
        self,
        transaction_id: Optional[UUID] = None,
        status: Optional[NotificationStatus] = None,
        channel: Optional[NotificationChannel] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[NotificationDelivery]:
        """Get deliveries with filtering."""
        query = sqlmodel_select(NotificationDelivery)

        if transaction_id:
            query = query.where(NotificationDelivery.transaction_id == transaction_id)

        if status:
            query = query.where(NotificationDelivery.status == status)

        if channel:
            query = query.where(NotificationDelivery.channel == channel)

        query = query.order_by(desc(NotificationDelivery.created_at))
        query = query.limit(limit).offset(offset)

        result = await self.db_session.execute(query)
        return result.scalars().all()

    async def update_delivery_status(
        self,
        delivery_id: UUID,
        status: NotificationStatus,
        error_message: Optional[str] = None,
    ) -> Optional[NotificationDelivery]:
        """Update delivery status."""
        delivery = await self.get_delivery(delivery_id)
        if not delivery:
            return None

        delivery.status = status
        delivery.error_message = error_message

        if status == NotificationStatus.DELIVERED:
            delivery.delivered_at = datetime.utcnow()
        elif status == NotificationStatus.FAILED:
            delivery.failed_at = datetime.utcnow()

        delivery.updated_at = datetime.utcnow()

        await self.db_session.commit()
        await self.db_session.refresh(delivery)

        return delivery

    async def increment_delivery_attempt(self, delivery_id: UUID) -> None:
        """Increment delivery attempt counter."""
        await self.db_session.execute(
            update(NotificationDelivery)
            .where(NotificationDelivery.id == delivery_id)
            .values(attempts=NotificationDelivery.attempts + 1)
        )
        await self.db_session.commit()

    # Delivery attempt operations
    async def create_delivery_attempt(
        self,
        delivery_id: UUID,
        attempt_number: int,
        success: bool,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        response_status: Optional[str] = None,
        response_body: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> NotificationDeliveryAttempt:
        """Create delivery attempt record."""
        attempt = NotificationDeliveryAttempt(
            delivery_id=delivery_id,
            attempt_number=attempt_number,
            success=success,
            error_message=error_message,
            error_code=error_code,
            response_status=response_status,
            response_body=response_body,
            metadata_=metadata or {},
            completed_at=datetime.utcnow(),
        )

        # Calculate duration if we have start time
        if metadata and "started_at" in metadata:
            start_time = datetime.fromisoformat(metadata["started_at"])
            duration = (attempt.completed_at - start_time).total_seconds() * 1000
            attempt.duration_ms = int(duration)

        self.db_session.add(attempt)
        await self.db_session.commit()
        await self.db_session.refresh(attempt)

        return attempt

    # Statistics operations
    async def get_delivery_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get delivery statistics."""
        query = sqlmodel_select(NotificationDelivery)

        if start_date:
            query = query.where(NotificationDelivery.created_at >= start_date)

        if end_date:
            query = query.where(NotificationDelivery.created_at <= end_date)

        result = await self.db_session.execute(query)
        deliveries = result.scalars().all()

        # Calculate statistics
        total_deliveries = len(deliveries)
        successful_deliveries = sum(
            1 for d in deliveries if d.status == NotificationStatus.DELIVERED
        )
        failed_deliveries = sum(
            1 for d in deliveries if d.status == NotificationStatus.FAILED
        )
        pending_deliveries = sum(
            1 for d in deliveries if d.status == NotificationStatus.PENDING
        )

        # Channel-specific stats
        channel_stats = {}
        for channel in NotificationChannel:
            channel_deliveries = [d for d in deliveries if d.channel == channel]
            channel_stats[channel] = {
                "total": len(channel_deliveries),
                "successful": sum(
                    1
                    for d in channel_deliveries
                    if d.status == NotificationStatus.DELIVERED
                ),
                "failed": sum(
                    1
                    for d in channel_deliveries
                    if d.status == NotificationStatus.FAILED
                ),
                "pending": sum(
                    1
                    for d in channel_deliveries
                    if d.status == NotificationStatus.PENDING
                ),
            }

        # Template usage stats
        template_usage = {}
        for delivery in deliveries:
            template_id = str(delivery.template_id)
            template_usage[template_id] = template_usage.get(template_id, 0) + 1

        # Error rate
        error_rate = (
            failed_deliveries / total_deliveries if total_deliveries > 0 else 0.0
        )

        return {
            "total_deliveries": total_deliveries,
            "successful_deliveries": successful_deliveries,
            "failed_deliveries": failed_deliveries,
            "pending_deliveries": pending_deliveries,
            "channel_stats": channel_stats,
            "template_usage": template_usage,
            "error_rate": error_rate,
        }

    async def get_pending_deliveries(
        self, limit: int = 100
    ) -> List[NotificationDelivery]:
        """Get pending deliveries for processing."""
        query = sqlmodel_select(NotificationDelivery).where(
            and_(
                NotificationDelivery.status == NotificationStatus.PENDING,
                NotificationDelivery.attempts < NotificationDelivery.max_attempts,
                NotificationDelivery.scheduled_at <= datetime.utcnow(),
            )
        )

        query = query.order_by(
            NotificationDelivery.priority.desc(), NotificationDelivery.created_at
        )
        query = query.limit(limit)

        result = await self.db_session.execute(query)
        return result.scalars().all()

    async def get_failed_deliveries_for_retry(
        self, limit: int = 100
    ) -> List[NotificationDelivery]:
        """Get failed deliveries that can be retried."""
        query = sqlmodel_select(NotificationDelivery).where(
            and_(
                NotificationDelivery.status == NotificationStatus.FAILED,
                NotificationDelivery.attempts < NotificationDelivery.max_attempts,
            )
        )

        query = query.order_by(NotificationDelivery.created_at)
        query = query.limit(limit)

        result = await self.db_session.execute(query)
        return result.scalars().all()
