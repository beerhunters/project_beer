from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from bot.core.database import get_async_session
from bot.repositories.user_repo import UserRepository
from bot.repositories.event_repo import EventRepository
from bot.repositories.beer_repo import BeerRepository
from bot.core.schemas import BeerChoiceCreate
from bot.utils.decorators import private_chat_only
from bot.utils.logger import setup_logger
import pendulum
from datetime import datetime, time, timedelta
from math import radians, sin, cos, sqrt, atan2

logger = setup_logger(__name__)
router = Router()


class BeerSelectionStates(StatesGroup):
    waiting_for_location = State()


def get_command_keyboard(event_id: int = 0):
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text="👤 Профиль", callback_data="cmd_profile")
    )
    builder.add(
        types.InlineKeyboardButton(text="🏠 В начало", callback_data="cmd_start")
    )
    builder.adjust(2)
    return builder.as_markup()


def get_location_keyboard(event_id: int):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Отправить геопозицию", request_location=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    cancel_builder = InlineKeyboardBuilder()
    cancel_builder.add(
        types.InlineKeyboardButton(
            text="❌ Отменить", callback_data="cancel_beer_selection"
        )
    )
    return keyboard, cancel_builder.as_markup()


def get_beer_choice_keyboard(event):
    builder = InlineKeyboardBuilder()
    valid_options = []
    if event.has_beer_choice and event.beer_option_1 and event.beer_option_2:
        valid_options = [event.beer_option_1, event.beer_option_2]
        builder.add(
            types.InlineKeyboardButton(
                text=f"🍺 {event.beer_option_1}",
                callback_data=f"beer_{event.id}_{event.beer_option_1}",
            )
        )
        builder.add(
            types.InlineKeyboardButton(
                text=f"🍺 {event.beer_option_2}",
                callback_data=f"beer_{event.id}_{event.beer_option_2}",
            )
        )
    else:
        valid_options = [event.beer_option_1 or "Лагер"]
        builder.add(
            types.InlineKeyboardButton(
                text=f"🍺 {valid_options[0]}",
                callback_data=f"beer_{event.id}_{valid_options[0]}",
            )
        )
    builder.add(
        types.InlineKeyboardButton(
            text="❌ Отменить", callback_data="cancel_beer_selection"
        )
    )
    builder.adjust(1 if not event.has_beer_choice else 2)
    return builder.as_markup(), valid_options


def get_event_selection_keyboard(events):
    builder = InlineKeyboardBuilder()
    for event in events:
        time_str = event.event_time.strftime("%H:%M")
        button_text = f"📅 {event.name} @ {time_str}"
        builder.add(
            types.InlineKeyboardButton(
                text=button_text, callback_data=f"select_event_{event.id}"
            )
        )
    builder.add(
        types.InlineKeyboardButton(
            text="❌ Отменить", callback_data="cancel_beer_selection"
        )
    )
    builder.adjust(1)
    return builder.as_markup()


EARTH_RADIUS_M = 6371000


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    if not all(isinstance(x, (int, float)) and -90 <= x <= 90 for x in (lat1, lat2)):
        raise ValueError("Latitudes must be between -90 and 90 degrees")
    if not all(isinstance(x, (int, float)) and -180 <= x <= 180 for x in (lon1, lon2)):
        raise ValueError("Longitudes must be between -180 and 180 degrees")
    if not all(
        isinstance(x, (int, float)) and x == x for x in (lat1, lon1, lat2, lon2)
    ):
        raise ValueError("Coordinates must be finite numbers")
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = EARTH_RADIUS_M * c
    return distance


def is_event_selection_available(event, today, current_time):
    """Проверяет, доступен ли выбор пива для события (30 минут до начала или раньше)"""
    if event.event_date != today:
        return False
    current_dt = datetime.combine(today, current_time)
    event_start = datetime.combine(today, event.event_time)
    window_start = event_start - timedelta(minutes=30)
    return window_start <= current_dt <= event_start


