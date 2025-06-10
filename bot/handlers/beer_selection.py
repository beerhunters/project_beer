from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from bot.core.database import get_async_session
from bot.repositories.user_repo import UserRepository
from bot.repositories.event_repo import EventRepository
from bot.repositories.beer_repo import BeerRepository
from bot.core.schemas import BeerChoiceCreate
from bot.utils.logger import setup_logger
import pendulum
from datetime import datetime, time
from math import radians, sin, cos, sqrt, atan2

logger = setup_logger(__name__)
router = Router()


class BeerSelectionStates(StatesGroup):
    waiting_for_location = State()


def get_command_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text="👤 Профиль", callback_data="cmd_profile")
    )
    builder.add(
        types.InlineKeyboardButton(text="🏠 В начало", callback_data="cmd_start")
    )
    builder.adjust(2)
    return builder.as_markup()


def get_location_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Отправить геопозицию", request_location=True)],
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
    if event.has_beer_choice and event.beer_option_1 and event.beer_option_2:
        builder.add(
            types.InlineKeyboardButton(
                text=f"🍺 {event.beer_option_1}",
                callback_data=f"beer_{event.beer_option_1}",
            )
        )
        builder.add(
            types.InlineKeyboardButton(
                text=f"🍺 {event.beer_option_2}",
                callback_data=f"beer_{event.beer_option_2}",
            )
        )
    else:
        builder.add(
            types.InlineKeyboardButton(
                text=f"🍺 {event.beer_option_1}",
                callback_data=f"beer_{event.beer_option_1}",
            )
        )
    builder.add(
        types.InlineKeyboardButton(
            text="❌ Отменить", callback_data="cancel_beer_selection"
        )
    )
    builder.adjust(1 if not event.has_beer_choice else 2)
    return builder.as_markup()


