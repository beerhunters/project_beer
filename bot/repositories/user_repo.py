# bot/repositories/user_repo.py
import logging
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from bot.core.models import User
from bot.core.schemas import UserCreate, UserUpdate, UserResponse, UserWithChoices

logger = logging.getLogger(__name__)


class UserRepository:

    @staticmethod
    async def create_user(session: AsyncSession, user_data: UserCreate) -> User:
        """Создание нового пользователя"""
        try:
            user = User(**user_data.model_dump())
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info(f"User created: {user.telegram_id}")
            return user
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def get_user_by_telegram_id(
        session: AsyncSession, telegram_id: int
    ) -> Optional[User]:
        """Получение пользователя по Telegram ID"""
        try:
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            return user
        except Exception as e:
            logger.error(f"Error getting user by telegram_id {telegram_id}: {e}")
            raise

    @staticmethod
    async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
        """Получение пользователя по ID"""
        try:
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            return user
        except Exception as e:
            logger.error(f"Error getting user by id {user_id}: {e}")
            raise

    @staticmethod
    async def get_user_with_choices(
        session: AsyncSession, telegram_id: int
    ) -> Optional[User]:
        """Получение пользователя с его выборами пива"""
        try:
            stmt = (
                select(User)
                .options(selectinload(User.choices))
                .where(User.telegram_id == telegram_id)
            )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            return user
        except Exception as e:
            logger.error(f"Error getting user with choices {telegram_id}: {e}")
            raise

    @staticmethod
    async def update_user(
        session: AsyncSession, telegram_id: int, user_data: UserUpdate
    ) -> Optional[User]:
        """Обновление данных пользователя"""
        try:
            update_data = {
                k: v for k, v in user_data.model_dump().items() if v is not None
            }
            if not update_data:
                return await UserRepository.get_user_by_telegram_id(
                    session, telegram_id
                )

            stmt = (
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(**update_data)
            )
            await session.execute(stmt)
            await session.commit()

            return await UserRepository.get_user_by_telegram_id(session, telegram_id)
        except Exception as e:
            logger.error(f"Error updating user {telegram_id}: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def get_all_users(
        session: AsyncSession, offset: int = 0, limit: int = 100
    ) -> List[User]:
        """Получение всех пользователей с пагинацией"""
        try:
            stmt = (
                select(User)
                .offset(offset)
                .limit(limit)
                .order_by(User.created_at.desc())
            )
            result = await session.execute(stmt)
            users = result.scalars().all()
            return list(users)
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            raise

    @staticmethod
    async def delete_user(session: AsyncSession, telegram_id: int) -> bool:
        """Удаление пользователя"""
        try:
            stmt = delete(User).where(User.telegram_id == telegram_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting user {telegram_id}: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def user_exists(session: AsyncSession, telegram_id: int) -> bool:
        """Проверка существования пользователя"""
        try:
            user = await UserRepository.get_user_by_telegram_id(session, telegram_id)
            return user is not None
        except Exception as e:
            logger.error(f"Error checking user exists {telegram_id}: {e}")
            raise
