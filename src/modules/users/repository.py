"""
Repository layer for user operations.

Provides CRUD operations for user management including
registration, authentication, and user data retrieval.
"""

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
            select(User).where(User.email == email) # type: ignore
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
        select(User).where(User.id == user_id) # type: ignore
        )
        return result.scalar_one_or_none()

    async def get_user_by_telegram_alias(
        self, telegram_alias: str
    ) -> Optional[User]:
        """
        Get user by Telegram alias.

        Args:
            telegram_alias: Telegram username (without @)

        Returns:
            User object if found, None otherwise
        """
        result = await self.db.execute(
            select(User).where(User.telegram_alias == telegram_alias.lower()) # type: ignore
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