EARTH_RADIUS_M = 6371000  # Earth's mean radius in meters


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth using the Haversine formula.

    Args:
        lat1 (float): Latitude of the first point in degrees.
        lon1 (float): Longitude of the first point in degrees.
        lat2 (float): Latitude of the second point in degrees.
        lon2 (float): Longitude of the second point in degrees.

    Returns:
        float: Distance between the points in meters.

    Raises:
        ValueError: If coordinates are invalid (not finite or out of range).
    """
    # Validate inputs
    if not all(isinstance(x, (int, float)) and -90 <= x <= 90 for x in (lat1, lat2)):
        raise ValueError("Latitudes must be between -90 and 90 degrees")
    if not all(isinstance(x, (int, float)) and -180 <= x <= 180 for x in (lon1, lon2)):
        raise ValueError("Longitudes must be between -180 and 180 degrees")
    if not all(
        isinstance(x, (int, float)) and x == x for x in (lat1, lon1, lat2, lon2)
    ):  # Check for NaN
        raise ValueError("Coordinates must be finite numbers")

    # Convert to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = EARTH_RADIUS_M * c

    return distance


@router.message(Command("beer"))
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
            current_time = pendulum.now("Europe/Moscow").time()
            events = await EventRepository.get_upcoming_events(session, limit=100)
            event = None
            for e in events:
                if e.event_date == today:
                    event_time = datetime.combine(today, e.event_time).time()
                    time_diff = (
                        datetime.combine(today, event_time)
                        - datetime.combine(today, current_time)
                    ).total_seconds() / 60
                    if 0 <= time_diff <= 30:
                        event = e
                        break
            if not event:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text="❌ Нет подходящих событий! Выбор пива доступен за 30 минут до начала события.",
                    reply_markup=get_command_keyboard(),
                )
                return
            await state.update_data(event_id=event.id)
            if event.latitude is not None and event.longitude is not None:
                reply_keyboard, cancel_keyboard = get_location_keyboard()
                await bot.send_message(
                    chat_id=message.chat.id,
                    text="📍 Пожалуйста, отправь свою геопозицию, чтобы подтвердить, что ты рядом с местом события.",
                    reply_markup=reply_keyboard,
                )
                await state.set_state(BeerSelectionStates.waiting_for_location)
            else:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text=f"🍺 Привет, {user.name}!\nВыбери пиво для события '{event.name}':",
                    reply_markup=get_beer_choice_keyboard(event),
                )
    except Exception as e:
        logger.error(f"Error in beer selection handler: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка. Попробуй позже.",
            reply_markup=get_command_keyboard(),
        )


@router.message(BeerSelectionStates.waiting_for_location)
async def process_user_location(message: types.Message, bot: Bot, state: FSMContext):
    try:
        if not message.location:
            reply_keyboard, cancel_keyboard = get_location_keyboard()
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
                    reply_markup=get_command_keyboard(),
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
                    reply_markup=get_command_keyboard(),
                )
                await state.clear()
                return
            user = await UserRepository.get_user_by_telegram_id(
                session, message.from_user.id
            )
            await bot.send_message(
                chat_id=message.chat.id,
                text=f"✅ Ты на месте! Выбери пиво для события '{event.name}':",
                reply_markup=get_beer_choice_keyboard(event),
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
async def beer_choice_callback(
    callback_query: types.CallbackQuery, bot: Bot, state: FSMContext
):
    try:
        await callback_query.answer()
        beer_choice = callback_query.data.replace("beer_", "")
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
            choice_data = BeerChoiceCreate(user_id=user.id, beer_choice=beer_choice)
            choice = await BeerRepository.create_choice(session, choice_data)
            await session.commit()
            user_stats = await BeerRepository.get_user_beer_stats(session, user.id)
            latest_choice = await BeerRepository.get_latest_user_choice(
                session, user.id
            )
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
                f"Beer choice saved for user {user.telegram_id}: {choice.beer_choice}, stats: {user_stats}"
            )
            await bot.edit_message_text(
                message_id=callback_query.message.message_id,
                text=message_text,
                chat_id=callback_query.message.chat.id,
                reply_markup=get_command_keyboard(),
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
        # Send a separate message to remove the reply keyboard
        await bot.send_message(
            chat_id=callback_query.message.chat.id,
            text=".",
            reply_markup=ReplyKeyboardRemove(),
            disable_notification=True,
        )
        await bot.delete_message(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id + 1,
        )
    except Exception as e:
        logger.error(f"Error canceling beer selection: {e}", exc_info=True)
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="Произошла ошибка. Попробуй позже.",
            reply_markup=get_command_keyboard(),
        )
        await bot.send_message(
            chat_id=callback_query.message.chat.id,
            text=".",
            reply_markup=ReplyKeyboardRemove(),
            disable_notification=True,
        )
        await bot.delete_message(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id + 1,
        )


@router.callback_query(lambda c: c.data == "cmd_beer")
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
            current_time = pendulum.now("Europe/Moscow").time()
            events = await EventRepository.get_upcoming_events(session, limit=100)
            event = None
            for e in events:
                if e.event_date == today:
                    event_time = datetime.combine(today, e.event_time).time()
                    time_diff = (
                        datetime.combine(today, event_time)
                        - datetime.combine(today, current_time)
                    ).total_seconds() / 60
                    if 0 <= time_diff <= 30:
                        event = e
                        break
            if not event:
                await bot.edit_message_text(
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    text="❌ Нет подходящих событий! Выбор пива доступен за 30 минут до начала события.",
                    reply_markup=get_command_keyboard(),
                )
                return
            await state.update_data(event_id=event.id)
            if event.latitude is not None and event.longitude is not None:
                reply_keyboard, cancel_keyboard = get_location_keyboard()
                # Use send_message instead of edit_message_text to attach reply keyboard
                await bot.send_message(
                    chat_id=callback_query.message.chat.id,
                    text="📍 Пожалуйста, отправь свою геопозицию, чтобы подтвердить, что ты рядом с местом события.",
                    reply_markup=reply_keyboard,
                )
                await state.set_state(BeerSelectionStates.waiting_for_location)
            else:
                await bot.edit_message_text(
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    text=f"🍺 Привет, {user.name}!\nВыбери пиво для события '{event.name}':",
                    reply_markup=get_beer_choice_keyboard(event),
                )
    except Exception as e:
        logger.error(f"Error in cmd_beer callback: {e}", exc_info=True)
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="Произошла ошибка. Попробуй позже.",
            reply_markup=get_command_keyboard(),
        )
