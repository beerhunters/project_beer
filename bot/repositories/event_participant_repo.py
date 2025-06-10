from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from bot.core.models import EventParticipant
from bot.utils.logger import setup_logger

logger = setup_logger(__name__)


class EventParticipantRepository:
    @staticmethod
    async def create_participant_record(
        session: AsyncSession, event_id: int, participant_count: int
    ) -> EventParticipant:
        try:
            stmt = (
                insert(EventParticipant)
                .values(event_id=event_id, participant_count=participant_count)
                .returning(EventParticipant)
            )
            result = await session.execute(stmt)
            record = result.scalar_one()
            await session.commit()
            return record
        except Exception as e:
            logger.error(f"Error creating participant record for event {event_id}: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def get_participant_record(
        session: AsyncSession, event_id: int
    ) -> Optional[EventParticipant]:
        try:
            stmt = select(EventParticipant).where(EventParticipant.event_id == event_id)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            return record
        except Exception as e:
            logger.error(f"Error getting participant record for event {event_id}: {e}")
            raise
