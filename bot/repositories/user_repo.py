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
        try:
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            return user
        except Exception as e:
            logger.error(f"Error getting user by id {user_id}: {e}")
            raise

    @staticmethod
    async def get_user_with_choices(  # Этот метод может быть полезен, если нужно сразу и пользователя и его выборы без доп. запросов
        session: AsyncSession, telegram_id: int
    ) -> Optional[User]:
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
        try:
            update_values = user_data.model_dump(
                exclude_unset=True
            )  # exclude_unset=True лучше подходит для частичных обновлений
            if not update_values:
                return await UserRepository.get_user_by_telegram_id(
                    session, telegram_id
                )
            stmt = (
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(**update_values)
                .returning(
                    User
                )  # Можно сразу вернуть обновленного пользователя, если БД поддерживает
            )
            result = await session.execute(stmt)
            await session.commit()
            # Если returning не поддерживается или не используется, нужно снова запросить пользователя
            # В данном случае, проще просто закоммитить и запросить снова, как было
            # updated_user = result.scalar_one_or_none() # если returning(User) используется
            # if updated_user:
            #    await session.refresh(updated_user) # Не обязательно, если данные из returning полные
            # return updated_user
            return await UserRepository.get_user_by_telegram_id(
                session, telegram_id
            )  # Как было
        except Exception as e:
            logger.error(f"Error updating user {telegram_id}: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def get_all_users(
        session: AsyncSession, offset: int = 0, limit: int = 100
    ) -> List[User]:
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
        try:
            stmt = delete(User).where(User.telegram_id == telegram_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount is not None and result.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting user {telegram_id}: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def user_exists(session: AsyncSession, telegram_id: int) -> bool:
        try:
            # Оптимизация: использовать select(func.count()).where(...) вместо полного объекта
            stmt = select(func.count(User.id)).where(User.telegram_id == telegram_id)
            result = await session.execute(stmt)
            count = result.scalar_one()
            return count > 0
        except Exception as e:
            logger.error(f"Error checking user exists {telegram_id}: {e}")
            # В случае ошибки лучше перевыбросить исключение или вернуть False, чтобы вызывающий код мог отреагировать
            raise  # или return False, в зависимости от желаемого поведения
