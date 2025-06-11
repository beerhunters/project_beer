import asyncio
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from bot.core.database import get_async_session
from bot.repositories.event_repo import EventRepository
from bot.repositories.beer_repo import BeerRepository
from bot.repositories.event_participant_repo import EventParticipantRepository
from bot.utils.logger import setup_logger
from aiogram import Bot
from bot.core.models import Event
from datetime import datetime, timedelta, date
import pendulum
import os

logger = setup_logger(__name__)
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "267863612"))


async def count_beer_choices(
    session: AsyncSession, event: Event, today: date
) -> tuple[int, dict[str, int]]:
    try:
        event_start = pendulum.datetime(
            year=today.year,
            month=today.month,
            day=today.day,
            hour=event.event_time.hour,
            minute=event.event_time.minute,  # Fixed: Use .minute to extract integer
            tz="Europe/Moscow",
        )
        window_start = event_start.subtract(minutes=30)
        logger.debug(
            f"Counting beer choices for event {event.id}: window_start={window_start}, event_start={event_start}"
        )
        beer_choices = await BeerRepository.get_choices_for_event(
            session, event, window_start, event_start
        )
        # Log choices for debugging
        logger.debug(f"Found {len(beer_choices)} beer choices for event {event.id}")
        # Count unique users to get participant count
        participant_count = len(set(choice.user_id for choice in beer_choices))
        beer_counts = {}
        valid_options = (
            [event.beer_option_1, event.beer_option_2]
            if event.has_beer_choice and event.beer_option_1 and event.beer_option_2
            else [event.beer_option_1 or "Лагер"]
        )
        valid_options = [opt for opt in valid_options if opt]
        for option in valid_options:
            beer_counts[option] = sum(
                1 for choice in beer_choices if choice.beer_choice == option
            )
        return participant_count, beer_counts
    except Exception as e:
        logger.error(
            f"Error counting beer choices for event {event.id}: {e}", exc_info=True
        )
        raise


async def send_bartender_notification(
    bot: Bot, event: Event, participant_count: int, beer_counts: dict[str, int]
):
    try:
        message_text = (
            f"🍺 Заказы на событие '{event.name}' "
            f"({event.event_date.strftime('%d.%m.%Y')} @ {event.event_time.strftime('%H:%M')}):\n"
        )
        message_text += f"👥 Участников: {participant_count}\n"
        if participant_count == 0:
            message_text += "🍻 Нет заказов."
        else:
            for beer, count in beer_counts.items():
                message_text += f"🍻 {beer}: {count}\n"
        await bot.send_message(chat_id=ADMIN_TELEGRAM_ID, text=message_text)
        logger.info(
            f"Bartender notification sent for event {event.id}: {participant_count} participants"
        )
    except Exception as e:
        logger.error(
            f"Error sending bartender notification for event {event.id}: {e}",
            exc_info=True,
        )
        raise


async def process_event_window(bot: Bot, event: Event, today: pendulum.Date):
    try:
        async for session in get_async_session():
            participant_record = (
                await EventParticipantRepository.get_participant_record(
                    session, event.id
                )
            )
            if participant_record:
                logger.debug(f"Event {event.id} already processed, skipping")
                return
            participant_count, beer_counts = await count_beer_choices(
                session, event, today
            )
            await send_bartender_notification(
                bot, event, participant_count, beer_counts
            )
            await EventParticipantRepository.create_participant_record(
                session, event.id, participant_count
            )
            logger.info(f"Processed event {event.id}: {participant_count} participants")
    except Exception as e:
        logger.error(
            f"Error processing event window for event {event.id}: {e}", exc_info=True
        )
        raise


async def check_event_windows(bot: Bot):
    while True:
        try:
            today = pendulum.now("Europe/Moscow").date()
            current_time = pendulum.now("Europe/Moscow").time()
            current_dt = pendulum.datetime(
                year=today.year,
                month=today.month,
                day=today.day,
                hour=current_time.hour,
                minute=current_time.minute,
                second=current_time.second,
                tz="Europe/Moscow",
            )
            async for session in get_async_session():
                events = await EventRepository.get_upcoming_events_by_date(
                    session, today, limit=100
                )
                logger.debug(
                    f"Found {len(events)} events for {today}: {[e.id for e in events]}"
                )
                for event in sorted(events, key=lambda e: e.event_time):
                    event_start = pendulum.datetime(
                        year=today.year,
                        month=today.month,
                        day=today.day,
                        hour=event.event_time.hour,
                        minute=event.event_time.minute,
                        tz="Europe/Moscow",
                    )
                    # Trigger only at or after event_time, within 10 seconds
                    if event_start <= current_dt < event_start.add(seconds=10):
                        logger.debug(
                            f"Processing event {event.id}: current_dt={current_dt}, event_start={event_start}"
                        )
                        await process_event_window(bot, event, today)
                    else:
                        logger.debug(
                            f"Skipping event {event.id}: current_dt={current_dt}, event_start={event_start}"
                        )
        except Exception as e:
            logger.error(f"Error in check_event_windows: {e}", exc_info=True)
        await asyncio.sleep(30)  # Check every 30 seconds


def start_background_tasks(bot: Bot):
    asyncio.create_task(check_event_windows(bot))
    logger.info("Background tasks started")
