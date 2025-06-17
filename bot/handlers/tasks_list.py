from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.utils.logger import setup_logger
from bot.tasks.celery_app import app as celery_app
from celery.result import AsyncResult
import os
import redis

logger = setup_logger(__name__)
router = Router()
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "267863612"))
TASKS_PER_PAGE = 5

# Initialize Redis client
redis_client = redis.Redis(
    host="redis", port=6379, db=0, decode_responses=True, socket_timeout=5
)


class TaskListStates(StatesGroup):
    browsing = State()


def get_tasks_keyboard(tasks, current_page, total_tasks, show_all=False):
    builder = InlineKeyboardBuilder()
    for task_id in tasks:
        builder.add(
            types.InlineKeyboardButton(
                text=f"🗑️ Отозвать ID {task_id}", callback_data=f"revoke_task_{task_id}"
            )
        )
    total_pages = (total_tasks + TASKS_PER_PAGE - 1) // TASKS_PER_PAGE
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
    builder.add(
        types.InlineKeyboardButton(
            text="🔄 Показать все" if not show_all else "🔄 Только активные",
            callback_data="toggle_all_tasks",
        )
    )
    builder.adjust(1, 2 if total_pages > 1 else 1)
    return builder.as_markup()


async def send_tasks_list(
    message: types.Message,
    bot: Bot,
    state: FSMContext,
    page: int = 0,
    show_all: bool = False,
):
    try:
        all_tasks = []
        if show_all:
            # Fetch all tasks from Redis
            task_keys = redis_client.keys("celery-task-meta-*")
            for key in task_keys:
                task_id = key.replace("celery-task-meta-", "")
                result = AsyncResult(task_id, app=celery_app)
                task_info = {
                    "id": task_id,
                    "name": getattr(result, "name", "Unknown"),
                    "args": getattr(result, "args", []),
                    "kwargs": getattr(result, "kwargs", {}),
                    "time_start": getattr(result, "date_done", "Unknown"),
                    "state": result.state,
                }
                all_tasks.append(task_info)
        else:
            # Fetch active tasks
            inspect = celery_app.control.inspect()
            active_tasks = inspect.active() or {}
            for worker, tasks in active_tasks.items():
                for task in tasks:
                    all_tasks.append(
                        {
                            "id": task["id"],
                            "name": task["name"],
                            "args": task["args"],
                            "kwargs": task["kwargs"],
                            "time_start": task.get("time_start", "Unknown"),
                            "state": "ACTIVE",
                        }
                    )
        total_tasks = len(all_tasks)
        start_idx = page * TASKS_PER_PAGE
        end_idx = start_idx + TASKS_PER_PAGE
        tasks_page = all_tasks[start_idx:end_idx]
        if not tasks_page:
            await bot.send_message(
                chat_id=message.chat.id,
                text=f"📋 Нет {'всех' if show_all else 'активных'} задач в Celery.",
            )
            await state.clear()
            return
        response = f"📋 Список {'всех' if show_all else 'активных'} задач (страница {page + 1} из {(total_tasks + TASKS_PER_PAGE - 1) // TASKS_PER_PAGE}):\n\n"
        for task in tasks_page:
            response += f"🆔 ID: {task['id']}\n"
            response += f"📝 Название: {task['name']}\n"
            response += f"📤 Аргументы: {task['args']}\n"
            response += f"🔧 Ключевые аргументы: {task['kwargs']}\n"
            response += f"🕐 Время: {task['time_start']}\n"
            response += f"📊 Статус: {task['state']}\n"
            response += "─" * 30 + "\n"
        keyboard = get_tasks_keyboard(
            [task["id"] for task in tasks_page], page, total_tasks, show_all
        )
        await bot.send_message(
            chat_id=message.chat.id,
            text=response,
            reply_markup=keyboard,
        )
        await state.update_data(current_page=page, show_all=show_all)
        await state.set_state(TaskListStates.browsing)
        logger.info(
            f"Tasks list page {page} ({'all' if show_all else 'active'}) requested by {message.from_user.id}"
        )
    except Exception as e:
        logger.error(f"Error fetching tasks list: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="❌ Ошибка при получении списка задач. Попробуйте позже.",
        )
        await state.clear()