async def get_all_upcoming_events(session, today):
    """Получает все предстоящие события на сегодня"""
    events = await EventRepository.get_upcoming_events_by_date(
        session, today, limit=100
    )
    # Фильтруем только сегодняшние события
    return [event for event in events if event.event_date == today]


@router.message(Command("beer"))
@private_chat_only(response_probability=0.5)
async def beer_selection_handler(message: types.Message, bot: Bot, state: FSMContext):
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
            upcoming_events = await get_all_upcoming_events(session, today)

            if not upcoming_events:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text="❌ Нет доступных событий на сегодня!",
                    reply_markup=get_command_keyboard(),
                )
                return

            # Показываем все события для выбора
            keyboard = get_event_selection_keyboard(upcoming_events)
            await bot.send_message(
                chat_id=message.chat.id,
                text="📅 Выбери событие для выбора пива:",
                reply_markup=keyboard,
            )

    except Exception as e:
        logger.error(f"Error in beer selection handler: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка. Попробуй позже.",
            reply_markup=get_command_keyboard(),
        )


@router.callback_query(lambda c: c.data.startswith("select_event_"))
@private_chat_only(response_probability=0.5)
async def select_event_callback(
    callback_query: types.CallbackQuery, bot: Bot, state: FSMContext
):
    try:
        await callback_query.answer()
        event_id = int(callback_query.data.split("_")[2])

        async for session in get_async_session():
            user = await UserRepository.get_user_by_telegram_id(
                session, callback_query.from_user.id
            )
            if not user:
                await bot.edit_message_text(
                    text="❌ Ты не зарегистрирован!\nИспользуй команду /start для регистрации.",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    reply_markup=get_command_keyboard(),
                )
                return

            event = await EventRepository.get_event_by_id(session, event_id)
            if not event:
                await bot.edit_message_text(
                    text="❌ Событие не найдено или завершилось.",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    reply_markup=get_command_keyboard(),
                )
                return

            today = pendulum.now("Europe/Moscow").date()
            current_time = pendulum.now("Europe/Moscow").time()

            # Проверяем, доступен ли выбор пива для этого события
            if not is_event_selection_available(event, today, current_time):
                event_start = datetime.combine(today, event.event_time)
                window_start = event_start - timedelta(minutes=30)
                current_dt = datetime.combine(today, current_time)

                if current_dt < window_start:
                    # Событие еще не началось (больше 30 минут до начала)
                    time_until_selection = window_start - current_dt
                    total_seconds = int(time_until_selection.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60

                    time_str = ""
                    if hours > 0:
                        time_str += f"{hours} ч. "
                    if minutes > 0:
                        time_str += f"{minutes} мин."
                    elif hours == 0 and minutes == 0:
                        time_str += f"{seconds} сек."

                    await bot.edit_message_text(
                        text=f"⏰ Выбор пива для события '{event.name}' будет доступен через {time_str}\n\nВозможность выбора предоставится за 30 минут до начала события.",
                        chat_id=callback_query.message.chat.id,
                        message_id=callback_query.message.message_id,
                        reply_markup=get_command_keyboard(event.id),
                    )
                else:
                    # Время для выбора истекло
                    await bot.edit_message_text(
                        text="❌ Время для выбора пива для этого события истекло.",
                        chat_id=callback_query.message.chat.id,
                        message_id=callback_query.message.message_id,
                        reply_markup=get_command_keyboard(event.id),
                    )
                return

            # Проверяем, не выбирал ли уже пользователь пиво для этого события
            has_chosen = await BeerRepository.has_user_chosen_for_event(
                session, user.id, event
            )
            if has_chosen:
                await bot.edit_message_text(
                    text="❌ Ты уже выбрал пиво для этого события!",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    reply_markup=get_command_keyboard(event.id),
                )
                return

            await state.update_data(event_id=event.id)

            # Если требуется геопозиция
            if event.latitude is not None and event.longitude is not None:
                reply_keyboard, cancel_keyboard = get_location_keyboard(event.id)
                await bot.send_message(
                    chat_id=callback_query.message.chat.id,
                    text="📍 Пожалуйста, отправь свою геопозицию, чтобы подтвердить, что ты рядом с местом события.",
                    reply_markup=reply_keyboard,
                )
                await state.set_state(BeerSelectionStates.waiting_for_location)
            else:
                # Сразу предлагаем выбор пива
                keyboard, _ = get_beer_choice_keyboard(event)
                await bot.edit_message_text(
                    text=f"🍺 Привет, {user.name}!\nВыбери пиво для события '{event.name}':",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    reply_markup=keyboard,
                )

    except Exception as e:
        logger.error(f"Error in select event callback: {e}", exc_info=True)
        await bot.edit_message_text(
            text="Произошла ошибка. Попробуй позже.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            reply_markup=get_command_keyboard(),
        )


@router.message(BeerSelectionStates.waiting_for_location)
@private_chat_only(response_probability=0.5)
async def process_user_location(message: types.Message, bot: Bot, state: FSMContext):
    try:
        if not message.location:
            reply_keyboard, cancel_keyboard = get_location_keyboard(0)
            await bot.send_message(
                chat_id=message.chat.id,
                text="❌ Пожалуйста, отправь геопозицию через кнопку.",
                reply_markup=reply_keyboard,
            )
            return

        user_lat = message.location.latitude
        user_lon = message.location.longitude
        data = await state.get_data()
        event_id = data.get("event_id")

        async for session in get_async_session():
            event = await EventRepository.get_event_by_id(session, event_id)
            if not event or event.latitude is None or event.longitude is None:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text="❌ Событие не найдено или координаты отсутствуют.",
                    reply_markup=get_command_keyboard(event_id or 0),
                )
                await state.clear()
                return

            distance = haversine_distance(
                user_lat, user_lon, event.latitude, event.longitude
            )

            if distance > 500:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text=f"❌ Ты слишком далеко от места события ({int(distance)} м). Нужно быть в радиусе 500 м.",
                    reply_markup=get_command_keyboard(event_id),
                )
                await state.clear()
                return

            user = await UserRepository.get_user_by_telegram_id(
                session, message.from_user.id
            )

            has_chosen = await BeerRepository.has_user_chosen_for_event(
                session, user.id, event
            )
            if has_chosen:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text="❌ Ты уже выбрал пиво для этого события!",
                    reply_markup=get_command_keyboard(event_id),
                )
                await state.clear()
                return

            keyboard, _ = get_beer_choice_keyboard(event)
            await bot.send_message(
                chat_id=message.chat.id,
                text=f"✅ Ты на месте! Выбери пиво для события '{event.name}':",
                reply_markup=keyboard,
            )
            await state.clear()

    except Exception as e:
        logger.error(f"Error processing user location: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка. Попробуй позже.",
            reply_markup=get_command_keyboard(),
        )
        await state.clear()


