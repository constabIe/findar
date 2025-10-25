"""
User notification settings routes.

Provides API endpoints for users to manage their notification templates
and channel settings (email/telegram).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.modules.notifications.repository import NotificationRepository
from src.modules.notifications.schemas import (
    NotificationChannelsResponse,
    NotificationChannelsUpdate,
    TemplateFieldsUpdate,
    UserNotificationTemplateResponse,
    UserNotificationTemplatesResponse,
)
from src.modules.users.dependencies import get_current_user
from src.modules.users.repository import UserRepository
from src.storage.dependencies import get_db_session
from src.storage.models import User

logger = get_logger("users.notifications_routes")

router = APIRouter(prefix="/users/notifications", tags=["user-notifications"])


@router.get(
    "/templates/",
    response_model=UserNotificationTemplatesResponse,
    summary="Get user's notification templates",
)
async def get_user_templates(
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> UserNotificationTemplatesResponse:
    """
    Get current user's email and telegram notification templates.

    Returns both templates with their field visibility settings.
    """
    notification_repo = NotificationRepository(db_session)

    # Get email template
    email_template_id = getattr(current_user, "email_template_id", None)
    if not email_template_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email template not found. Please contact support.",
        )

    email_template = await notification_repo.get_template(email_template_id)
    if not email_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email template not found in database.",
        )

    # Get telegram template
    telegram_template_id = getattr(current_user, "telegram_template_id", None)
    if not telegram_template_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Telegram template not found. Please contact support.",
        )

    telegram_template = await notification_repo.get_template(telegram_template_id)
    if not telegram_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Telegram template not found in database.",
        )

    return UserNotificationTemplatesResponse(
        email_template=UserNotificationTemplateResponse.model_validate(email_template),
        telegram_template=UserNotificationTemplateResponse.model_validate(
            telegram_template
        ),
    )


@router.patch(
    "/templates/email",
    response_model=UserNotificationTemplateResponse,
    summary="Update email template fields",
)
async def update_email_template(
    fields: TemplateFieldsUpdate,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> UserNotificationTemplateResponse:
    """
    Update email template field visibility settings.

    Only updates the show_* fields that control which information
    is included in email notifications.
    """
    email_template_id = getattr(current_user, "email_template_id", None)
    if not email_template_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email template not found.",
        )

    notification_repo = NotificationRepository(db_session)

    # Update template fields
    fields_dict = fields.model_dump(exclude_unset=True)
    updated_template = await notification_repo.update_template_fields(
        email_template_id, fields_dict
    )

    if not updated_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found or update failed.",
        )

    logger.info(
        f"User {current_user.id} updated email template fields",
        user_id=str(current_user.id),
        updated_fields=list(fields_dict.keys()),
    )

    return UserNotificationTemplateResponse.model_validate(updated_template)


@router.patch(
    "/templates/telegram",
    response_model=UserNotificationTemplateResponse,
    summary="Update telegram template fields",
)
async def update_telegram_template(
    fields: TemplateFieldsUpdate,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> UserNotificationTemplateResponse:
    """
    Update telegram template field visibility settings.

    Only updates the show_* fields that control which information
    is included in telegram notifications.
    """
    telegram_template_id = getattr(current_user, "telegram_template_id", None)
    if not telegram_template_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Telegram template not found.",
        )

    notification_repo = NotificationRepository(db_session)

    # Update template fields
    fields_dict = fields.model_dump(exclude_unset=True)
    updated_template = await notification_repo.update_template_fields(
        telegram_template_id, fields_dict
    )

    if not updated_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found or update failed.",
        )

    logger.info(
        f"User {current_user.id} updated telegram template fields",
        user_id=str(current_user.id),
        updated_fields=list(fields_dict.keys()),
    )

    return UserNotificationTemplateResponse.model_validate(updated_template)


@router.get(
    "/channels/",
    response_model=NotificationChannelsResponse,
    summary="Get notification channel settings",
)
async def get_notification_channels(
    current_user: User = Depends(get_current_user),
) -> NotificationChannelsResponse:
    """
    Get current user's notification channel settings.

    Returns whether email and telegram notifications are enabled.
    """
    return NotificationChannelsResponse(
        email_enabled=getattr(current_user, "email_notifications_enabled", True),
        telegram_enabled=getattr(current_user, "telegram_notifications_enabled", True),
    )


@router.patch(
    "/channels/",
    response_model=NotificationChannelsResponse,
    summary="Update notification channel settings",
)
async def update_notification_channels(
    settings: NotificationChannelsUpdate,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> NotificationChannelsResponse:
    """
    Enable or disable email/telegram notification channels.

    Allows users to turn on/off notifications for each channel independently.
    """
    user_repo = UserRepository(db_session)

    updated_user = await user_repo.update_notification_channels(
        user_id=current_user.id,
        email_enabled=settings.email_enabled,
        telegram_enabled=settings.telegram_enabled,
    )

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or update failed.",
        )

    logger.info(
        f"User {current_user.id} updated notification channels",
        user_id=str(current_user.id),
        email_enabled=settings.email_enabled,
        telegram_enabled=settings.telegram_enabled,
    )

    return NotificationChannelsResponse(
        email_enabled=updated_user.email_notifications_enabled,
        telegram_enabled=updated_user.telegram_notifications_enabled,
    )
