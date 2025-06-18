import asyncio
import os
import traceback
from datetime import datetime
from typing import Optional, Tuple
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import Update, Message, CallbackQuery
from bot.core.database import init_db, check_db_connection
from bot.handlers import (
    start,
    beer_selection,
    profile,
    event_creation,
    events_list,
    delete_event,
    hero_of_the_day,
)
from bot.utils.logger import setup_logger
from dotenv import load_dotenv

logger = setup_logger(__name__)


def escape_html(text: str) -> str:
    """Экранирует специальные символы для HTML."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class ErrorInfo:
    def __init__(self, exception: Exception, update: Optional[Update] = None):
        self.exception = exception
        self.exception_name = type(exception).__name__
        self.exception_message = str(exception)
        self.error_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.update = update
        self.traceback_info = traceback.format_exc()
        self.traceback_snippet = self._format_traceback()
        self.error_location = self._get_error_location()

    def _get_error_location(self) -> str:
        if not hasattr(self.exception, "__traceback__"):
            return "❓ Неизвестное местоположение"
        tb = traceback.extract_tb(self.exception.__traceback__)
        if not tb:
            return "❓ Неизвестное местоположение"
        last_call = tb[-1]
        filename = last_call.filename
        line = last_call.lineno
        func = last_call.name
        code_line = last_call.line.strip() if last_call.line else "???"
        return (
            f"📂 <b>Файл:</b> {escape_html(filename)}\n"
            f"📌 <b>Строка:</b> {line}\n"
            f"🔹 <b>Функция:</b> {escape_html(func)}\n"
            f"🖥 <b>Код:</b> <pre>{escape_html(code_line)}</pre>"
        )

    def _format_traceback(self, max_length: int = 2000) -> str:
        tb_lines = self.traceback_info.splitlines()
        snippet = (
            "\n".join(tb_lines[-4:]) if len(tb_lines) >= 4 else self.traceback_info
        )
        if len(snippet) > max_length:
            return snippet[:max_length] + "\n...[сокращено]"
        return escape_html(snippet)

    def get_user_info(self) -> Tuple[Optional[int], Optional[str], Optional[str]]:
        if not self.update:
            return None, None, None
        if self.update.message:
            return (
                self.update.message.from_user.id,
                self.update.message.from_user.full_name,
                self.update.message.text,
            )
        elif self.update.callback_query:
            return (
                self.update.callback_query.from_user.id,
                self.update.callback_query.from_user.full_name,
                self.update.callback_query.data,
            )
        return None, None, None


class ErrorNotificationMiddleware(BaseMiddleware):
    def __init__(self, bot_token: str, group_chat_id: str):
        super().__init__()
        self.bot = Bot(token=bot_token)
        self.group_chat_id = group_chat_id

    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except Exception as e:
            # Получаем объект Update из data или event
            update = data.get("event_update")
            if not update and isinstance(event, Update):
                update = event
            logger.info(
                f"Update object in middleware: {update}"
            )  # Отладочное логирование

            error_info = ErrorInfo(e, update)

            # Логируем ошибку (записывается в файл, но не в консоль для ERROR)
            logger.error(
                "Ошибка %s: %s\nМестоположение: %s\nTraceback: %s",
                error_info.exception_name,
                error_info.exception_message,
                error_info.error_location.replace("\n", " | "),
                error_info.traceback_snippet,
            )

            # Формируем сообщение для группы Telegram
            user_id, user_name, user_message = error_info.get_user_info()
            admin_message = (
                f"⚠️ <b>Ошибка в боте!</b>\n\n"
                f"⏰ <b>Время:</b> {error_info.error_time}\n\n"
                f"👤 <b>Пользователь:</b> {escape_html(user_name or 'Неизвестно')}\n"
                f"🆔 <b>ID:</b> {user_id or 'Неизвестно'}\n"
                f"💬 <b>Сообщение:</b> {escape_html(user_message or 'Неизвестно')}\n\n"
                f"❌ <b>Тип ошибки:</b> {escape_html(error_info.exception_name)}\n"
                f"📝 <b>Описание:</b> {escape_html(error_info.exception_message)}\n\n"
                f"📍 <b>Местоположение:</b>\n{error_info.error_location}\n\n"
                f"📚 <b>Трейсбек:</b>\n<pre>{error_info.traceback_snippet}</pre>"
            )

            # Отправляем уведомление в группу Telegram
            try:
                if len(admin_message) > 4000:
                    admin_message = admin_message[:4000] + "...\n[Message truncated]"
                await self.bot.send_message(
                    chat_id=self.group_chat_id,
                    text=admin_message,
                    parse_mode="HTML",
                )
            except Exception as send_error:
                logger.error(
                    f"Failed to send error notification to Telegram: {send_error}"
                )

            # Отправляем сообщение пользователю, если возможно
            bot = data.get("bot")
            if bot and hasattr(event, "chat"):
                try:
                    await bot.send_message(
                        chat_id=event.chat.id,
                        text="❌ Произошла ошибка. Пожалуйста, попробуйте позже.",
                    )
                except Exception as send_error:
                    logger.error(f"Failed to send error message to user: {send_error}")

            raise  # Перебрасываем исключение для дальнейшей обработки aiogram


async def main():
    try:
        load_dotenv()
        bot_token = os.getenv("BOT_TOKEN")
        group_chat_id = os.getenv("FOR_LOGS")  # Используем FOR_LOGS, как в вашем коде
        if not bot_token:
            logger.error("BOT_TOKEN not found in environment variables. Exiting...")
            return
        if not group_chat_id:
            logger.error("FOR_LOGS not found in environment variables. Exiting...")
            return
        if not await check_db_connection():
            logger.error(
                "Failed to connect to the database during initial check. Exiting..."
            )
            return
        await init_db()
        bot = Bot(token=bot_token)
        dp = Dispatcher(storage=MemoryStorage())
        dp.update.middleware(ErrorNotificationMiddleware(bot_token, group_chat_id))
        dp.include_routers(
            start.router,
            beer_selection.router,
            profile.router,
            event_creation.router,
            events_list.router,
            delete_event.router,
            hero_of_the_day.router,
        )
        logger.info("Bot successfully initialized and starting polling...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Critical error in main execution: {e}")


if __name__ == "__main__":
    asyncio.run(main())
