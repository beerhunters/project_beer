from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.core.database import get_async_session
from bot.core.models import Event
from bot.repositories.user_repo import UserRepository
from bot.repositories.event_repo import EventRepository
from bot.core.schemas import EventCreate
from bot.utils.logger import setup_logger
import pendulum
import os
import re
from datetime import time, datetime
from typing import Optional
from sqlalchemy.exc import ProgrammingError, IntegrityError
from aiogram.exceptions import TelegramAPIError
from bot.tasks.celery_app import app as celery_app
from sqlalchemy import update

logger = setup_logger(__name__)
router = Router()
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "267863612"))


class EventCreationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_location = State()
    waiting_for_location_name = State()
    waiting_for_description = State()
    waiting_for_image = State()
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


def get_notification_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text="🍺 Выбрать пиво", callback_data="cmd_beer")
    )
    builder.add(
        types.InlineKeyboardButton(text="🏠 В начало", callback_data="cmd_start")
    )
    builder.adjust(2)
    return builder.as_markup()


@router.message(Command("create_event"))
async def create_event_handler(message: types.Message, bot: Bot, state: FSMContext):
    try:
        if message.chat.type != "private":
            await bot.send_message(
                chat_id=message.chat.id,
                text="❌ Команда доступна только в личных сообщениях.",
            )
            return
        if message.from_user.id != ADMIN_TELEGRAM_ID:
            await bot.send_message(
                chat_id=message.chat.id, text="❌ У вас нет прав для создания событий."
            )
            return
        await bot.send_message(
            chat_id=message.chat.id,
            text="🎉 Создание нового события!\n\n📝 Введите название события (1-200 символов):",
            reply_markup=get_cancel_keyboard(),
        )
        await state.set_state(EventCreationStates.waiting_for_name)
    except Exception as e:
        logger.error(f"Error in create_event handler: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка. Попробуйте позже.",
            reply_markup=get_cancel_keyboard(),
        )
        await state.clear()


@router.message(EventCreationStates.waiting_for_name)
async def process_event_name(message: types.Message, bot: Bot, state: FSMContext):
    try:
        name = message.text.strip()
        if not name or len(name) > 200:
            await bot.send_message(
                chat_id=message.chat.id,
                text="❌ Название должно быть от 1 до 200 символов и не пустым. Попробуйте еще раз:",
                reply_markup=get_cancel_keyboard(),
            )
            return
        await state.update_data(name=name)
        await bot.send_message(
            chat_id=message.chat.id,
            text=f"✅ Название: {name}\n\n📅 Введите дату события в формате ДД.ММ.ГГГГ\nНапример: 15.12.2025",
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
        await state.clear()


@router.message(EventCreationStates.waiting_for_date)
async def process_event_date(message: types.Message, bot: Bot, state: FSMContext):
    try:
        date_str = message.text.strip()
        if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", date_str):
            await bot.send_message(
                chat_id=message.chat.id,
                text="❌ Неверный формат даты! Используйте формат ДД.ММ.ГГГГ\nНапример: 15.12.2025",
                reply_markup=get_cancel_keyboard(),
            )
            return
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
            text="❌ Неверный формат даты! Используйте формат ДД.ММ.ГГГГ\nНапример: 15.12.2025",
            reply_markup=get_cancel_keyboard(),
        )
    except Exception as e:
        logger.error(f"Error processing event date: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка. Попробуйте позже.",
            reply_markup=get_cancel_keyboard(),
        )
        await state.clear()


