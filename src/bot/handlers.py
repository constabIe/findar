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
    if not message.from_user:
        logger.warning("Received message without from_user", component="telegram_bot")
        return

    telegram_id = message.from_user.id
    username = message.from_user.username

    print("HEREEE", username)

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

            # Check if user exists by telegram alias (username)
            user = await user_repo.get_user_by_telegram_alias(username)
            print("CURR_USER", user, username)

            if user:
                # User found in DB - update telegram_id if needed
                if user.telegram_id != telegram_id:
                    # Update telegram_id
                    updated_user = await user_repo.update_user_telegram_id(
                        user.id, telegram_id
                    )
                    if updated_user:
                        await message.answer(
                            f"✅ Привет, {username}!\n\n"
                            f"Твой Telegram ID успешно привязан к аккаунту Findar.\n"
                            f"Email: {updated_user.email}\n\n"
                            f"Теперь ты будешь получать уведомления о подозрительных транзакциях на этот Telegram аккаунт."
                        )
                        logger.info(
                            "Telegram ID updated for user",
                            component="telegram_bot",
                            telegram_id=telegram_id,
                            user_id=str(updated_user.id),
                            telegram_alias=username,
                        )
                else:
                    # telegram_id already set
                    await message.answer(
                        f"✅ Привет, {username}!\n\n"
                        f"Ты уже зарегистрирован в системе Findar.\n"
                        f"Email: {user.email}\n\n"
                        f"Ты будешь получать уведомления о подозрительных транзакциях на этот Telegram аккаунт."
                    )
                    logger.info(
                        "User already registered with correct telegram_id",
                        component="telegram_bot",
                        telegram_id=telegram_id,
                        user_id=str(user.id),
                        telegram_alias=username,
                    )
            else:
                # User NOT found in DB by alias
                await message.answer(
                    f"👋 Привет, {username}!\n\n"
                    f"Пользователь с username @{username} не найден в системе Findar.\n\n"
                    f"Пожалуйста, пройди регистрацию на сайте:\n"
                    f"https://findar.example.com/register\n\n"
                    f"⚠️ Важно: при регистрации укажи telegram alias: @{username}\n\n"
                    f"После регистрации возвращайся и снова напиши /start"
                )
                logger.info(
                    "User not found by telegram alias, sent registration instructions",
                    component="telegram_bot",
                    telegram_id=telegram_id,
                    telegram_alias=username,
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
