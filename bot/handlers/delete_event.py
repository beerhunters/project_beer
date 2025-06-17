from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.core.database import get_async_session
from bot.repositories.event_repo import EventRepository
from bot.utils.logger import setup_logger
from bot.handlers.event_creation import get_cancel_keyboard
from bot.tasks.celery_app import app as celery_app
from celery.result import AsyncResult
import os
from sqlalchemy.exc import NoResultFound
import redis

logger = setup_logger(__name__)
router = Router()
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "267863612"))

# Initialize Redis client for manual cleanup
redis_client = redis.Redis(
    host="redis", port=6379, db=0, decode_responses=True, socket_timeout=5
)


class EventDeletionStates(StatesGroup):
    waiting_for_event_id = State()


@router.message(Command("delete_event"))
async def delete_event_handler(message: types.Message, bot: Bot, state: FSMContext):
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
                text="❌ У вас нет прав для удаления событий.",
            )
            return
        await bot.send_message(
            chat_id=message.chat.id,
            text="🗑️ Введите ID события для удаления (число):",
            reply_markup=get_cancel_keyboard(),
        )
        await state.set_state(EventDeletionStates.waiting_for_event_id)
    except Exception as e:
        logger.error(f"Error in delete_event handler: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="❌ Произошла ошибка. Попробуйте позже.",
            reply_markup=get_cancel_keyboard(),
        )
        await state.clear()


@router.message(EventDeletionStates.waiting_for_event_id)
async def process_event_id(message: types.Message, bot: Bot, state: FSMContext):
    try:
        event_id_str = message.text.strip()
        if not event_id_str.isdigit():
            await bot.send_message(
                chat_id=message.chat.id,
                text="❌ ID события должно быть числом. Попробуйте еще раз:",
                reply_markup=get_cancel_keyboard(),
            )
            return
        event_id = int(event_id_str)
        async for session in get_async_session():
            try:
                event = await EventRepository.get_event_by_id(session, event_id)
                if not event:
                    raise NoResultFound
                # Revoke and clear associated Celery task if exists
                if event.celery_task_id:
                    try:
                        # Revoke task
                        celery_app.control.revoke(event.celery_task_id, terminate=True)
                        logger.info(
                            f"Revoked Celery task {event.celery_task_id} for event {event_id}"
                        )
                        # Clear task result
                        AsyncResult(event.celery_task_id, app=celery_app).forget()
                        logger.info(
                            f"Cleared Celery task result {event.celery_task_id} from backend"
                        )
                        # Manually delete Redis keys
                        redis_keys = redis_client.keys(
                            f"celery-task-meta-{event.celery_task_id}*"
                        )
                        if redis_keys:
                            redis_client.delete(*redis_keys)
                            logger.info(
                                f"Deleted Redis keys {redis_keys} for task {event.celery_task_id}"
                            )
                    except Exception as revoke_error:
                        logger.error(
                            f"Failed to revoke or clear Celery task {event.celery_task_id}: {revoke_error}",
                            exc_info=True,
                        )
                # Clear celery_task_id and delete event
                event.celery_task_id = None
                await session.commit()
                await EventRepository.delete_event(session, event_id)
                await bot.send_message(
                    chat_id=message.chat.id,
                    text=f"🗑️ Событие ID {event_id} ({event.name}) успешно удалено.",
                )
                logger.info(f"Event {event_id} deleted by {message.from_user.id}")
            except NoResultFound:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text=f"❌ Событие с ID {event_id} не найдено.",
                    reply_markup=get_cancel_keyboard(),
                )
            except Exception as e:
                logger.error(f"Error deleting event {event_id}: {e}", exc_info=True)
                await bot.send_message(
                    chat_id=message.chat.id,
                    text="❌ Ошибка при удалении события. Попробуйте позже.",
                    reply_markup=get_cancel_keyboard(),
                )
        await state.clear()
    except Exception as e:
        logger.error(f"Error processing event ID for deletion: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="❌ Произошла ошибка. Попробуйте позже.",
            reply_markup=get_cancel_keyboard(),
        )
        await state.clear()


@router.callback_query(lambda c: c.data == "cancel_event_deletion")
async def cancel_event_deletion(
    callback_query: types.CallbackQuery, bot: Bot, state: FSMContext
):
    try:
        await callback_query.answer()
        await state.clear()
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="❌ Удаление события отменено.",
        )
    except Exception as e:
        logger.error(f"Error cancelling event deletion: {e}", exc_info=True)
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="❌ Произошла ошибка. Попробуйте позже.",
            reply_markup=get_cancel_keyboard(),
        )
