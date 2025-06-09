from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.core.database import get_async_session
from bot.repositories.user_repo import UserRepository
from bot.repositories.event_repo import EventRepository
from bot.core.schemas import EventCreate
from bot.utils.logger import setup_logger
import pendulum
import os
from datetime import time
from sqlalchemy.exc import ProgrammingError
import random

logger = setup_logger(__name__)
router = Router()
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "267863612"))


class EventCreationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_location = State()
    waiting_for_beer_choice = State()
    waiting_for_beer_options = State()


def get_cancel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(
            text="❌ Отменить", callback_data="cancel_event_creation"
        )
    )
    return builder.as_markup()


def get_beer_choice_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="✅ Да", callback_data="choice_yes"))
    builder.add(types.InlineKeyboardButton(text="❌ Нет", callback_data="choice_no"))
    builder.add(
        types.InlineKeyboardButton(
            text="🚫 Отменить", callback_data="cancel_event_creation"
        )
    )
    builder.adjust(2, 1)
    return builder.as_markup()


@router.message(Command("create_event"))
async def create_event_handler(message: types.Message, bot: Bot, state: FSMContext):
    try:
        if message.chat.type != "private":
            return
        if message.from_user.id != ADMIN_TELEGRAM_ID:
            await bot.send_message(
                chat_id=message.chat.id, text="❌ У вас нет прав для создания событий."
            )
            return
        await bot.send_message(
            chat_id=message.chat.id,
            text="🎉 Создание нового события!\n\n📝 Введите название события:",
            reply_markup=get_cancel_keyboard(),
        )
        await state.set_state(EventCreationStates.waiting_for_name)
    except Exception as e:
        logger.error(f"Error in create_event handler: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id, text="Произошла ошибка. Попробуйте позже."
        )


@router.message(EventCreationStates.waiting_for_name)
async def process_event_name(message: types.Message, bot: Bot, state: FSMContext):
    try:
        name = message.text.strip()
        if not (1 <= len(name) <= 200):
            await bot.send_message(
                chat_id=message.chat.id,
                text="❌ Название должно быть от 1 до 200 символов. Попробуйте еще раз:",
                reply_markup=get_cancel_keyboard(),
            )
            return
        await state.update_data(name=name)
        await bot.send_message(
            chat_id=message.chat.id,
            text=f"✅ Название: {name}\n\n📅 Введите дату события в формате ДД.ММ.ГГГГ\nНапример: 15.12.2024",
            reply_markup=get_cancel_keyboard(),
        )
        await state.set_state(EventCreationStates.waiting_for_date)
    except Exception as e:
        logger.error(f"Error processing event name: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка. Попробуйте позже.",
            reply_markup=get_cancel_keyboard(),
        )


@router.message(EventCreationStates.waiting_for_date)
async def process_event_date(message: types.Message, bot: Bot, state: FSMContext):
    try:
        date_str = message.text.strip()
        event_date = pendulum.from_format(
            date_str, "DD.MM.YYYY", tz="Europe/Moscow"
        ).date()
        today = pendulum.now("Europe/Moscow").date()
        if event_date < today:
            await bot.send_message(
                chat_id=message.chat.id,
                text="❌ Дата события не может быть в прошлом. Попробуйте еще раз:",
                reply_markup=get_cancel_keyboard(),
            )
            return
        await state.update_data(event_date=event_date)
        await bot.send_message(
            chat_id=message.chat.id,
            text=f"✅ Дата: {event_date.strftime('%d.%m.%Y')}\n\n🕐 Введите время события в формате ЧЧ:ММ\nНапример: 18:30",
            reply_markup=get_cancel_keyboard(),
        )
        await state.set_state(EventCreationStates.waiting_for_time)
    except pendulum.exceptions.ParserError:
        await bot.send_message(
            chat_id=message.chat.id,
            text="❌ Неверный формат даты! Используйте формат ДД.ММ.ГГГГ\nНапример: 15.12.2024",
            reply_markup=get_cancel_keyboard(),
        )
    except Exception as e:
        logger.error(f"Error processing event date: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка. Попробуйте позже.",
            reply_markup=get_cancel_keyboard(),
        )