@router.message(EventCreationStates.waiting_for_time)
async def process_event_time(message: types.Message, bot: Bot, state: FSMContext):
    try:
        time_str = message.text.strip()
        if not re.match(r"^\d{2}:\d{2}$", time_str):
            await bot.send_message(
                chat_id=message.chat.id,
                text="❌ Неверный формат времени! Используйте формат ЧЧ:ММ\nНапример: 18:30",
                reply_markup=get_cancel_keyboard(),
            )
            return
        hour, minute = map(int, time_str.split(":"))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            await bot.send_message(
                chat_id=message.chat.id,
                text="❌ Часы должны быть от 0 до 23, минуты от 0 до 59. Попробуйте еще раз:",
                reply_markup=get_cancel_keyboard(),
            )
            return
        event_time = time(hour=hour, minute=minute)
        await state.update_data(event_time=event_time)
        await bot.send_message(
            chat_id=message.chat.id,
            text=f"✅ Время: {event_time.strftime('%H:%M')}\n\n📍 Введите координаты места (широта, долгота) через запятую, например, 59.9343, 30.3351\nИли введите \"-\" для пропуска координат:",
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
        await state.clear()


@router.message(EventCreationStates.waiting_for_location)
async def process_event_location(message: types.Message, bot: Bot, state: FSMContext):
    try:
        input_str = message.text.strip()
        latitude = None
        longitude = None
        if input_str != "-":
            if not re.match(r"^-?\d+\.\d+,-?\d+\.\d+$", input_str):
                await bot.send_message(
                    chat_id=message.chat.id,
                    text='❌ Координаты должны быть в формате "широта,долгота" (например, 59.9343,30.3351) или "-". Попробуйте еще раз:',
                    reply_markup=get_cancel_keyboard(),
                )
                return
            lat_str, lon_str = map(str.strip, input_str.split(","))
            try:
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
                    text='❌ Координаты должны быть числами в формате "широта,долгота" (например, 59.9343,30.3351). Попробуйте еще раз:',
                    reply_markup=get_cancel_keyboard(),
                )
                return
        await state.update_data(latitude=latitude, longitude=longitude)
        await bot.send_message(
            chat_id=message.chat.id,
            text='📍 Введите название места (1-500 символов, например, Бар Крафт) или "-" для пропуска:',
            reply_markup=get_cancel_keyboard(),
        )
        await state.set_state(EventCreationStates.waiting_for_location_name)
    except Exception as e:
        logger.error(f"Error processing event location: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка. Попробуйте позже.",
            reply_markup=get_cancel_keyboard(),
        )
        await state.clear()


@router.message(EventCreationStates.waiting_for_location_name)
async def process_event_location_name(
    message: types.Message, bot: Bot, state: FSMContext
):
    try:
        location_name = None
        input_str = message.text.strip()
        if input_str != "-":
            if not input_str or len(input_str) > 500:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text="❌ Название места должно быть от 1 до 500 символов и не пустым. Попробуйте еще раз:",
                    reply_markup=get_cancel_keyboard(),
                )
                return
            location_name = input_str
        await state.update_data(location_name=location_name)
        location_text = location_name if location_name else "Не указано"
        await bot.send_message(
            chat_id=message.chat.id,
            text=f'✅ Место: {location_text}\n\n📖 Введите описание события (1-1000 символов) или "-" для пропуска:',
            reply_markup=get_cancel_keyboard(),
        )
        await state.set_state(EventCreationStates.waiting_for_description)
    except Exception as e:
        logger.error(f"Error processing event location name: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка. Попробуйте позже.",
            reply_markup=get_cancel_keyboard(),
        )
        await state.clear()


@router.message(EventCreationStates.waiting_for_description)
async def process_event_description(
    message: types.Message, bot: Bot, state: FSMContext
):
    try:
        description = None
        input_str = message.text.strip()
        if input_str != "-":
            if not input_str or len(input_str) > 1000:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text="❌ Описание должно быть от 1 до 1000 символов и не пустым. Попробуйте еще раз:",
                    reply_markup=get_cancel_keyboard(),
                )
                return
            description = input_str
        await state.update_data(description=description)
        desc_text = description if description else "Не указано"
        await bot.send_message(
            chat_id=message.chat.id,
            text=f'✅ Описание: {desc_text}\n\n🖼️ Отправьте изображение для события (фото) или введите "-" для пропуска:',
            reply_markup=get_cancel_keyboard(),
        )
        await state.set_state(EventCreationStates.waiting_for_image)
    except Exception as e:
        logger.error(f"Error processing event description: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка. Попробуйте позже.",
            reply_markup=get_cancel_keyboard(),
        )
        await state.clear()


