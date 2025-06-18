from random import choice
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, delete
from sqlalchemy.orm import selectinload
from bot.core.models import Group, GroupUser, HeroSelection, User
from bot.utils.logger import setup_logger
from datetime import date
import pendulum

logger = setup_logger(__name__)


class GroupUserRepository:
    @staticmethod
    async def get_group_by_chat_id(
        session: AsyncSession, chat_id: int
    ) -> Optional[Group]:
        try:
            stmt = select(Group).where(Group.chat_id == chat_id)
            result = await session.execute(stmt)
            group = result.scalar_one_or_none()
            return group
        except Exception as e:
            logger.error(f"Error getting group by chat_id {chat_id}: {e}")
            raise

    @staticmethod
    async def add_group(session: AsyncSession, chat_id: int, name: str) -> Group:
        try:
            stmt = insert(Group).values(chat_id=chat_id, name=name).returning(Group)
            result = await session.execute(stmt)
            group = result.scalar_one()
            await session.commit()
            return group
        except Exception as e:
            logger.error(f"Error adding group {chat_id}: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def register_candidate(
        session: AsyncSession,
        telegram_id: int,
        chat_id: int,
        name: str,
        username: Optional[str],
    ) -> bool:
        try:
            # Проверяем пользователя
            user = await GroupUserRepository.get_user_by_telegram_id(
                session, telegram_id
            )
            if not user:
                raise ValueError(f"User with telegram_id {telegram_id} not found")

            # Проверяем группу
            group = await GroupUserRepository.get_group_by_chat_id(session, chat_id)
            if not group:
                raise ValueError(f"Group with chat_id {chat_id} not found")

            # Проверяем, не зарегистрирован ли пользователь уже
            stmt = select(GroupUser).where(
                GroupUser.group_id == group.id, GroupUser.user_id == user.id
            )
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                logger.debug(
                    f"User {telegram_id} already registered in group {chat_id}"
                )
                return False

            # Регистрируем пользователя в группе
            stmt = (
                insert(GroupUser)
                .values(group_id=group.id, user_id=user.id)
                .returning(GroupUser)
            )
            result = await session.execute(stmt)
            group_user = result.scalar_one()
            await session.commit()
            logger.info(f"User {telegram_id} registered in group {chat_id}")
            return True
        except Exception as e:
            logger.error(
                f"Error registering user {telegram_id} in group {chat_id}: {e}"
            )
            await session.rollback()
            raise

    @staticmethod
    async def remove_user_from_group(
        session: AsyncSession, telegram_id: int, chat_id: int
    ) -> bool:
        try:
            user = await GroupUserRepository.get_user_by_telegram_id(
                session, telegram_id
            )
            if not user:
                return False
            stmt = select(Group).where(Group.chat_id == chat_id)
            result = await session.execute(stmt)
            group = result.scalar_one_or_none()
            if not group:
                return False
            stmt = delete(GroupUser).where(
                GroupUser.group_id == group.id, GroupUser.user_id == user.id
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount is not None and result.rowcount > 0
        except Exception as e:
            logger.error(f"Error removing user {telegram_id} from group {chat_id}: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def get_users_in_group(
        session: AsyncSession, chat_id: int
    ) -> List[GroupUser]:
        try:
            stmt = select(Group).where(Group.chat_id == chat_id)
            result = await session.execute(stmt)
            group = result.scalar_one_or_none()
            if not group:
                return []
            stmt = (
                select(GroupUser)
                .where(GroupUser.group_id == group.id)
                .options(selectinload(GroupUser.user))
            )
            result = await session.execute(stmt)
            group_users = result.scalars().all()
            return list(group_users)
        except Exception as e:
            logger.error(f"Error getting users in group {chat_id}: {e}")
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
    async def select_hero_of_the_day(
        session: AsyncSession, chat_id: int, selection_date: date
    ) -> Optional[HeroSelection]:
        try:
            # Проверяем группу
            stmt = select(Group).where(Group.chat_id == chat_id)
            result = await session.execute(stmt)
            group = result.scalar_one_or_none()
            if not group:
                logger.warning(f"Group with chat_id {chat_id} not found")
                return None

            # Проверяем, есть ли уже герой
            existing_hero = await GroupUserRepository.get_hero_of_the_day(
                session, chat_id, selection_date
            )
            if existing_hero:
                return existing_hero

            # Получаем пользователей группы
            group_users = await GroupUserRepository.get_users_in_group(session, chat_id)
            if not group_users:
                logger.warning(f"No users registered in group {chat_id}")
                return None

            # Выбираем случайного пользователя
            import random

            random.shuffle(group_users)
            for gu in group_users:
                # Проверяем, не был ли пользователь героем сегодня
                stmt = select(HeroSelection).where(
                    HeroSelection.group_id == group.id,
                    HeroSelection.user_id == gu.user_id,
                    HeroSelection.selection_date == selection_date,
                )
                result = await session.execute(stmt)
                if not result.scalar_one_or_none():
                    hero_selection = HeroSelection(
                        group_id=group.id,
                        user_id=gu.user_id,
                        selection_date=selection_date,
                    )
                    session.add(hero_selection)
                    await session.commit()
                    await session.refresh(hero_selection)
                    logger.info(
                        f"Hero selected: user_id={gu.user_id} for group {chat_id}"
                    )
                    return hero_selection

            logger.warning(
                f"No eligible users found for group {chat_id} on {selection_date}"
            )
            return None
        except Exception as e:
            logger.error(f"Error selecting hero for group {chat_id}: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def get_hero_of_the_day(
        session: AsyncSession, chat_id: int, selection_date: date
    ) -> Optional[HeroSelection]:
        try:
            stmt = select(Group).where(Group.chat_id == chat_id)
            result = await session.execute(stmt)
            group = result.scalar_one_or_none()
            if not group:
                return None
            stmt = select(HeroSelection).where(
                HeroSelection.group_id == group.id,
                HeroSelection.selection_date == selection_date,
            )
            result = await session.execute(stmt)
            hero = result.scalar_one_or_none()
            return hero
        except Exception as e:
            logger.error(f"Error getting hero for group {chat_id}: {e}")
            raise
