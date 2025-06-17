from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.core.database import get_async_session
from bot.repositories.event_repo import EventRepository
from bot.utils.logger import setup_logger
from bot.handlers.event_creation import get_cancel_keyboard
import pendulum
import os

logger = setup_logger(__name__)
router = Router()
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "267863612"))
EVENTS_PER_PAGE = 5


class EventListStates(StatesGroup):
    browsing = State()


def get_events_keyboard(events, current_page, total_events):
    builder = InlineKeyboardBuilder()
    for event in events:
        builder.add(
            types.InlineKeyboardButton(
                text=f"🗑️ Удалить ID {event.id}",
                callback_data=f"delete_event_{event.id}",
            )
        )
    total_pages = (total_events + EVENTS_PER_PAGE - 1) // EVENTS_PER_PAGE
    if total_pages > 1:
        if current_page > 0:
            builder.add(
                types.InlineKeyboardButton(
                    text="⬅️ Назад", callback_data=f"prev_page_{current_page}"
                )
            )
        if current_page < total_pages - 1:
            builder.add(
                types.InlineKeyboardButton(
                    text="➡️ Вперед", callback_data=f"next_page_{current_page}"
                )
            )
    # builder.adjust(1, 2 if total_pages > 1 else 1)
    builder.adjust(1, 2)
    return builder.as_markup()


async def send_events_list(
    message: types.Message, bot: Bot, state: FSMContext, page: int = 0
):
    async for session in get_async_session():
        today = pendulum.now("Europe/Moscow").date()
        offset = page * EVENTS_PER_PAGE
        events = await EventRepository.get_all_events(
            session,
            offset=offset,
            limit=EVENTS_PER_PAGE,
            upcoming_only=True,
            date_from=today,
        )
        total_events = len(
            await EventRepository.get_all_events(
                session, upcoming_only=True, date_from=today
            )
        )
        if not events:
            await bot.send_message(
                chat_id=message.chat.id,
                text="📅 Нет предстоящих событий.",
            )
            await state.clear()
            return
        response = f"📅 Список предстоящих событий (страница {page + 1} из {(total_events + EVENTS_PER_PAGE - 1) // EVENTS_PER_PAGE}):\n\n"
        for event in events:
            response += f"🆔 ID: {event.id}\n"
            response += f"📝 Название: {event.name}\n"
            response += f"📅 Дата: {event.event_date.strftime('%d.%m.%Y')}\n"
            response += f"🕐 Время: {event.event_time.strftime('%H:%M')}\n"
            response += f"📍 Место: {event.location_name or 'Не указано'}\n"
            response += f"📖 Описание: {event.description or 'Не указано'}\n"
            response += f"🖼️ Изображение: {'Есть' if event.image_file_id else 'Нет'}\n"
            response += f"🍺 Выбор пива: {'Да' if event.has_beer_choice else 'Нет'}\n"
            if event.has_beer_choice and event.beer_option_1 and event.beer_option_2:
                response += (
                    f"🍻 Варианты: {event.beer_option_1}, {event.beer_option_2}\n"
                )
            elif not event.has_beer_choice:
                response += f"🍺 Пиво: Лагер\n"
            response += "─" * 30 + "\n"
        keyboard = get_events_keyboard(events, page, total_events)
        await bot.send_message(
            chat_id=message.chat.id,
            text=response,
            reply_markup=keyboard,
        )
        await state.update_data(current_page=page)
        await state.set_state(EventListStates.browsing)
        logger.info(f"Events list page {page} requested by {message.from_user.id}")


@router.message(Command("events_list"))
async def events_list_handler(message: types.Message, bot: Bot, state: FSMContext):
    try:
        if message.chat.type != "private":
            await bot.send_message(
                chat_id=message.chat.id,
                text="❌ Команда доступна только в личных сообщениях.",
            )
            return
        if message.from_user.id != ADMIN_TELEGRAM_ID:
            await bot.send_message(
                chat_id=message.chat.id,
                text="❌ У вас нет прав для просмотра списка событий.",
            )
            return
        await send_events_list(message, bot, state, page=0)
    except Exception as e:
        logger.error(f"Error in events_list handler: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="❌ Произошла ошибка при получении списка событий. Попробуйте позже.",
        )
        await state.clear()


