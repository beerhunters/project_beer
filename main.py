import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.core.database import init_db, check_db_connection
from bot.handlers import start, beer_selection, profile
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/bot.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


async def main():
    """Основная функция запуска бота"""
    try:
        # Загрузка переменных окружения
        load_dotenv()

        # Проверка подключения к БД
        if not await check_db_connection():
            logger.error("Failed to connect to database. Exiting...")
            return

        # Инициализация БД
        await init_db()

        # Инициализация бота
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            logger.error("BOT_TOKEN not found in environment variables")
            return

        bot = Bot(token=bot_token)
        dp = Dispatcher(storage=MemoryStorage())

        # Регистрация роутеров
        dp.include_routers(start.router, beer_selection.router, profile.router)

        logger.info("Starting bot...")

        # Запуск polling
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
