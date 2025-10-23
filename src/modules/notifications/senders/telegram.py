"""
Telegram notification sender using aiogram.

Sends notifications to Telegram chats using the Bot API through aiogram library.
"""

from typing import Any, Dict, List, Optional, Tuple

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError

from src.config import settings
from src.core.logging import get_logger

from .base import BaseSender

logger = get_logger("notifications.telegram")


class TelegramSender(BaseSender):
    """
    Telegram notification sender.

    Sends messages to Telegram chats using aiogram Bot API.
    Uses bot token from configuration settings.
    """

    def __init__(self) -> None:
        """Initialize Telegram sender with bot token from settings."""
        self.bot_token = settings.notifications.TELEGRAM_BOT_TOKEN
        self._bot: Optional[Bot] = None

    def _get_bot(self) -> Bot:
        """
        Get or create Bot instance.

        Returns:
            Bot instance configured with token
        """
        if not self._bot:
            if not self.bot_token:
                raise ValueError("TELEGRAM_BOT_TOKEN not configured")
            self._bot = Bot(token=self.bot_token)
        return self._bot

    async def send(
        self,
        recipients: List[str],
        message: str,
        config: Dict[str, Any],
        subject: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Send message to Telegram chats.

        Args:
            recipients: List of chat IDs (as strings)
            message: Message text to send
            config: Telegram-specific configuration (parse_mode, etc.)
            subject: Not used for Telegram (optional)

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        if not recipients:
            return False, "no_recipients"

        try:
            bot = self._get_bot()
            parse_mode = config.get("parse_mode", "HTML")

            # Convert parse_mode string to ParseMode enum
            if parse_mode.upper() == "HTML":
                parse_mode_enum = ParseMode.HTML
            elif parse_mode.upper() == "MARKDOWN":
                parse_mode_enum = ParseMode.MARKDOWN
            else:
                parse_mode_enum = None

            success_count = 0
            failed_chats = []

            # Send to each chat
            for chat_id in recipients:
                try:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode=parse_mode_enum,
                    )
                    success_count += 1
                    logger.debug(
                        "Telegram message sent",
                        component="notifications",
                        event="telegram_sent",
                        chat_id=chat_id,
                    )
                except TelegramAPIError as e:
                    failed_chats.append(chat_id)
                    logger.warning(
                        "Failed to send Telegram message to chat",
                        component="notifications",
                        event="telegram_send_failed",
                        chat_id=chat_id,
                        error=str(e),
                    )
                except Exception:
                    failed_chats.append(chat_id)
                    logger.exception(
                        "Unexpected error sending Telegram message",
                        component="notifications",
                        event="telegram_unexpected_error",
                        chat_id=chat_id,
                    )

            # Determine overall success
            if success_count == len(recipients):
                logger.info(
                    "All Telegram messages sent successfully",
                    component="notifications",
                    event="telegram_all_sent",
                    total=len(recipients),
                )
                return True, None
            elif success_count > 0:
                error_msg = f"telegram_partial:{success_count}/{len(recipients)}"
                logger.warning(
                    "Partial Telegram delivery",
                    component="notifications",
                    event="telegram_partial",
                    success=success_count,
                    total=len(recipients),
                    failed_chats=failed_chats,
                )
                return False, error_msg
            else:
                error_msg = "telegram_all_failed"
                logger.error(
                    "All Telegram messages failed",
                    component="notifications",
                    event="telegram_all_failed",
                    total=len(recipients),
                )
                return False, error_msg

        except ValueError as e:
            logger.error(
                "Telegram configuration error",
                component="notifications",
                event="telegram_config_error",
                error=str(e),
            )
            return False, str(e)
        except Exception as e:
            logger.exception(
                "Telegram sender unexpected error",
                component="notifications",
                event="telegram_sender_error",
            )
            return False, str(e)

    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate Telegram configuration.

        Args:
            config: Configuration to validate

        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        if not self.bot_token:
            return False, "TELEGRAM_BOT_TOKEN not configured"

        # Validate parse_mode if provided
        if "parse_mode" in config:
            parse_mode = config["parse_mode"]
            if parse_mode and parse_mode.upper() not in [
                "HTML",
                "MARKDOWN",
                "MARKDOWNV2",
            ]:
                return False, f"Invalid parse_mode: {parse_mode}"

        return True, None

    def get_channel_name(self) -> str:
        """
        Get channel name.

        Returns:
            "telegram"
        """
        return "telegram"

    async def close(self) -> None:
        """
        Close bot session.

        Should be called when shutting down the application.
        """
        if self._bot:
            await self._bot.session.close()
            self._bot = None
            logger.debug(
                "Telegram bot session closed",
                component="notifications",
                event="telegram_closed",
            )