@router.message(EventCreationStates.waiting_for_time)
async def process_event_time(message: types.Message, bot: Bot, state: FSMContext):
    try:
        time_str = message.text.strip()
        hour, minute = map(int, time_str.split(":"))
        event_time = time(hour=hour, minute=minute)
        await state.update_data(event_time=event_time)
        await bot.send_message(
            chat_id=message.chat.id,
            text=f"✅ Время: {event_time.strftime('%H:%M')}\n\n📍 Введите координаты места (широта, долгота) через запятую, например, 55.7558,37.6173\nИли введите \"-\" для пропуска координат, после чего можно указать название места:",
            reply_markup=get_cancel_keyboard(),
        )
        await state.set_state(EventCreationStates.waiting_for_location)
    except ValueError:
        await bot.send_message(
            chat_id=message.chat.id,
            text="❌ Неверный формат времени! Используйте формат ЧЧ:ММ\nНапример: 18:30",
            reply_markup=get_cancel_keyboard(),
        )
    except Exception as e:
        logger.error(f"Error processing event time: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка. Попробуйте позже.",
            reply_markup=get_cancel_keyboard(),
        )


@router.message(EventCreationStates.waiting_for_location)
async def process_event_location(message: types.Message, bot: Bot, state: FSMContext):
    try:
        input_str = message.text.strip()
        latitude = None
        longitude = None
        if input_str != "-":
            try:
                lat_str, lon_str = map(str.strip, input_str.split(","))
                latitude = float(lat_str)
                longitude = float(lon_str)
                if not (-90 <= latitude <= 90):
                    await bot.send_message(
                        chat_id=message.chat.id,
                        text="❌ Широта должна быть числом от -90 до 90. Попробуйте еще раз:",
                        reply_markup=get_cancel_keyboard(),
                    )
                    return
                if not (-180 <= longitude <= 180):
                    await bot.send_message(
                        chat_id=message.chat.id,
                        text="❌ Долгота должна быть числом от -180 до 180. Попробуйте еще раз:",
                        reply_markup=get_cancel_keyboard(),
                    )
                    return
            except ValueError:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text='❌ Координаты должны быть в формате "широта,долгота" (например, 55.7558,37.6173) или "-". Попробуйте еще раз:',
                    reply_markup=get_cancel_keyboard(),
                )
                return
        await state.update_data(latitude=latitude, longitude=longitude)
        await bot.send_message(
            chat_id=message.chat.id,
            text='📍 Введите название места (например, Бар Хмель) или "-" для пропуска:',
            reply_markup=get_cancel_keyboard(),
        )
        await state.set_state(EventCreationStates.waiting_for_beer_choice)
    except Exception as e:
        logger.error(f"Error processing event location: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка. Попробуйте позже.",
            reply_markup=get_cancel_keyboard(),
        )


@router.message(EventCreationStates.waiting_for_beer_choice)
async def process_event_location_name(
    message: types.Message, bot: Bot, state: FSMContext
):
    try:
        location_name = None
        if message.text and message.text.strip() != "-":
            location_name = message.text.strip()[:500]
        await state.update_data(location_name=location_name)
        location_text = location_name if location_name else "Не указано"
        await bot.send_message(
            chat_id=message.chat.id,
            text=f"✅ Место: {location_text}\n\n🍺 Будет ли выбор пива на событии?",
            reply_markup=get_beer_choice_keyboard(),
        )
        await state.set_state(EventCreationStates.waiting_for_beer_choice)
    except Exception as e:
        logger.error(f"Error processing event location name: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка. Попробуйте позже.",
            reply_markup=get_cancel_keyboard(),
        )


@router.callback_query(
    lambda c: c.data in ["choice_yes", "choice_no"],
)
async def process_beer_choice(
    callback_query: types.CallbackQuery, bot: Bot, state: FSMContext
):
    try:
        await callback_query.answer()
        has_beer_choice = callback_query.data == "choice_yes"
        await state.update_data(has_beer_choice=has_beer_choice)
        if has_beer_choice:
            await bot.edit_message_text(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                text="🍺 Введите два варианта пива через запятую\nНапример: IPA, Wheat Beer",
                reply_markup=get_cancel_keyboard(),
            )
            await state.set_state(EventCreationStates.waiting_for_beer_options)
        else:
            await finalize_event_creation(
                callback_query.message, bot, state, None, None
            )
    except Exception as e:
        logger.error(f"Error processing beer choice: {e}", exc_info=True)
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="Произошла ошибка. Попробуйте позже.",
            reply_markup=get_cancel_keyboard(),
        )


