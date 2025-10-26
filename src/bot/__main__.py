"""
Entry point for running Telegram bot as a module.

Usage:
    python -m src.bot
"""

import asyncio

from src.bot import start_bot

if __name__ == "__main__":
    asyncio.run(start_bot())