@router.message(Command("tasks_list"))
async def tasks_list_handler(message: types.Message, bot: Bot, state: FSMContext):
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
                text="❌ У вас нет прав для просмотра списка задач.",
            )
            return
        await send_tasks_list(message, bot, state, page=0, show_all=False)
    except Exception as e:
        logger.error(f"Error in tasks_list handler: {e}", exc_info=True)
        await bot.send_message(
            chat_id=message.chat.id,
            text="❌ Произошла ошибка при получении списка задач. Попробуйте позже.",
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
        show_all = data.get("show_all", False)
        action, page = callback_query.data.split("_")
        page = int(page)
        new_page = page + 1 if action == "next" else page - 1
        if new_page < 0:
            return
        all_tasks = []
        if show_all:
            task_keys = redis_client.keys("celery-task-meta-*")
            for key in task_keys:
                task_id = key.replace("celery-task-meta-", "")
                result = AsyncResult(task_id, app=celery_app)
                task_info = {
                    "id": task_id,
                    "name": getattr(result, "name", "Unknown"),
                    "args": getattr(result, "args", []),
                    "kwargs": getattr(result, "kwargs", {}),
                    "time_start": getattr(result, "date_done", "Unknown"),
                    "state": result.state,
                }
                all_tasks.append(task_info)
        else:
            inspect = celery_app.control.inspect()
            active_tasks = inspect.active() or {}
            for worker, tasks in active_tasks.items():
                for task in tasks:
                    all_tasks.append(
                        {
                            "id": task["id"],
                            "name": task["name"],
                            "args": task["args"],
                            "kwargs": task["kwargs"],
                            "time_start": task.get("time_start", "Unknown"),
                            "state": "ACTIVE",
                        }
                    )
        total_tasks = len(all_tasks)
        total_pages = (total_tasks + TASKS_PER_PAGE - 1) // TASKS_PER_PAGE
        if new_page >= total_pages:
            return
        start_idx = new_page * TASKS_PER_PAGE
        end_idx = start_idx + TASKS_PER_PAGE
        tasks_page = all_tasks[start_idx:end_idx]
        response = f"📋 Список {'всех' if show_all else 'активных'} задач (страница {new_page + 1} из {total_pages}):\n\n"
        for task in tasks_page:
            response += f"🆔 ID: {task['id']}\n"
            response += f"📝 Название: {task['name']}\n"
            response += f"📤 Аргументы: {task['args']}\n"
            response += f"🔧 Ключевые аргументы: {task['kwargs']}\n"
            response += f"🕐 Время: {task['time_start']}\n"
            response += f"📊 Статус: {task['state']}\n"
            response += "─" * 30 + "\n"
        keyboard = get_tasks_keyboard(
            [task["id"] for task in tasks_page], new_page, total_tasks, show_all
        )
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text=response,
            reply_markup=keyboard,
        )
        await state.update_data(current_page=new_page, show_all=show_all)
        logger.info(
            f"Tasks list navigated to page {new_page} ({'all' if show_all else 'active'}) by {callback_query.from_user.id}"
        )
    except Exception as e:
        logger.error(f"Error in pagination handler: {e}", exc_info=True)
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="❌ Ошибка при переключении страницы. Попробуйте позже.",
        )
        await state.clear()


@router.callback_query(lambda c: c.data == "toggle_all_tasks")
async def toggle_all_tasks(
    callback_query: types.CallbackQuery, bot: Bot, state: FSMContext
):
    try:
        await callback_query.answer()
        data = await state.get_data()
        current_page = data.get("current_page", 0)
        show_all = data.get("show_all", False)
        await send_tasks_list(
            callback_query.message, bot, state, page=current_page, show_all=not show_all
        )
    except Exception as e:
        logger.error(f"Error toggling tasks view: {e}", exc_info=True)
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="❌ Ошибка при переключении вида задач. Попробуйте позже.",
        )


@router.callback_query(lambda c: c.data.startswith("revoke_task_"))
async def revoke_task(callback_query: types.CallbackQuery, bot: Bot, state: FSMContext):
    try:
        await callback_query.answer()
        task_id = callback_query.data.split("_")[2]
        if callback_query.from_user.id != ADMIN_TELEGRAM_ID:
            await bot.edit_message_text(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                text="❌ У вас нет прав для отзыва задач.",
            )
            return
        celery_app.control.revoke(task_id, terminate=True)
        AsyncResult(task_id, app=celery_app).forget()
        redis_keys = redis_client.keys(f"celery-task-meta-{task_id}*")
        if redis_keys:
            redis_client.delete(*redis_keys)
            logger.info(f"Deleted Redis keys {redis_keys} for task {task_id}")
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text=f"🗑️ Задача ID {task_id} успешно отозвана и удалена.",
        )
        logger.info(
            f"Task {task_id} revoked and cleared by {callback_query.from_user.id}"
        )
    except Exception as e:
        logger.error(f"Error revoking task {task_id}: {e}", exc_info=True)
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="❌ Ошибка при отзыве задачи. Попробуйте позже.",
        )
