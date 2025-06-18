from aiogram import Router, types, Bot
from aiogram.filters import Command
from bot.core.database import get_async_session
from bot.repositories.group_user_repo import GroupUserRepository
from bot.utils.decorators import group_chat_only
from bot.utils.logger import setup_logger
import pendulum
import asyncio

logger = setup_logger(__name__)
router = Router()

# Текстовые сообщения
HERO_COMMAND_SUCCESS_MESSAGE = "🏆 Герой дня: @{username}!"
HERO_COMMAND_NO_HERO_MESSAGE = "❌ Герой дня ещё не выбран. Ждите выборов в 10:00!"
HERO_COMMAND_ERROR_MESSAGE = "❌ Произошла ошибка. Попробуйте позже."
GROUP_ADDED_MESSAGE = (
    "👋 Группа зарегистрирована! Теперь я буду выбирать Героя Дня каждый день в 10:00!\n"
    "Пользователи могут зарегистрироваться как кандидаты с помощью /become_hero."
)
USER_REGISTERED_MESSAGE = (
    "✅ Вы зарегистрированы как кандидат на Героя Дня! Ждите своего звездного часа!"
)
USER_ALREADY_CANDIDATE_MESSAGE = "ℹ️ Вы уже зарегистрированы как кандидат на Героя Дня!"
USER_NOT_FOUND_MESSAGE = (
    "❌ Вы не зарегистрированы в системе. Нажмите кнопку ниже, чтобы начать!"
)


@router.message(Command("hero"))
@group_chat_only(response_probability=1.0)
async def hero_command_handler(message: types.Message, bot: Bot):
    try:
        chat_id = message.chat.id
        chat_title = message.chat.title or f"Group {chat_id}"

        # Регистрируем группу
        async for session in get_async_session():
            group = await GroupUserRepository.get_group_by_chat_id(session, chat_id)
            if not group:
                logger.info(
                    f"Registering new group: chat_id={chat_id}, title={chat_title}"
                )
                await GroupUserRepository.add_group(session, chat_id, chat_title)
                await bot.send_message(
                    chat_id=chat_id,
                    text=GROUP_ADDED_MESSAGE,
                )
                logger.info(f"Group registered in database: chat_id={chat_id}")
            else:
                await bot.send_message(
                    chat_id=chat_id,
                    text="✅ Группа уже зарегистрирована!",
                )
                logger.debug(f"Group already registered: chat_id={chat_id}")
    except Exception as e:
        logger.error(f"Error in hero command handler: {e}", exc_info=True)
        await bot.send_message(
            chat_id=chat_id,
            text=HERO_COMMAND_ERROR_MESSAGE,
        )


@router.message(Command("hero_today"))
@group_chat_only(response_probability=1.0)
async def hero_today_handler(message: types.Message, bot: Bot):
    try:
        chat_id = message.chat.id

        async for session in get_async_session():
            today = pendulum.now("Europe/Moscow").date()
            hero = await GroupUserRepository.get_hero_of_the_day(
                session, chat_id, today
            )
            if hero:
                user = await GroupUserRepository.get_user_by_id(session, hero.user_id)
                await bot.send_message(
                    chat_id=chat_id,
                    text=HERO_COMMAND_SUCCESS_MESSAGE.format(
                        username=user.username or user.name
                    ),
                )
            else:
                await bot.send_message(
                    chat_id=chat_id,
                    text=HERO_COMMAND_NO_HERO_MESSAGE,
                )
    except Exception as e:
        logger.error(f"Error in hero_today handler: {e}", exc_info=True)
        await bot.send_message(
            chat_id=chat_id,
            text=HERO_COMMAND_ERROR_MESSAGE,
        )


@router.message(Command("become_hero"))
@group_chat_only(response_probability=1.0)
async def become_hero_handler(message: types.Message, bot: Bot):
    try:
        chat_id = message.chat.id
        telegram_id = message.from_user.id
        username = message.from_user.username
        name = message.from_user.first_name or f"User {telegram_id}"

        async for session in get_async_session():
            # Проверяем группу
            group = await GroupUserRepository.get_group_by_chat_id(session, chat_id)
            if not group:
                await bot.send_message(
                    chat_id=chat_id,
                    text="❌ Группа не зарегистрирована. Сначала выполните /hero.",
                )
                return

            # Проверяем, есть ли пользователь в users и завершена ли регистрация
            user = await GroupUserRepository.get_user_by_telegram_id(
                session, telegram_id
            )
            if not user or not user.name or not user.birth_date:
                bot_info = await bot.get_me()
                bot_username = f"@{bot_info.username}"
                deep_link = f"t.me/{bot_username}?start=group_{chat_id}"
                await bot.send_message(
                    chat_id=chat_id,
                    text=USER_NOT_FOUND_MESSAGE,
                    reply_markup=types.InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                types.InlineKeyboardButton(
                                    text="Начать с ботом", url=deep_link
                                )
                            ]
                        ]
                    ),
                )
                logger.info(
                    f"User {telegram_id} not found or incomplete, prompted to start private chat with deep link"
                )
                return

            # Регистрируем пользователя как кандидата
            is_new = await GroupUserRepository.register_candidate(
                session, telegram_id, chat_id, name, username
            )
            if is_new:
                await bot.send_message(
                    chat_id=chat_id,
                    text=USER_REGISTERED_MESSAGE,
                )
            else:
                await bot.send_message(
                    chat_id=chat_id,
                    text=USER_ALREADY_CANDIDATE_MESSAGE,
                )
            logger.info(
                f"User {telegram_id} processed as hero candidate in group {chat_id}"
            )
    except Exception as e:
        logger.error(f"Error in become_hero handler: {e}", exc_info=True)
        await bot.send_message(
            chat_id=chat_id,
            text="❌ Ошибка при регистрации. Попробуйте позже.",
        )
