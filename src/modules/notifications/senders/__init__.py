"""
Notification senders package.

Contains implementations of different notification channel senders:
- EmailSender: Email notifications via SMTP
- TelegramSender: Telegram notifications via aiogram Bot API
"""

from .base import BaseSender
from .email import EmailSender
from .telegram import TelegramSender

__all__ = [
    "BaseSender",
    "EmailSender",
    "TelegramSender",
]
