from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from bot.core.models import Event
from bot.core.schemas import EventCreate
from bot.utils.logger import setup_logger
from datetime import date
import pendulum

logger = setup_logger(__name__)


class EventRepository:
    @staticmethod
    async def create_event(session: AsyncSession, event_data: EventCreate) -> Event:
        try:
            event = Event(**event_data.model_dump())
            session.add(event)
            await session.commit()
            await session.refresh(event)
            return event
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def get_event_by_id(session: AsyncSession, event_id: int) -> Optional[Event]:
        try:
            stmt = select(Event).where(Event.id == event_id)
            result = await session.execute(stmt)
            event = result.scalar_one_or_none()
            return event
        except Exception as e:
            logger.error(f"Error getting event by id {event_id}: {e}")
            raise

    @staticmethod
    async def get_all_events(
        session: AsyncSession, offset: int = 0, limit: int = 100
    ) -> List[Event]:
        try:
            stmt = (
                select(Event)
                .offset(offset)
                .limit(limit)
                .order_by(Event.event_date.desc(), Event.event_time.desc())
            )
            result = await session.execute(stmt)
            events = result.scalars().all()
            return list(events)
        except Exception as e:
            logger.error(f"Error getting all events: {e}")
            raise

    @staticmethod
    async def get_upcoming_events(
        session: AsyncSession, offset: int = 0, limit: int = 100
    ) -> List[Event]:
        try:
            today = pendulum.now("Europe/Moscow").date()
            stmt = (
                select(Event)
                .where(Event.event_date >= today)
                .offset(offset)
                .limit(limit)
                .order_by(Event.event_date.asc(), Event.event_time.asc())
            )
            result = await session.execute(stmt)
            events = result.scalars().all()
            return events
        except Exception as e:
            logger.error(f"Error getting upcoming events: {e}")
            raise

    @staticmethod
    async def get_upcoming_events_by_date(
        session: AsyncSession, date: date, limit: int = 100
    ) -> List[Event]:
        try:
            stmt = (
                select(Event)
                .where(Event.event_date == date)
                .order_by(Event.event_time.asc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            events = result.scalars().all()
            return list(events)
        except Exception as e:
            logger.error(f"Error getting events for date {date}: {e}")
            raise

    @staticmethod
    async def delete_event(session: AsyncSession, event_id: int) -> bool:
        try:
            stmt = delete(Event).where(Event.id == event_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount is not None and result.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting event {event_id}: {e}")
            await session.rollback()
            raise
