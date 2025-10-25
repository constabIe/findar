"""
Telegram bot message handlers.

Contains handlers for bot commands and messages.
"""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from src.core.logging import get_logger
from src.modules.users.repository import UserRepository
from src.storage.sql import get_async_session

logger = get_logger("bot.handlers")

# Create router for handlers
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """
    Handle /start command.
    
    Checks if user is registered and provides appropriate response.
    """
    telegram_id = message.from_user.id
    username = message.from_user.username
    
    logger.info(
        "Received /start command",
        component="telegram_bot",
        telegram_id=telegram_id,
        username=username,
    )
    
    try:
        # Get database session
        async for session in get_async_session():
            user_repo = UserRepository(session)
            
            # Check if user exists by telegram_id
            user = await user_repo.get_user_by_telegram_id(telegram_id)
            
            if user:
                # User is registered
                await message.answer(
                    f"✅ Привет, {message.from_user.first_name}!\n\n"
                    f"Ты уже зарегистрирован в системе Findar.\n"
                    f"Email: {user.email}\n\n"
                    f"Ты будешь получать уведомления о подозрительных транзакциях на этот Telegram аккаунт."
                )
                logger.info(
                    "User already registered",
                    component="telegram_bot",
                    telegram_id=telegram_id,
                    user_id=str(user.id),
                )
            else:
                # User NOT registered
                await message.answer(
                    f"👋 Привет, {message.from_user.first_name}!\n\n"
                    f"Ты ещё не зарегистрирован в системе Findar.\n\n"
                    f"Пожалуйста, пройди регистрацию на сайте:\n"
                    f"https://findar.example.com/register\n\n"
                    f"Затем возвращайся и снова напиши /start"
                )
                logger.info(
                    "User not registered, sent registration instructions",
                    component="telegram_bot",
                    telegram_id=telegram_id,
                )
            
            break  # Exit async generator
            
    except Exception as e:
        logger.exception(
            "Error handling /start command",
            component="telegram_bot",
            telegram_id=telegram_id,
        )
        await message.answer(
            "❌ Произошла ошибка при обработке команды.\n"
            f"Попробуй позже или обратись в поддержку. {e}"
        )


@router.message()
async def handle_unknown_message(message: Message) -> None:
    """Handle all other messages."""
    await message.answer(
        "ℹ️ Я бот для уведомлений о фродовых транзакциях.\n\n"
        "Доступные команды:\n"
        "/start - Проверить статус регистрации"
    )