@router.callback_query(
    lambda c: c.data.startswith("next_page_") or c.data.startswith("prev_page_")
)
async def handle_pagination(
    callback_query: types.CallbackQuery, bot: Bot, state: FSMContext
):
    try:
        await callback_query.answer()
        data = await state.get_data()
        current_page = data.get("current_page", 0)
        action, page_str, page = callback_query.data.split("_")
        page = int(page)
        new_page = page + 1 if action == "next" else page - 1
        if new_page < 0:
            return
        async for session in get_async_session():
            today = pendulum.now("Europe/Moscow").date()
            total_events = len(
                await EventRepository.get_all_events(
                    session, upcoming_only=True, date_from=today
                )
            )
            total_pages = (total_events + EVENTS_PER_PAGE - 1) // EVENTS_PER_PAGE
            if new_page >= total_pages:
                return
            offset = new_page * EVENTS_PER_PAGE
            events = await EventRepository.get_all_events(
                session,
                offset=offset,
                limit=EVENTS_PER_PAGE,
                upcoming_only=True,
                date_from=today,
            )
            response = f"📅 Список предстоящих событий (страница {new_page + 1} из {total_pages}):\n\n"
            for event in events:
                response += f"🆔 ID: {event.id}\n"
                response += f"📝 Название: {event.name}\n"
                response += f"📅 Дата: {event.event_date.strftime('%d.%m.%Y')}\n"
                response += f"🕐 Время: {event.event_time.strftime('%H:%M')}\n"
                response += f"📍 Место: {event.location_name or 'Не указано'}\n"
                response += f"📖 Описание: {event.description or 'Не указано'}\n"
                response += (
                    f"🖼️ Изображение: {'Есть' if event.image_file_id else 'Нет'}\n"
                )
                response += (
                    f"🍺 Выбор пива: {'Да' if event.has_beer_choice else 'Нет'}\n"
                )
                if (
                    event.has_beer_choice
                    and event.beer_option_1
                    and event.beer_option_2
                ):
                    response += (
                        f"🍻 Варианты: {event.beer_option_1}, {event.beer_option_2}\n"
                    )
                elif not event.has_beer_choice:
                    response += f"🍺 Пиво: Лагер\n"
                response += "─" * 30 + "\n"
            keyboard = get_events_keyboard(events, new_page, total_events)
            await bot.edit_message_text(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                text=response,
                reply_markup=keyboard,
            )
            await state.update_data(current_page=new_page)
            logger.info(
                f"Events list navigated to page {new_page} by {callback_query.from_user.id}"
            )
    except Exception as e:
        logger.error(f"Error in pagination handler: {e}", exc_info=True)
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="❌ Произошла ошибка при переключении страницы. Попробуйте позже.",
        )
        await state.clear()


@router.callback_query(lambda c: c.data.startswith("delete_event_"))
async def initiate_delete_event(
    callback_query: types.CallbackQuery, bot: Bot, state: FSMContext
):
    try:
        await callback_query.answer()
        event_id = int(callback_query.data.split("_")[2])
        if callback_query.from_user.id != ADMIN_TELEGRAM_ID:
            await bot.edit_message_text(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                text="❌ У вас нет прав для удаления событий.",
            )
            return
        async for session in get_async_session():
            event = await EventRepository.get_event_by_id(session, event_id)
            if not event:
                await bot.edit_message_text(
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    text=f"❌ Событие с ID {event_id} не найдено.",
                )
                return
            await state.update_data(event_id=event_id)
            await bot.send_message(
                chat_id=callback_query.message.chat.id,
                text=f"🗑️ Подтвердите удаление события ID {event_id} ({event.name}):",
                reply_markup=get_cancel_keyboard(),
            )
            from bot.handlers.delete_event import EventDeletionStates

            await state.set_state(EventDeletionStates.waiting_for_event_id)
            logger.info(
                f"Delete event {event_id} initiated by {callback_query.from_user.id}"
            )
    except Exception as e:
        logger.error(f"Error initiating delete event: {e}", exc_info=True)
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="❌ Произошла ошибка при попытке удаления события. Попробуйте позже.",
        )
        await state.clear()
