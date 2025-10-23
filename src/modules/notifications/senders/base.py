"""
Base sender class for notification channels.

Defines the common interface that all notification senders must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class BaseSender(ABC):
    """
    Abstract base class for notification senders.

    All notification channel implementations (Email, Telegram, etc.)
    must inherit from this class and implement the required methods.
    """

    @abstractmethod
    async def send(
        self,
        recipients: List[str],
        message: str,
        config: Dict[str, Any],
        subject: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Send notification to recipients.

        Args:
            recipients: List of recipient addresses/IDs
            message: Message body to send
            config: Channel-specific configuration
            subject: Message subject (optional, for channels that support it)

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
            - (True, None) on success
            - (False, error_message) on failure
        """
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate channel configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        pass

    @abstractmethod
    def get_channel_name(self) -> str:
        """
        Get the name of the notification channel.

        Returns:
            Channel name (e.g., "email", "telegram")
        """
        pass
