# bot/handlers/start.py
import logging
from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.core.database import get_async_session
from bot.repositories.user_repo import UserRepository
from bot.core.schemas import UserCreate
from datetime import datetime
import pendulum

logger = logging.getLogger(__name__)
router = Router()


class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_birth_date = State()


@router.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    try:
        async for session in get_async_session():
            # Проверяем, существует ли пользователь
            user_exists = await UserRepository.user_exists(
                session, message.from_user.id
            )

            if user_exists:
                await message.answer(
                    f"👋 Привет, {message.from_user.first_name}!\n"
                    "Ты уже зарегистрирован. Выбери пиво! 🍺\n\n"
                    "/beer - выбрать пиво\n"
                    "/profile - мой профиль\n"
                    "/stats - статистика"
                )
            else:
                await message.answer(
                    f"👋 Привет, {message.from_user.first_name}!\n"
                    "Давай знакомиться! Как тебя зовут?"
                )
                await state.set_state(RegistrationStates.waiting_for_name)
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await message.answer("Произошла ошибка. Попробуй позже.")


@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    """Обработка имени пользователя"""
    name = message.text.strip()

    if len(name) < 1 or len(name) > 50:
        await message.answer("Имя должно быть от 1 до 50 символов. Попробуй еще раз:")
        return

    await state.update_data(name=name)
    await message.answer(
        f"Приятно познакомиться, {name}! 😊\n"
        "Теперь укажи свою дату рождения в формате ДД.ММ.ГГГГ\n"
        "Например: 15.03.1990"
    )
    await state.set_state(RegistrationStates.waiting_for_birth_date)


@router.message(RegistrationStates.waiting_for_birth_date)
async def process_birth_date(message: types.Message, state: FSMContext):
    """Обработка даты рождения"""
    try:
        # Парсим дату
        date_str = message.text.strip()
        birth_date = pendulum.from_format(date_str, "DD.MM.YYYY").date()

        # Проверяем возраст (должен быть старше 18)
        today = pendulum.now().date()
        age = (
            today.year
            - birth_date.year
            - ((today.month, today.day) < (birth_date.month, birth_date.day))
        )

        if age < 18:
            await message.answer("Извини, но тебе должно быть не менее 18 лет 🔞")
            return

        if birth_date > today:
            await message.answer("Дата рождения не может быть в будущем 📅")
            return

        # Получаем данные из состояния
        user_data = await state.get_data()

        # Создаем пользователя
        async for session in get_async_session():
            user_create = UserCreate(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                name=user_data["name"],
                birth_date=birth_date,
            )

            user = await UserRepository.create_user(session, user_create)
            logger.info(f"New user registered: {user.telegram_id}")

            await message.answer(
                f"🎉 Отлично! Ты успешно зарегистрирован!\n\n"
                f"👤 Имя: {user.name}\n"
                f"🎂 Дата рождения: {birth_date.strftime('%d.%m.%Y')}\n"
                f"📅 Возраст: {age} лет\n\n"
                "Теперь можешь выбирать пиво! 🍺\n\n"
                "/beer - выбрать пиво\n"
                "/profile - мой профиль\n"
                "/stats - статистика"
            )

        await state.clear()

    except ValueError:
        await message.answer(
            "Неверный формат даты! 📅\n"
            "Используй формат ДД.ММ.ГГГГ\n"
            "Например: 15.03.1990"
        )
    except Exception as e:
        logger.error(f"Error processing birth date: {e}")
        await message.answer("Произошла ошибка при регистрации. Попробуй позже.")