@router.message(EventCreationStates.waiting_for_beer_options)
async def process_beer_options(message: types.Message, bot: Bot, state: FSMContext):
    try:
        beer_options = [option.strip() for option in message.text.split(",")]
        if len(beer_options) != 2 or not all(
            1 <= len(option) <= 100 for option in beer_options
        ):
            await bot.send_message(
                chat_id=message.chat.id,
                text="❌ Введите ровно два варианта пива через запятую (каждый от 1 до 100 символов)\nНапример: IPA, Wheat Beer",
                reply_markup=get_cancel_keyboard(),
            )
            return
        await finalize_event_creation(
            message, bot, state, beer_options[0], beer_options[1]
        )
    except Exception as e:
        logger.error(f"Error processing beer options: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка. Попробуйте позже.",
            reply_markup=get_cancel_keyboard(),
        )


async def finalize_event_creation(
    message: types.Message,
    bot: Bot,
    state: FSMContext,
    beer_option_1: str | None,
    beer_option_2: str | None,
):
    try:
        data = await state.get_data()
        has_beer_choice = data.get("has_beer_choice", False)
        if has_beer_choice and (not beer_option_1 or not beer_option_2):
            await bot.send_message(
                chat_id=message.chat.id,
                text="❌ Ошибка: для события с выбором пива необходимо указать два варианта пива.",
                reply_markup=get_cancel_keyboard(),
            )
            return
        event_data = EventCreate(
            name=data["name"],
            event_date=data["event_date"],
            event_time=data["event_time"],
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            location_name=data.get("location_name"),
            has_beer_choice=has_beer_choice,
            beer_option_1=beer_option_1,
            beer_option_2=beer_option_2,
            created_by=message.from_user.id,
        )
        async for session in get_async_session():
            event = await EventRepository.create_event(session, event_data)
            summary = f"🎉 Событие создано!\n\n"
            summary += f"📝 Название: {event.name}\n"
            summary += f"📅 Дата: {event.event_date.strftime('%d.%m.%Y')}\n"
            summary += f"🕐 Время: {event.event_time.strftime('%H:%M')}\n"
            summary += f"📍 Место: {event.location_name or 'Не указано'}\n"
            summary += f"🍺 Выбор пива: {'Да' if event.has_beer_choice else 'Нет'}\n"
            if event.has_beer_choice and event.beer_option_1 and event.beer_option_2:
                summary += (
                    f"🍻 Варианты: {event.beer_option_1}, {event.beer_option_2}\n"
                )
            await bot.send_message(chat_id=message.chat.id, text=summary)
            await send_event_notifications(bot, event)
            logger.info(f"Event created: {event.id} by {message.from_user.id}")
        await state.clear()
    except ProgrammingError as e:
        logger.error(f"Database schema error: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="Ошибка базы данных. Пожалуйста, свяжитесь с администратором.",
        )
    except Exception as e:
        logger.error(f"Error finalizing event creation: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка при создании события. Попробуйте позже.",
        )


async def send_event_notifications(bot: Bot, event):
    try:
        async for session in get_async_session():
            users = await UserRepository.get_all_users(session, limit=1000)
            notification_text = f"🎉 Новое событие!\n\n"
            notification_text += f"📝 {event.name}\n"
            notification_text += f"📅 {event.event_date.strftime('%d.%m.%Y')}\n"
            notification_text += f"🕐 {event.event_time.strftime('%H:%M')}\n"
            if event.location_name:
                notification_text += f"📍 {event.location_name}\n"
            if event.has_beer_choice and event.beer_option_1 and event.beer_option_2:
                notification_text += (
                    f"🍻 Варианты пива: {event.beer_option_1}, {event.beer_option_2}\n"
                )
            else:
                default_beer = random.choice(["Пенный Изотоник", "Вкуснейший лагер"])
                notification_text += f"🍺 На финише ждем: {default_beer}\n"
            notification_text += "\nУвидимся на событии! 🎊"
            successful_sends = 0
            failed_sends = 0
            for user in users:
                try:
                    await bot.send_message(
                        chat_id=user.telegram_id, text=notification_text
                    )
                    successful_sends += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to send notification to user {user.telegram_id}: {e}"
                    )
                    failed_sends += 1
            logger.info(
                f"Event notifications sent: {successful_sends} successful, {failed_sends} failed"
            )
    except Exception as e:
        logger.error(f"Error sending event notifications: {e}", exc_info=True)


@router.callback_query(lambda c: c.data == "cancel_event_creation")
async def cancel_event_creation(
    callback_query: types.CallbackQuery, bot: Bot, state: FSMContext
):
    try:
        await callback_query.answer()
        await state.clear()
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="❌ Создание события отменено.",
        )
    except Exception as e:
        logger.error(f"Error canceling event creation: {e}", exc_info=True)
