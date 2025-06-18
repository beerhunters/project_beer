from aiogram import Router, types, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.core.database import get_async_session
from bot.repositories.beer_repo import BeerRepository
from bot.repositories.user_repo import UserRepository
from bot.repositories.group_user_repo import GroupUserRepository
from bot.core.schemas import UserCreate
from bot.utils.decorators import private_chat_only
from bot.utils.logger import setup_logger
import pendulum
import re

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
@private_chat_only(response_probability=0.5)
async def start_handler(message: types.Message, bot: Bot, state: FSMContext):
    try:
        telegram_id = message.from_user.id
        username = message.from_user.username
        name = message.from_user.first_name or f"User {telegram_id}"

        # Проверяем наличие deep link
        deep_link_match = re.match(r"/start (group_-\d+)", message.text)
        chat_id = None
        if deep_link_match:
            deep_link_param = deep_link_match.group(1)  # e.g., group_-1002350206500
            chat_id = int(deep_link_param.replace("group_", ""))
            await state.update_data(group_chat_id=chat_id)

        async for session in get_async_session():
            user = await UserRepository.get_user_by_telegram_id(session, telegram_id)
            if (
                user and user.name and user.birth_date
            ):  # Пользователь полностью зарегистрирован
                if chat_id:
                    # Проверяем группу
                    group = await GroupUserRepository.get_group_by_chat_id(
                        session, chat_id
                    )
                    if not group:
                        await bot.send_message(
                            chat_id=telegram_id,
                            text="❌ Группа не найдена. Попросите администратора зарегистрировать группу с помощью /hero.",
                            reply_markup=get_command_keyboard(),
                        )
                        return

                    # Регистрируем как кандидата
                    is_new_candidate = await GroupUserRepository.register_candidate(
                        session, telegram_id, chat_id, user.name, username
                    )
                    if is_new_candidate:
                        await bot.send_message(
                            chat_id=telegram_id,
                            text="✅ Ты добавлен как кандидат на Героя Дня в группе!",
                            reply_markup=get_command_keyboard(),
                        )
                        logger.info(
                            f"User {telegram_id} added as candidate in group {chat_id} via deep link"
                        )
                    else:
                        await bot.send_message(
                            chat_id=telegram_id,
                            text="ℹ️ Ты уже зарегистрирован как кандидат на Героя Дня в группе!",
                            reply_markup=get_command_keyboard(),
                        )
                        logger.info(
                            f"User {telegram_id} already a candidate in group {chat_id}"
                        )
                else:
                    await bot.send_message(
                        chat_id=message.chat.id,
                        text=f"👋 Привет, {user.name}!\nВыбери действие:",
                        reply_markup=get_command_keyboard(),
                    )
            else:
                # Пользователь не зарегистрирован или регистрация не завершена
                if not user:
                    await bot.send_message(
                        chat_id=message.chat.id,
                        text=f"👋 Привет, {name}!\nДавай знакомиться! Как тебя зовут?",
                    )
                    await state.set_state(RegistrationStates.waiting_for_name)
                else:
                    await bot.send_message(
                        chat_id=message.chat.id,
                        text=f"👋 Привет, {name}!\nТы не завершил регистрацию. Укажи свою дату рождения в формате ДД.ММ.ГГГГ (например: 15.03.1990):",
                    )
                    await state.set_state(RegistrationStates.waiting_for_birth_date)
    except Exception as e:
        logger.error(f"Error in start handler: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка. Попробуй позже.",
        )


@router.callback_query(lambda c: c.data == "cmd_start")
@private_chat_only(response_probability=0.5)
async def cmd_start_callback(
    callback_query: types.CallbackQuery, bot: Bot, state: FSMContext
):
    try:
        await callback_query.answer()
        await state.clear()
        async for session in get_async_session():
            user = await UserRepository.get_user_by_telegram_id(
                session, callback_query.from_user.id
            )
            if user and user.name and user.birth_date:
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
        )


@router.message(RegistrationStates.waiting_for_name)
@private_chat_only(response_probability=0.5)
async def process_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if not (1 <= len(name) <= 50):
        await message.bot.send_message(
            chat_id=message.chat.id,
            text="Имя должно быть от 1 до 50 символов. Попробуй еще раз:",
        )
        return
    await state.update_data(name=name)
    await message.bot.send_message(
        chat_id=message.chat.id,
        text=f"Приятно познакомиться, {name}! 😊\n"
        "Теперь укажи свою дату рождения в формате ДД.ММ.ГГГГ\n"
        "Например: 15.03.1990",
    )
    await state.set_state(RegistrationStates.waiting_for_birth_date)


@router.message(RegistrationStates.waiting_for_birth_date)
@private_chat_only(response_probability=0.5)
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
            )
            return
        if birth_date > today:
            await message.bot.send_message(
                chat_id=message.chat.id,
                text="Дата рождения не может быть в будущем 📅",
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

            # Проверяем, есть ли group_chat_id в состоянии
            chat_id = user_data.get("group_chat_id")
            if chat_id:
                group = await GroupUserRepository.get_group_by_chat_id(session, chat_id)
                if group:
                    is_new_candidate = await GroupUserRepository.register_candidate(
                        session, message.from_user.id, chat_id, user.name, user.username
                    )
                    if is_new_candidate:
                        await message.bot.send_message(
                            chat_id=message.chat.id,
                            text=f"🎉 Отлично! Ты успешно зарегистрирован и добавлен как кандидат на Героя Дня в группе!\n\n"
                            f"👤 Имя: {user.name}\n"
                            f"🎂 Дата рождения: {birth_date.strftime('%d.%m.%Y')}\n"
                            f"📅 Возраст: {age} лет\n\n"
                            "Теперь можешь выбирать пиво! 🍺\n\nВыбери действие:",
                            reply_markup=get_command_keyboard(),
                        )
                        logger.info(
                            f"User {message.from_user.id} added as candidate in group {chat_id} after registration"
                        )
                    else:
                        await message.bot.send_message(
                            chat_id=message.chat.id,
                            text=f"🎉 Отлично! Ты успешно зарегистрирован и уже являешься кандидатом на Героя Дня в группе!\n\n"
                            f"👤 Имя: {user.name}\n"
                            f"🎂 Дата рождения: {birth_date.strftime('%d.%m.%Y')}\n"
                            f"📅 Возраст: {age} лет\n\n"
                            "Теперь можешь выбирать пиво! 🍺\n\nВыбери действие:",
                            reply_markup=get_command_keyboard(),
                        )
                        logger.info(
                            f"User {message.from_user.id} already a candidate in group {chat_id}"
                        )
                else:
                    await message.bot.send_message(
                        chat_id=message.chat.id,
                        text=f"🎉 Отлично! Ты успешно зарегистрирован!\n\n"
                        f"👤 Имя: {user.name}\n"
                        f"🎂 Дата рождения: {birth_date.strftime('%d.%m.%Y')}\n"
                        f"📅 Возраст: {age} лет\n\n"
                        "Группа не найдена, но ты можешь вернуться в группу и выполнить /become_hero.",
                        reply_markup=get_command_keyboard(),
                    )
            else:
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
        )
    except Exception as e:
        logger.error(f"Error processing birth date: {e}")
        await message.bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка при регистрации. Попробуй позже.",
        )