@router.message(EventCreationStates.waiting_for_image)
async def process_event_image(message: types.Message, bot: Bot, state: FSMContext):
    try:
        image_file_id = None
        if message.text and message.text.strip() == "-":
            pass
        elif message.photo:
            image_file_id = message.photo[-1].file_id
        else:
            await bot.send_message(
                chat_id=message.chat.id,
                text='❌ Отправьте фото или введите "-" для пропуска.',
                reply_markup=get_cancel_keyboard(),
            )
            return
        await state.update_data(image_file_id=image_file_id)
        img_text = "Загружено" if image_file_id else "Не загружено"
        await bot.send_message(
            chat_id=message.chat.id,
            text=f"✅ Изображение: {img_text}\n\n🍺 Будет ли выбор пива на событии? (Да - два варианта пива, Нет - Лагер)",
            reply_markup=get_beer_choice_keyboard(),
        )
        await state.set_state(EventCreationStates.waiting_for_beer_choice)
    except Exception as e:
        logger.error(f"Error processing event image: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="Произошла ошибка. Попробуйте позже.",
            reply_markup=get_cancel_keyboard(),
        )
        await state.clear()


@router.callback_query(lambda c: c.data in ["choice_yes", "choice_no"])
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
                text="🍺 Введите два варианта пива через запятую (каждый 1-100 символов)\nНапример: IPA, Wheat Beer",
                reply_markup=get_cancel_keyboard(),
            )
            await state.set_state(EventCreationStates.waiting_for_beer_options)
        else:
            await finalize_event_creation(
                callback_query.message,
                bot,
                state,
                beer_option_1="Лагер",
                beer_option_2=None,
            )
    except Exception as e:
        logger.error(f"Error processing beer choice: {e}", exc_info=True)
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="Произошла ошибка. Попробуйте позже.",
            reply_markup=get_cancel_keyboard(),
        )
        await state.clear()


