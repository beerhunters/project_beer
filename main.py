import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.core.database import init_db, check_db_connection
from bot.handlers import start, beer_selection, profile, event_creation
from bot.utils.logger import setup_logger
from dotenv import load_dotenv

logger = setup_logger(__name__)


async def main():
    try:
        load_dotenv()
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            logger.error("BOT_TOKEN not found in environment variables. Exiting...")
            return
        if not await check_db_connection():
            logger.error(
                "Failed to connect to the database during initial check. Exiting..."
            )
            return
        await init_db()
        bot = Bot(token=bot_token)
        dp = Dispatcher(storage=MemoryStorage())
        dp.include_routers(
            start.router, beer_selection.router, profile.router, event_creation.router
        )
        logger.info("Bot successfully initialized and starting polling...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Critical error in main execution: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
