from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.core.database import get_async_session
from bot.repositories.user_repo import UserRepository
from bot.repositories.beer_repo import BeerRepository
from bot.core.models import BeerTypeEnum
from bot.utils.logger import setup_logger
import pendulum
import enum

logger = setup_logger(__name__)
router = Router()


def get_command_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text="🍺 Выбрать пиво", callback_data="cmd_beer")
    )
    builder.add(
        types.InlineKeyboardButton(text="📊 Статистика", callback_data="cmd_stats")
    )
    builder.add(
        types.InlineKeyboardButton(text="🏠 В начало", callback_data="cmd_start")
    )
    builder.adjust(2)
    return builder.as_markup()


@router.message(Command("profile"))
async def profile_handler(message: types.Message, bot: Bot):
    try:
        async for session in get_async_session():
            user = await UserRepository.get_user_by_telegram_id(
                session, message.from_user.id
            )
            if not user:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text="❌ Ты не зарегистрирован!\nИспользуй команду /start для регистрации.",
                    reply_markup=get_command_keyboard(),
                )
                return
            today = pendulum.now("Europe/Moscow").date()
            age = (
                today.year
                - user.birth_date.year
                - (
                    (today.month, today.day)
                    < (user.birth_date.month, user.birth_date.day)
                )
            )
            user_stats = await BeerRepository.get_user_beer_stats(session, user.id)
            latest_choice = await BeerRepository.get_latest_user_choice(
                session, user.id
            )
            beer_names = {
                BeerTypeEnum.LAGER.value: "🍺 Lager",
                BeerTypeEnum.HAND_OF_GOD.value: "🍻 Hand of God",
            }
            profile_text = f"👤 **Твой профиль**\n\n"
            profile_text += f"📛 Имя: {user.name}\n"
            profile_text += (
                f"🎂 Дата рождения: {user.birth_date.strftime('%d.%m.%Y')}\n"
            )
            profile_text += f"📅 Возраст: {age} лет\n"
            profile_text += f"🆔 Telegram ID: {user.telegram_id}\n"
            profile_text += (
                f"📪 Username: @{user.username if user.username else 'не указан'}\n"
            )
            profile_text += f"📅 Дата регистрации: {pendulum.instance(user.created_at).in_timezone('Europe/Moscow').strftime('%d.%m.%Y %H:%M')}\n\n"
            profile_text += "🍺 **Твои выборы пива**:\n"
            if user_stats:
                for beer_type_value, count in user_stats.items():
                    profile_text += f"{beer_names.get(beer_type_value, beer_type_value)}: {count} раз(а)\n"
            else:
                profile_text += "Ты еще не выбирал пиво!\n"
            if latest_choice:
                latest_beer_display_name = beer_names.get(
                    (
                        latest_choice.beer_type.value
                        if isinstance(latest_choice.beer_type, enum.Enum)
                        else latest_choice.beer_type
                    ),
                    str(latest_choice.beer_type),
                )
                profile_text += f"\n⏰ Последний выбор: {latest_beer_display_name} "
                profile_text += f"({pendulum.instance(latest_choice.selected_at).in_timezone('Europe/Moscow').strftime('%d.%m.%Y %H:%M')})\n"
            profile_text += "\nВыбери действие:"
            await bot.send_message(
                chat_id=message.chat.id,
                text=profile_text,
                parse_mode="Markdown",
                reply_markup=get_command_keyboard(),
            )
    except Exception as e:
        logger.error(f"Error in profile handler: {e}")
        await bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка. Попробуй позже.",
            reply_markup=get_command_keyboard(),
        )


@router.callback_query(lambda c: c.data == "cmd_profile")
async def cmd_profile_callback(callback_query: types.CallbackQuery, bot: Bot):
    try:
        await callback_query.answer()
        async for session in get_async_session():
            user = await UserRepository.get_user_by_telegram_id(
                session, callback_query.from_user.id
            )
            if not user:
                await bot.edit_message_text(
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    text="❌ Ты не зарегистрирован!\nИспользуй команду /start для регистрации.",
                    reply_markup=get_command_keyboard(),
                )
                return
            today = pendulum.now("Europe/Moscow").date()
            age = (
                today.year
                - user.birth_date.year
                - (
                    (today.month, today.day)
                    < (user.birth_date.month, user.birth_date.day)
                )
            )
            user_stats = await BeerRepository.get_user_beer_stats(session, user.id)
            latest_choice = await BeerRepository.get_latest_user_choice(
                session, user.id
            )
            beer_names = {
                BeerTypeEnum.LAGER.value: "🍺 Lager",
                BeerTypeEnum.HAND_OF_GOD.value: "🍻 Hand of God",
            }
            profile_text = f"👤 **Твой профиль**\n\n"
            profile_text += f"📛 Имя: {user.name}\n"
            profile_text += (
                f"🎂 Дата рождения: {user.birth_date.strftime('%d.%m.%Y')}\n"
            )
            profile_text += f"📅 Возраст: {age} лет\n"
            profile_text += f"🆔 Telegram ID: {user.telegram_id}\n"
            profile_text += (
                f"📪 Username: @{user.username if user.username else 'не указан'}\n"
            )
            profile_text += f"📅 Дата регистрации: {pendulum.instance(user.created_at).in_timezone('Europe/Moscow').strftime('%d.%m.%Y %H:%M')}\n\n"
            profile_text += "🍺 **Твои выборы пива**:\n"
            if user_stats:
                for beer_type_value, count in user_stats.items():
                    profile_text += f"{beer_names.get(beer_type_value, beer_type_value)}: {count} раз(а)\n"
            else:
                profile_text += "Ты еще не выбирал пиво!\n"
            if latest_choice:
                latest_beer_display_name = beer_names.get(
                    (
                        latest_choice.beer_type.value
                        if isinstance(latest_choice.beer_type, enum.Enum)
                        else latest_choice.beer_type
                    ),
                    str(latest_choice.beer_type),
                )
                profile_text += f"\n⏰ Последний выбор: {latest_beer_display_name} "
                profile_text += f"({pendulum.instance(latest_choice.selected_at).in_timezone('Europe/Moscow').strftime('%d.%m.%Y %H:%M')})\n"
            profile_text += "\nВыбери действие:"
            await bot.edit_message_text(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                text=profile_text,
                parse_mode="Markdown",
                reply_markup=get_command_keyboard(),
            )
    except Exception as e:
        logger.error(f"Error in profile callback: {e}")
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="Произошла ошибка. Попробуй позже.",
            reply_markup=get_command_keyboard(),
        )