@router.message(EventCreationStates.waiting_for_beer_options)
async def process_beer_options(message: types.Message, bot: Bot, state: FSMContext):
    try:
        input_str = message.text.strip()
        if not re.match(r"[^,]+,[^,]+", input_str):
            await bot.send_message(
                chat_id=message.chat.id,
                text="❌ Введите ровно два варианта пива через запятую (без лишних запятых)\nНапример: IPA, Wheat Beer",
                reply_markup=get_cancel_keyboard(),
            )
            return
        beer_options = [option.strip() for option in input_str.split(",")]
        if len(beer_options) != 2 or not all(
            1 <= len(option) <= 100 and option for option in beer_options
        ):
            await bot.send_message(
                chat_id=message.chat.id,
                text="❌ Каждый вариант пива должен быть от 1 до 100 символов и не пустым. Попробуйте еще раз:",
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
        await state.clear()


async def finalize_event_creation(
    message: types.Message,
    bot: Bot,
    state: FSMContext,
    beer_option_1: Optional[str],
    beer_option_2: Optional[str],
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
            description=data.get("description"),
            image_file_id=data.get("image_file_id"),
            has_beer_choice=has_beer_choice,
            beer_option_1=beer_option_1,
            beer_option_2=beer_option_2,
            created_by=int(message.from_user.id),
        )
        async for session in get_async_session():
            try:
                event = await EventRepository.create_event(session, event_data)
                # Schedule one-time Celery task
                event_start = pendulum.datetime(
                    year=event.event_date.year,
                    month=event.event_date.month,
                    day=event.event_date.day,
                    hour=event.event_time.hour,
                    minute=event.event_time.minute,
                    tz="Europe/Moscow",
                )
                logger.debug(
                    f"event_start type: {type(event_start)}, value: {event_start}"
                )
                if not isinstance(event_start, pendulum.DateTime):
                    raise ValueError(
                        f"event_start is not a pendulum.DateTime: {type(event_start)}"
                    )
                task_id = None
                try:
                    # Primary method: manual datetime construction
                    eta = datetime(
                        year=event_start.year,
                        month=event_start.month,
                        day=event_start.day,
                        hour=event_start.hour,
                        minute=event_start.minute,
                        tzinfo=event_start.tzinfo,
                    )
                    if not isinstance(eta, datetime):
                        raise ValueError(f"eta is not a datetime object: {type(eta)}")
                    task = celery_app.send_task(
                        "bot.tasks.bartender_notification.process_event_notification",
                        args=(event.id,),
                        eta=eta,
                    )
                    task_id = task.id
                    logger.info(
                        f"Scheduled Celery task {task_id} for event {event.id} at {eta}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to schedule task (primary) for event {event.id}: {e}",
                        exc_info=True,
                    )
                    # Fallback: try to_pydatetime()
                    try:
                        eta = event_start.to_pydatetime()
                        task = celery_app.send_task(
                            "bot.tasks.bartender_notification.process_event_notification",
                            args=(event.id,),
                            eta=eta,
                        )
                        task_id = task.id
                        logger.info(
                            f"Scheduled Celery task (to_pydatetime fallback) {task_id} for event {event.id} at {eta}"
                        )
                    except Exception as e2:
                        logger.error(
                            f"Fallback scheduling (to_pydatetime) failed for event {event.id}: {e2}",
                            exc_info=True,
                        )
                        await bot.send_message(
                            chat_id=message.chat.id,
                            text="⚠️ Событие создано, но уведомление бармену не запланировано. Свяжитесь с администратором.",
                        )
                        await state.clear()
                        return
                # Save task_id to event
                if task_id:
                    stmt = (
                        update(Event)
                        .where(Event.id == event.id)
                        .values(celery_task_id=task_id)
                    )
                    await session.execute(stmt)
                    await session.commit()
                    logger.info(f"Saved Celery task ID {task_id} for event {event.id}")
                summary = f"🎉 Событие создано!\n\n"
                summary += f"📝 Название: {event.name}\n"
                summary += f"📅 Дата: {event.event_date.strftime('%d.%m.%Y')}\n"
                summary += f"🕐 Время: {event.event_time.strftime('%H:%M')}\n"
                summary += f"📍 Место: {event.location_name or 'Не указано'}\n"
                summary += f"📖 Описание: {event.description or 'Не указано'}\n"
                summary += (
                    f"🖼️ Изображение: {'Есть' if event.image_file_id else 'Нет'}\n"
                )
                summary += (
                    f"🍺 Выбор пива: {'Да' if event.has_beer_choice else 'Нет'}\n"
                )
                if (
                    event.has_beer_choice
                    and event.beer_option_1
                    and event.beer_option_2
                ):
                    summary += (
                        f"🍻 Варианты: {event.beer_option_1}, {event.beer_option_2}\n"
                    )
                elif not event.has_beer_choice:
                    summary += f"🍺 Пиво: Лагер\n"
                await bot.send_message(chat_id=message.chat.id, text=summary)
                await send_event_notifications(bot, event)
                logger.info(f"Event created: {event.id} by {message.from_user.id}")
            except IntegrityError as e:
                logger.error(
                    f"Database integrity error creating event: {e}", exc_info=True
                )
                await bot.send_message(
                    chat_id=message.chat.id,
                    text="❌ Ошибка: событие с такими параметрами уже существует или данные некорректны.",
                    reply_markup=get_cancel_keyboard(),
                )
                return
            except Exception as e:
                logger.error(f"Unexpected error creating event: {e}", exc_info=True)
                raise
        await state.clear()
    except ProgrammingError as e:
        logger.error(f"Database schema error: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="❌ Ошибка базы данных. Пожалуйста, свяжитесь с администратором.",
            reply_markup=get_cancel_keyboard(),
        )
    except Exception as e:
        logger.error(f"Error finalizing event creation: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="❌ Произошла ошибка при создании события. Попробуйте позже.",
            reply_markup=get_cancel_keyboard(),
        )
    finally:
        if await state.get_state():
            await state.clear()


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
            if event.description:
                notification_text += f"📖 {event.description}\n"
            if event.has_beer_choice:
                notification_text += (
                    f"🍻 Варианты пива: {event.beer_option_1}, {event.beer_option_2}\n"
                )
            else:
                notification_text += f"🍺 Пиво: Лагер\n"
            notification_text += "\nУвидимся на событии! 🎊"
            successful_sends = 0
            failed_sends = 0
            for user in users:
                try:
                    if event.image_file_id:
                        await bot.send_photo(
                            chat_id=user.telegram_id,
                            photo=event.image_file_id,
                            caption=notification_text,
                            reply_markup=get_notification_keyboard(),
                        )
                    else:
                        await bot.send_message(
                            chat_id=user.telegram_id,
                            text=notification_text,
                            reply_markup=get_notification_keyboard(),
                        )
                    successful_sends += 1
                except TelegramAPIError as e:
                    logger.warning(
                        f"Failed to send notification to user {user.telegram_id}: {e}"
                    )
                    failed_sends += 1
                except Exception as e:
                    logger.error(
                        f"Unexpected error sending notification to user {user.telegram_id}: {e}"
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
        logger.error(f"Error cancelling event creation: {e}", exc_info=True)
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="Произошла ошибка. Попробуйте позже.",
            reply_markup=get_cancel_keyboard(),
        )
