import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.core.database import init_db, check_db_connection
from bot.handlers import (
    start,
    beer_selection,
    profile,
)  # __init__ уже импортирует все нужные роутеры
from dotenv import load_dotenv

# Настройка логирования
log_directory = "logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),  # Уровень логирования из .env
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(log_directory, "bot.log")),  # Логи в файл
        logging.StreamHandler(),  # Логи в консоль
    ],
)
logger = logging.getLogger(__name__)


async def main():
    try:
        load_dotenv()  # Загрузка переменных окружения из .env файла
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            logger.error("BOT_TOKEN not found in environment variables. Exiting...")
            return
        logger.info("Checking database connection...")
        if not await check_db_connection():
            logger.error(
                "Failed to connect to the database during initial check. Exiting..."
            )
            return
        logger.info("Database connection successful. Initializing database schema...")
        await init_db()  # Инициализация БД (создание таблиц)
        logger.info("Database initialized.")
        bot = Bot(token=bot_token)
        dp = Dispatcher(storage=MemoryStorage())  # MemoryStorage для FSM
        # Регистрация роутеров
        dp.include_routers(start.router, beer_selection.router, profile.router)
        # (Опционально: добавить роутер для /stats, если он будет реализован)
        logger.info("Starting bot polling...")
        await bot.delete_webhook(
            drop_pending_updates=True
        )  # Удаление вебхука и пропуск старых апдейтов перед запуском поллинга
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(
            f"Critical error in main execution: {e}", exc_info=True
        )  # exc_info для полного стектрейса


if __name__ == "__main__":
    asyncio.run(main())
