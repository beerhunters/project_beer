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
    builder.adjust(2)
    return builder.as_markup()


@router.message(CommandStart())
async def start_handler(message: types.Message, bot: Bot, state: FSMContext):
    try:
        async for session in get_async_session():
            user = await UserRepository.get_user_by_telegram_id(
                session, message.from_user.id
            )
            if user:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text=f"👋 Привет, {user.name}!\nВыбери действие:",
                    reply_markup=get_command_keyboard(),
                )
            else:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text=f"👋 Привет, {message.from_user.first_name}!\n"
                    "Давай знакомиться! Как тебя зовут?",
                )
                await state.set_state(RegistrationStates.waiting_for_name)
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка. Попробуй позже.",
            # reply_markup=get_command_keyboard(),
        )


@router.callback_query(lambda c: c.data == "cmd_start")
async def cmd_start_callback(
    callback_query: types.CallbackQuery, bot: Bot, state: FSMContext
):
    try:
        await callback_query.answer()
        await state.clear()  # Clear any FSM state to reset the user
        async for session in get_async_session():
            user = await UserRepository.get_user_by_telegram_id(
                session, callback_query.from_user.id
            )
            if user:
                await bot.edit_message_text(
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    text=f"👋 Привет, {user.name}!\nВыбери действие:",
                    reply_markup=get_command_keyboard(),
                )
            else:
                await bot.edit_message_text(
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    text=f"👋 Привет, {callback_query.from_user.first_name}!\n"
                    "Давай знакомиться! Как тебя зовут?",
                )
                await state.set_state(RegistrationStates.waiting_for_name)
    except Exception as e:
        logger.error(f"Error in start callback: {e}")
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="Произошла ошибка. Попробуй позже.",
            # reply_markup=get_command_keyboard(),
        )


@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if not (1 <= len(name) <= 50):
        await message.bot.send_message(
            chat_id=message.chat.id,
            text="Имя должно быть от 1 до 50 символов. Попробуй еще раз:",
            # reply_markup=get_command_keyboard(),
        )
        return
    await state.update_data(name=name)
    await message.bot.send_message(
        chat_id=message.chat.id,
        text=f"Приятно познакомиться, {name}! 😊\n"
        "Теперь укажи свою дату рождения в формате ДД.ММ.ГГГГ\n"
        "Например: 15.03.1990",
        # reply_markup=get_command_keyboard(),
    )
    await state.set_state(RegistrationStates.waiting_for_birth_date)


@router.message(RegistrationStates.waiting_for_birth_date)
async def process_birth_date(message: types.Message, state: FSMContext):
    try:
        date_str = message.text.strip()
        birth_date = pendulum.from_format(
            date_str, "DD.MM.YYYY", tz="Europe/Moscow"
        ).date()
        today = pendulum.now("Europe/Moscow").date()
        age = (
            today.year
            - birth_date.year
            - ((today.month, today.day) < (birth_date.month, birth_date.day))
        )
        if age < 18:
            await message.bot.send_message(
                chat_id=message.chat.id,
                text="Извини, но тебе должно быть не менее 18 лет 🔞",
                # reply_markup=get_command_keyboard(),
            )
            return
        if birth_date > today:
            await message.bot.send_message(
                chat_id=message.chat.id,
                text="Дата рождения не может быть в будущем 📅",
                # reply_markup=get_command_keyboard(),
            )
            return
        user_data = await state.get_data()
        async for session in get_async_session():
            user_create = UserCreate(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                name=user_data["name"],
                birth_date=birth_date,
            )
            user = await UserRepository.create_user(session, user_create)
            await message.bot.send_message(
                chat_id=message.chat.id,
                text=f"🎉 Отлично! Ты успешно зарегистрирован!\n\n"
                f"👤 Имя: {user.name}\n"
                f"🎂 Дата рождения: {birth_date.strftime('%d.%m.%Y')}\n"
                f"📅 Возраст: {age} лет\n\n"
                "Теперь можешь выбирать пиво! 🍺\n\nВыбери действие:",
                reply_markup=get_command_keyboard(),
            )
        await state.clear()
    except pendulum.exceptions.ParserError:
        await message.bot.send_message(
            chat_id=message.chat.id,
            text="Неверный формат даты! 📅\n"
            "Используй формат ДД.ММ.ГГГГ\n"
            "Например: 15.03.1990",
            # reply_markup=get_command_keyboard(),
        )
    except Exception as e:
        logger.error(f"Error processing birth date: {e}")
        await message.bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка при регистрации. Попробуй позже.",
            # reply_markup=get_command_keyboard(),
        )
