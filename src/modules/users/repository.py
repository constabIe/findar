"""
Repository layer for user operations.

Provides CRUD operations for user management including
registration, authentication, and user data retrieval.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.storage.models import User

logger = get_logger("users.repository")


class UserRepository:
    """
    Repository for user CRUD operations.

    Manages user data in PostgreSQL.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            db_session: SQLModel async database session
        """
        self.db = db_session

    async def create_user(
        self,
        email: str,
        hashed_password: str,
        telegram_alias: str,
    ) -> User:
        """
        Create a new user in the database.

        Args:
            email: User's email address
            hashed_password: Pre-hashed password
            telegram_alias: Telegram username (without @)

        Returns:
            Created User object

        Raises:
            IntegrityError: If email or telegram_alias already exists
        """
        user = User(
            email=email,
            hashed_password=hashed_password,
            telegram_alias=telegram_alias,
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        logger.info(f"User created: {user.id} ({user.email})")
        return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.

        Args:
            email: User's email address

        Returns:
            User object if found, None otherwise
        """
        result = await self.db.execute(
            select(User).where(User.email == email)  # type: ignore
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User's unique identifier

        Returns:
            User object if found, None otherwise
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)  # type: ignore
        )
        return result.scalar_one_or_none()

    async def get_user_by_telegram_alias(self, telegram_alias: str) -> Optional[User]:
        """
        Get user by Telegram alias.

        Args:
            telegram_alias: Telegram username (without @)

        Returns:
            User object if found, None otherwise
        """
        result = await self.db.execute(
            select(User).where(User.telegram_alias == telegram_alias.lower())  # type: ignore
        )
        return result.scalar_one_or_none()

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Get user by Telegram ID.

        Args:
            telegram_id: Telegram user ID (numeric)

        Returns:
            User object if found, None otherwise
        """
        result = await self.db.execute(
            select(User).where(User.telegram_id == telegram_id)  # type: ignore
        )
        return result.scalar_one_or_none()

    async def update_user_telegram_id(
        self, user_id: UUID, telegram_id: int
    ) -> Optional[User]:
        """
        Update user's Telegram ID (when bot is started).

        Args:
            user_id: User's unique identifier
            telegram_id: Telegram user ID from bot message

        Returns:
            Updated User object if found, None otherwise
        """
        user = await self.get_user_by_id(user_id)

        if user:
            user.telegram_id = telegram_id
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            logger.info(f"User {user.id} Telegram ID updated: {telegram_id}")

        return user

    async def update_user_telegram_alias(
        self, user_id: UUID, telegram_alias: str
    ) -> Optional[User]:
        """
        Update user's Telegram alias.

        Args:
            user_id: User's unique identifier
            telegram_alias: New Telegram username (without @, lowercase)

        Returns:
            Updated User object if found, None otherwise

        Raises:
            IntegrityError: If telegram_alias already exists for another user
        """
        user = await self.get_user_by_id(user_id)

        if user:
            user.telegram_alias = telegram_alias.lower()
            user.updated_at = datetime.utcnow()
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            logger.info(f"User {user.id} Telegram alias updated: @{telegram_alias}")

        return user

    async def create_default_templates_for_user(
        self, user_id: UUID
    ) -> tuple[UUID, UUID]:
        """
        Create default email and telegram notification templates for a user.

        Args:
            user_id: User ID to create templates for

        Returns:
            Tuple of (email_template_id, telegram_template_id)
        """
        from src.modules.notifications.enums import NotificationChannel, TemplateType
        from src.storage.models import NotificationTemplate

        # Create default email template
        email_template = NotificationTemplate(
            name=f"User {user_id} - Email Template",
            type=TemplateType.FRAUD_ALERT,
            channel=NotificationChannel.EMAIL,
            subject_template="Fraud Alert: Rule Violation Detected",
            body_template=(
                "Hello,\n\n"
                "Your fraud detection rule was triggered.\n\n"
                "Transaction ID: {transaction_id}\n"
                "Amount: {amount} {currency}\n"
                "Timestamp: {timestamp}\n"
                "From Account: {from_account}\n"
                "To Account: {to_account}\n"
                "Triggered Rules: {triggered_rules}\n"
                "Risk Level: {overall_risk_level}\n\n"
                "Please review this transaction in the admin panel.\n\n"
                "Regards,\nFindar Fraud Detection System"
            ),
            enabled=True,
            priority=1,
            show_transaction_id=True,
            show_amount=True,
            show_timestamp=True,
            show_from_account=True,
            show_to_account=True,
            show_triggered_rules=True,
            show_fraud_probability=True,
            show_location=True,
            show_device_info=True,
            description="Default email notification template",
        )

        # Create default telegram template
        telegram_template = NotificationTemplate(
            name=f"User {user_id} - Telegram Template",
            type=TemplateType.FRAUD_ALERT,
            channel=NotificationChannel.TELEGRAM,
            subject_template=None,
            body_template=(
                "🚨 *Fraud Alert*\n\n"
                "Transaction ID: `{transaction_id}`\n"
                "Amount: *{amount} {currency}*\n"
                "Time: {timestamp}\n"
                "From: {from_account}\n"
                "To: {to_account}\n"
                "Rules: {triggered_rules}\n"
                "Risk: *{overall_risk_level}*"
            ),
            enabled=True,
            priority=1,
            show_transaction_id=True,
            show_amount=True,
            show_timestamp=True,
            show_from_account=True,
            show_to_account=True,
            show_triggered_rules=True,
            show_fraud_probability=True,
            show_location=True,
            show_device_info=True,
            description="Default Telegram notification template",
        )

        self.db.add(email_template)
        self.db.add(telegram_template)
        await self.db.commit()
        await self.db.refresh(email_template)
        await self.db.refresh(telegram_template)

        logger.info(
            f"Created default templates for user {user_id}: "
            f"email={email_template.id}, telegram={telegram_template.id}"
        )

        return email_template.id, telegram_template.id

    async def update_notification_channels(
        self,
        user_id: UUID,
        email_enabled: Optional[bool] = None,
        telegram_enabled: Optional[bool] = None,
    ) -> Optional[User]:
        """
        Update user's notification channel settings.

        Args:
            user_id: User ID
            email_enabled: Enable/disable email notifications (optional)
            telegram_enabled: Enable/disable telegram notifications (optional)

        Returns:
            Updated User object if found, None otherwise
        """
        user = await self.get_user_by_id(user_id)

        if user:
            if email_enabled is not None:
                user.email_notifications_enabled = email_enabled
            if telegram_enabled is not None:
                user.telegram_notifications_enabled = telegram_enabled

            user.updated_at = datetime.utcnow()
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)

            logger.info(
                f"User {user_id} notification channels updated: "
                f"email={user.email_notifications_enabled}, "
                f"telegram={user.telegram_notifications_enabled}"
            )

        return user

    async def link_templates_to_user(
        self, user_id: UUID, email_template_id: UUID, telegram_template_id: UUID
    ) -> Optional[User]:
        """
        Link notification templates to a user.

        Args:
            user_id: User ID
            email_template_id: Email template ID
            telegram_template_id: Telegram template ID

        Returns:
            Updated User object if found, None otherwise
        """
        user = await self.get_user_by_id(user_id)

        if user:
            user.email_template_id = email_template_id
            user.telegram_template_id = telegram_template_id
            user.updated_at = datetime.utcnow()

            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)

            logger.info(
                f"Templates linked to user {user_id}: "
                f"email={email_template_id}, telegram={telegram_template_id}"
            )

        return user
