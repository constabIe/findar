"""
Telegram bot application setup and startup.

Main bot initialization and polling loop.
"""

from aiogram import Bot, Dispatcher

from src.config import settings
from src.core.logging import get_logger

from .handlers import router

logger = get_logger("bot.app")


async def start_bot() -> None:
    """
    Start the Telegram bot with long polling.
    
    This function should be run as a separate service/process.
    """
    if not settings.notifications.TELEGRAM_BOT_TOKEN:
        logger.error(
            "TELEGRAM_BOT_TOKEN not configured, bot cannot start",
            component="telegram_bot",
        )
        return
    
    bot = Bot(token=settings.notifications.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    
    # Register router with handlers
    dp.include_router(router)
    
    logger.info("Starting Telegram bot", component="telegram_bot")
    
    try:
        # Delete webhook if exists (for polling mode)
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Start polling
        await dp.start_polling(bot)
    except Exception:
        logger.exception("Error running Telegram bot", component="telegram_bot")
    finally:
        await bot.session.close()
