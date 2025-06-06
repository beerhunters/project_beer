from aiogram import Router, types, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.core.database import get_async_session
from bot.core.models import BeerTypeEnum
from bot.repositories.beer_repo import BeerRepository
from bot.repositories.user_repo import UserRepository
from bot.core.schemas import UserCreate
from bot.utils.logger import setup_logger
import pendulum

logger = setup_logger(__name__)
router = Router()


class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_birth_date = State()


def get_command_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text="🍺 Выбрать пиво", callback_data="cmd_beer")
    )
    builder.add(
        types.InlineKeyboardButton(text="👤 Профиль", callback_data="cmd_profile")
    )
    builder.add(
        types.InlineKeyboardButton(text="🏠 В начало", callback_data="cmd_start")
    )
    builder.adjust(2)
    return builder.as_markup()


@router.message(Command("stats"))
async def stats_handler(message: types.Message, bot: Bot):
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
            beer_stats = await BeerRepository.get_beer_stats(session)
            beer_names = {
                BeerTypeEnum.LAGER.value: "🍺 Lager",
                BeerTypeEnum.HAND_OF_GOD.value: "🍻 Hand of God",
            }
            text = "📊 Общая статистика выбора пива:\n\n"
            if beer_stats:
                for beer_type_value, count in beer_stats.items():
                    display_name = beer_names.get(beer_type_value, beer_type_value)
                    text += f"{display_name}: {count} раз(а)\n"
            else:
                text += "Пока никто ничего не выбрал."
            text += "\nВыбери действие:"
            await bot.send_message(
                chat_id=message.chat.id, text=text, reply_markup=get_command_keyboard()
            )
    except Exception as e:
        logger.error(f"Error in stats handler: {e}")
        await bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка при получении статистики.",
            reply_markup=get_command_keyboard(),
        )


@router.callback_query(lambda c: c.data == "cmd_stats")
async def cmd_stats_callback(callback_query: types.CallbackQuery, bot: Bot):
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
            beer_stats = await BeerRepository.get_beer_stats(session)
            beer_names = {
                BeerTypeEnum.LAGER.value: "🍺 Lager",
                BeerTypeEnum.HAND_OF_GOD.value: "🍻 Hand of God",
            }
            text = "📊 Общая статистика выбора пива:\n\n"
            if beer_stats:
                for beer_type_value, count in beer_stats.items():
                    display_name = beer_names.get(beer_type_value, beer_type_value)
                    text += f"{display_name}: {count} раз(а)\n"
            else:
                text += "Пока никто ничего не выбрал."
            text += "\nВыбери действие:"
            await bot.edit_message_text(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                text=text,
                reply_markup=get_command_keyboard(),
            )
    except Exception as e:
        logger.error(f"Error in cmd_stats callback: {e}")
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="Произошла ошибка при получении статистики.",
            reply_markup=get_command_keyboard(),
        )
