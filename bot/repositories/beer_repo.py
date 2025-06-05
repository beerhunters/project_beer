# bot/repositories/beer_repo.py
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload
from bot.core.models import BeerChoice, User, BeerTypeEnum
from bot.core.schemas import BeerChoiceCreate, BeerChoiceResponse

logger = logging.getLogger(__name__)


class BeerRepository:

    @staticmethod
    async def create_choice(
        session: AsyncSession, choice_data: BeerChoiceCreate
    ) -> BeerChoice:
        """Создание выбора пива"""
        try:
            choice = BeerChoice(**choice_data.model_dump())
            session.add(choice)
            await session.commit()
            await session.refresh(choice)
            logger.info(
                f"Beer choice created: user_id={choice.user_id}, beer_type={choice.beer_type}"
            )
            return choice
        except Exception as e:
            logger.error(f"Error creating beer choice: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def get_user_choices(
        session: AsyncSession, user_id: int, offset: int = 0, limit: int = 50
    ) -> List[BeerChoice]:
        """Получение выборов пива пользователя с пагинацией"""
        try:
            stmt = (
                select(BeerChoice)
                .where(BeerChoice.user_id == user_id)
                .order_by(BeerChoice.selected_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(stmt)
            choices = result.scalars().all()
            return list(choices)
        except Exception as e:
            logger.error(f"Error getting user choices for user_id {user_id}: {e}")
            raise

    @staticmethod
    async def get_latest_user_choice(
        session: AsyncSession, user_id: int
    ) -> Optional[BeerChoice]:
        """Получение последнего выбора пива пользователя"""
        try:
            stmt = (
                select(BeerChoice)
                .where(BeerChoice.user_id == user_id)
                .order_by(BeerChoice.selected_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            choice = result.scalar_one_or_none()
            return choice
        except Exception as e:
            logger.error(f"Error getting latest choice for user_id {user_id}: {e}")
            raise

    @staticmethod
    async def get_beer_stats(session: AsyncSession) -> dict:
        """Получение статистики по типам пива"""
        try:
            stmt = select(
                BeerChoice.beer_type, func.count(BeerChoice.id).label("count")
            ).group_by(BeerChoice.beer_type)
            result = await session.execute(stmt)
            stats = {}
            for row in result:
                stats[row.beer_type.value] = row.count
            return stats
        except Exception as e:
            logger.error(f"Error getting beer stats: {e}")
            raise

    @staticmethod
    async def get_user_beer_stats(session: AsyncSession, user_id: int) -> dict:
        """Получение статистики по типам пива для конкретного пользователя"""
        try:
            stmt = (
                select(BeerChoice.beer_type, func.count(BeerChoice.id).label("count"))
                .where(BeerChoice.user_id == user_id)
                .group_by(BeerChoice.beer_type)
            )
            result = await session.execute(stmt)
            stats = {}
            for row in result:
                stats[row.beer_type.value] = row.count
            return stats
        except Exception as e:
            logger.error(f"Error getting beer stats for user_id {user_id}: {e}")
            raise

    @staticmethod
    async def get_all_choices(
        session: AsyncSession, offset: int = 0, limit: int = 100
    ) -> List[BeerChoice]:
        """Получение всех выборов с пагинацией"""
        try:
            stmt = (
                select(BeerChoice)
                .options(selectinload(BeerChoice.user))
                .order_by(BeerChoice.selected_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(stmt)
            choices = result.scalars().all()
            return list(choices)
        except Exception as e:
            logger.error(f"Error getting all choices: {e}")
            raise

    @staticmethod
    async def delete_user_choices(session: AsyncSession, user_id: int) -> int:
        """Удаление всех выборов пользователя"""
        try:
            stmt = delete(BeerChoice).where(BeerChoice.user_id == user_id)
            result = await session.execute(stmt)
            await session.commit()
            deleted_count = result.rowcount
            logger.info(f"Deleted {deleted_count} choices for user_id {user_id}")
            return deleted_count
        except Exception as e:
            logger.error(f"Error deleting choices for user_id {user_id}: {e}")
            await session.rollback()
            raise
