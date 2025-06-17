from aiogram import Router, Bot
from aiogram.handlers import ErrorHandler
from aiogram.types import Update, InlineKeyboardButton
from bot.utils.logger import setup_logger
from typing import Optional
import traceback
import os
import pendulum

logger = setup_logger(__name__)
router = Router()


class ErrorInfo:
    """Class to store and format error information"""

    def __init__(self, exception: Exception, update: Optional[Update] = None):
        self.exception = exception
        self.exception_name = type(exception).__name__
        self.exception_message = str(exception)
        self.error_time = pendulum.now("Europe/Moscow").strftime("%Y-%m-%d %H:%M:%S")
        self.update = update
        self.traceback_info = traceback.format_exc()
        self.error_location = self._get_error_location()

    def _get_error_location(self) -> str:
        """Get detailed error location information"""
        if not hasattr(self.exception, "__traceback__"):
            return "❓ Unknown location"

        tb = traceback.extract_tb(self.exception.__traceback__)
        if not tb:
            return "❓ Unknown location"

        last_call = tb[-1]
        filename = last_call.filename
        line = last_call.lineno
        func = last_call.name
        code_line = last_call.line.strip() if last_call.line else "???"
        return (
            f"📂 <b>File:</b> {filename}\n"
            f"📌 <b>Line:</b> {line}\n"
            f"🔹 <b>Function:</b> {func}\n"
            f"🖥 <b>Code:</b> <pre>{code_line}</pre>"
        )

    def get_user_info(self) -> tuple[Optional[int], Optional[str], Optional[str]]:
        """Get user information from the update"""
        if not self.update:
            return None, None, None
        if hasattr(self.update, "message") and self.update.message:
            return (
                self.update.message.from_user.id,
                self.update.message.from_user.full_name,
                self.update.message.text,
            )
        elif hasattr(self.update, "callback_query") and self.update.callback_query:
            return (
                self.update.callback_query.from_user.id,
                self.update.callback_query.from_user.full_name,
                self.update.callback_query.data,
            )
        return None, None, None


@router.errors()
class MyErrorHandler(ErrorHandler):
    """Custom error handler for aiogram bot"""

    async def handle(self) -> None:
        exception = getattr(self.event, "exception", None)
        update = getattr(self.event, "update", None)

        if not exception:
            logger.error("Event without exception: %s", self.event)
            return

        error_info = ErrorInfo(exception, update)

        # Log the error with detailed traceback
        logger.error(
            "Error occurred: %s: %s\nLocation: %s\nTraceback: %s",
            error_info.exception_name,
            error_info.exception_message,
            error_info.error_location.replace("\n", " | "),
            error_info.traceback_info,
        )

        # Notify user
        try:
            await self._notify_user(update)
        except Exception as e:
            logger.error("Error notifying user: %s\n%s", str(e), traceback.format_exc())

        # Notify admins
        try:
            await self._notify_admins(error_info)
        except Exception as e:
            logger.error(
                "Error notifying admins: %s\n%s", str(e), traceback.format_exc()
            )

    async def _notify_user(self, update: Optional[Update]) -> None:
        """Send error message to the user"""
        if not update:
            logger.warning("No update object for user notification")
            return

        error_message = "❌ Произошла ошибка. Пожалуйста, попробуйте позже."

        try:
            if update.message:
                await update.message.answer(error_message)
                logger.info("Error message sent to user (Message)")
            elif update.callback_query and update.callback_query.message:
                await update.callback_query.message.answer(error_message)
                logger.info("Error message sent to user (CallbackQuery)")
            else:
                logger.warning("Unknown update type: %s", type(update))
        except Exception as e:
            logger.error("Failed to send user notification: %s", str(e))

    async def _notify_admins(self, error_info: ErrorInfo) -> None:
        """Send detailed error notification to the admin chat"""
        FOR_LOGS = os.getenv("FOR_LOGS")
        if not FOR_LOGS:
            logger.warning("FOR_LOGS not set, skipping admin notification")
            return

        try:
            FOR_LOGS = int(FOR_LOGS)
        except ValueError:
            logger.error("FOR_LOGS is not a valid integer: %s", FOR_LOGS)
            return

        user_id, user_name, user_message = error_info.get_user_info()
        admin_message = (
            f"⚠️ <b>Bot Error!</b>\n\n"
            f"⏰ <b>Time:</b> {error_info.error_time}\n\n"
            f"👤 <b>User:</b> {user_name or 'Unknown'}\n"
            f"🆔 <b>User ID:</b> {user_id or 'Unknown'}\n"
            f"💬 <b>Message:</b> {user_message or 'Unknown'}\n\n"
            f"❌ <b>Error Type:</b> {error_info.exception_name}\n"
            f"📝 <b>Description:</b> {error_info.exception_message}\n\n"
            f"📍 <b>Location:</b>\n{error_info.error_location}\n\n"
            f"📚 <b>Traceback:</b>\n<pre>{error_info.traceback_info}</pre>"
        )

        try:
            await self.bot.send_message(
                chat_id=FOR_LOGS,
                text=admin_message,
                parse_mode="HTML",
            )
            logger.info("Error notification sent to admin chat %s", FOR_LOGS)
        except Exception as e:
            logger.error(
                "Failed to send admin notification to chat %s: %s\n%s",
                FOR_LOGS,
                str(e),
                traceback.format_exc(),
            )