@router.callback_query(lambda c: c.data.startswith("beer_"))
@private_chat_only(response_probability=0.5)
async def beer_choice_callback(
    callback_query: types.CallbackQuery, bot: Bot, state: FSMContext
):
    try:
        await callback_query.answer()
        parts = callback_query.data.split("_")
        if len(parts) != 3:
            await bot.edit_message_text(
                text="❌ Неверный формат выбора пива.",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                reply_markup=get_command_keyboard(),
            )
            return

        event_id = int(parts[1])
        beer_choice = parts[2]

        async for session in get_async_session():
            user = await UserRepository.get_user_by_telegram_id(
                session, callback_query.from_user.id
            )
            if not user:
                await bot.edit_message_text(
                    text="❌ Пользователь не найден!\nИспользуй команду /start для регистрации.",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    reply_markup=get_command_keyboard(),
                )
                return

            event = await EventRepository.get_event_by_id(session, event_id)
            if not event:
                await bot.edit_message_text(
                    text="❌ Событие завершилось или недоступно.",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    reply_markup=get_command_keyboard(),
                )
                return

            today = pendulum.now("Europe/Moscow").date()
            current_time = pendulum.now("Europe/Moscow").time()

            # Повторная проверка времени выбора
            if not is_event_selection_available(event, today, current_time):
                await bot.edit_message_text(
                    text="❌ Время для выбора пива истекло или еще не началось.",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    reply_markup=get_command_keyboard(event_id),
                )
                return

            keyboard, valid_options = get_beer_choice_keyboard(event)
            if beer_choice not in valid_options:
                await bot.edit_message_text(
                    text="❌ Недопустимый выбор пива. Пожалуйста, выбери из предложенных вариантов.",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    reply_markup=keyboard,
                )
                return

            has_chosen = await BeerRepository.has_user_chosen_for_event(
                session, user.id, event
            )
            if has_chosen:
                await bot.edit_message_text(
                    text="❌ Ты уже выбрал пиво для этого события!",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    reply_markup=get_command_keyboard(event_id),
                )
                return

            choice_data = BeerChoiceCreate(
                user_id=user.id, event_id=event.id, beer_choice=beer_choice
            )
            choice = await BeerRepository.create_choice(session, choice_data)
            user_stats = await BeerRepository.get_user_beer_stats(session, user.id)

            message_text = f"✅ Отличный выбор! Ты выбрал 🍺 {beer_choice}\n\n"
            if user_stats:
                stats_lines = ["📊 Твоя статистика:"]
                for beer_type, count in user_stats.items():
                    stats_lines.append(f"🍺 {beer_type}: {count}")
                message_text += "\n".join(stats_lines) + "\n"
            else:
                message_text += "📊 У тебя пока нет статистики по выбору пива.\n"

            message_text += "\nВыбери действие:"

            logger.info(
                f"Beer choice saved for user {user.telegram_id}: {choice.beer_choice}, event {event.id}, stats: {user_stats}"
            )

            await bot.edit_message_text(
                message_id=callback_query.message.message_id,
                text=message_text,
                chat_id=callback_query.message.chat.id,
                reply_markup=get_command_keyboard(event_id),
            )

    except Exception as e:
        logger.error(f"Error in beer choice callback: {e}", exc_info=True)
        await bot.edit_message_text(
            text="Произошла ошибка. Попробуй позже.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            reply_markup=get_command_keyboard(),
        )


