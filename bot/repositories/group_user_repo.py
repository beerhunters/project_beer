import logging
from typing import List, Optional, Dict
from sqlalchemy import select, insert, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from bot.core.models import Group, GroupUser, User, HeroSelection
from bot.utils.logger import setup_logger

logger = setup_logger(__name__)


class GroupUserRepository:
    @staticmethod
    async def get_group_by_chat_id(
        session: AsyncSession, chat_id: int
    ) -> Optional[Group]:
        stmt = select(Group).where(Group.chat_id == chat_id)
        result = await session.execute(stmt)
        group = result.scalar_one_or_none()
        return group

    @staticmethod
    async def add_group(session: AsyncSession, chat_id: int, name: str) -> Group:
        stmt = insert(Group).values(chat_id=chat_id, name=name).returning(Group)
        result = await session.execute(stmt)
        group = result.scalar_one()
        await session.commit()
        return group

    @staticmethod
    async def get_user_by_telegram_id(
        session: AsyncSession, telegram_id: int
    ) -> Optional[User]:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        return user

    @staticmethod
    async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        return user

    @staticmethod
    async def register_candidate(
        session: AsyncSession,
        chat_id: int,
        user_id: int,
        telegram_id: int,
        username: str,
        name: str,
    ) -> bool:
        group = await GroupUserRepository.get_group_by_chat_id(session, chat_id)
        if not group:
            group = await GroupUserRepository.add_group(session, chat_id, name)
        user = await GroupUserRepository.get_user_by_telegram_id(session, telegram_id)
        if not user:
            return False
        stmt = select(GroupUser).where(
            and_(GroupUser.group_id == group.id, GroupUser.user_id == user.id)
        )
        result = await session.execute(stmt)
        if not result.scalar_one_or_none():
            stmt = insert(GroupUser).values(group_id=group.id, user_id=user.id)
            await session.execute(stmt)
            await session.commit()
            return True
        return False

    @staticmethod
    async def get_hero_of_the_day(
        session: AsyncSession, group_id: int, date
    ) -> Optional[HeroSelection]:
        stmt = select(HeroSelection).where(
            and_(
                HeroSelection.group_id == group_id, HeroSelection.selection_date == date
            )
        )
        result = await session.execute(stmt)
        hero = result.scalar_one_or_none()
        return hero

    @staticmethod
    async def select_hero_of_the_day(session: AsyncSession, group_id: int, today):
        group_users = await GroupUserRepository.get_users_in_group(session, group_id)
        if not group_users:
            return None
        weights = []
        for gu in group_users:
            stmt = (
                select(HeroSelection.selection_date)
                .where(
                    and_(
                        HeroSelection.group_id == group_id,
                        HeroSelection.user_id == gu.user_id,
                    )
                )
                .order_by(HeroSelection.selection_date.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            last_selection_date = result.scalar_one_or_none()
            weight = 100
            if last_selection_date:
                days_since_last = (today - last_selection_date).days
                weight = min(100, days_since_last * 10)
            weights.append(weight)
        import random

        selected_user = random.choices(group_users, weights=weights, k=1)[0]
        hero_selection = HeroSelection(
            group_id=group_id, user_id=selected_user.user_id, selection_date=today
        )
        session.add(hero_selection)
        await session.commit()
        return hero_selection

    @staticmethod
    async def get_users_in_group(
        session: AsyncSession, group_id: int
    ) -> List[GroupUser]:
        stmt = select(GroupUser).where(GroupUser.group_id == group_id)
        result = await session.execute(stmt)
        group_users = result.scalars().all()
        return group_users

    @staticmethod
    async def get_hero_top(session: AsyncSession, group_id: int) -> List[Dict]:
        stmt = (
            select(
                User.username,
                User.name,
                func.count(HeroSelection.id).label("hero_count"),
            )
            .join(HeroSelection, HeroSelection.user_id == User.id)
            .where(HeroSelection.group_id == group_id)
            .group_by(User.id, User.username, User.name)
            .order_by(func.count(HeroSelection.id).desc())
            .limit(10)
        )
        result = await session.execute(stmt)
        top_heroes = [
            {"username": row.username, "name": row.name, "hero_count": row.hero_count}
            for row in result
        ]
        return top_heroes
