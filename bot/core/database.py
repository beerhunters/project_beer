# bot/core/database.py
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
import os
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# Базовый класс для моделей
Base = declarative_base()

# Настройки БД
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://bot_user:bot_password@postgres:5432/beer_bot"
)

# Создание движка
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Установить True для отладки SQL запросов
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
)

# Фабрика сессий
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Получение асинхронной сессии БД"""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Инициализация БД - создание всех таблиц"""
    try:
        async with engine.begin() as conn:
            # Импортируем модели для создания таблиц
            from bot.core.models import User, BeerChoice

            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


async def check_db_connection():
    """Проверка подключения к БД"""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False