@router.callback_query(lambda c: c.data == "cancel_beer_selection")
@private_chat_only(response_probability=0.5)
async def cancel_beer_selection(
    callback_query: types.CallbackQuery, bot: Bot, state: FSMContext
):
    try:
        await callback_query.answer()
        await state.clear()
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="❌ Выбор пива отменен.",
            reply_markup=get_command_keyboard(),
        )
    except Exception as e:
        logger.error(f"Error canceling beer selection: {e}", exc_info=True)
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="Произошла ошибка. Попробуй позже.",
            reply_markup=get_command_keyboard(),
        )


@router.callback_query(lambda c: c.data == "cmd_beer")
@private_chat_only(response_probability=0.5)
async def cmd_beer_callback(
    callback_query: types.CallbackQuery, bot: Bot, state: FSMContext
):
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
            upcoming_events = await get_all_upcoming_events(session, today)

            if not upcoming_events:
                await bot.edit_message_text(
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    text="❌ Нет доступных событий на сегодня!",
                    reply_markup=get_command_keyboard(),
                )
                return

            # Показываем все события для выбора
            keyboard = get_event_selection_keyboard(upcoming_events)
            await bot.edit_message_text(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                text="📅 Выбери событие для выбора пива:",
                reply_markup=keyboard,
            )

    except Exception as e:
        logger.error(f"Error in cmd_beer callback: {e}", exc_info=True)
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="Произошла ошибка. Попробуй позже.",
            reply_markup=get_command_keyboard(),
        )
