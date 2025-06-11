import asyncio
import json
import os
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

logger = setup_logger(__name__)
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "267863612"))
EVENT_TIMERS_FILE = "event_timers.json"


async def count_beer_choices(
    session: AsyncSession, event: Event, today: date
) -> tuple[int, dict[str, int]]:
    try:
        event_start = pendulum.datetime(
            year=today.year,
            month=today.month,
            day=today.day,
            hour=event.event_time.hour,
            minute=event.event_time.minute,
            tz="Europe/Moscow",
        )
        window_start = event_start.subtract(minutes=30)
        logger.debug(
            f"Counting beer choices for event {event.id}: window_start={window_start}, event_start={event_start}"
        )
        beer_choices = await BeerRepository.get_choices_for_event(
            session, event, window_start, event_start
        )
        logger.debug(f"Found {len(beer_choices)} beer choices for event {event.id}")
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


async def process_event_notification(bot: Bot, event: Event):
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
                session, event, event.event_date
            )
            await send_bartender_notification(
                bot, event, participant_count, beer_counts
            )
            await EventParticipantRepository.create_participant_record(
                session, event.id, participant_count
            )
            logger.info(f"Processed event {event.id}: {participant_count} participants")

            # Удаляем событие из файла
            try:
                if os.path.exists(EVENT_TIMERS_FILE):
                    with open(EVENT_TIMERS_FILE, "r") as f:
                        timers = json.load(f)
                    timers = [t for t in timers if t["event_id"] != event.id]
                    with open(EVENT_TIMERS_FILE, "w") as f:
                        json.dump(timers, f, indent=2)
                    logger.info(
                        f"Event {event.id} removed from timers file: {EVENT_TIMERS_FILE}"
                    )
            except Exception as e:
                logger.error(
                    f"Error removing event {event.id} from timers file: {e}",
                    exc_info=True,
                )
    except Exception as e:
        logger.error(
            f"Error processing event notification for event {event.id}: {e}",
            exc_info=True,
        )


async def schedule_bartender_notification(
    bot: Bot, event: Event, event_start: pendulum.DateTime
):
    try:
        now = pendulum.now("Europe/Moscow")
        seconds_until_event = (event_start - now).total_seconds()

        logger.debug(
            f"Scheduling notification for event {event.id}: starts in {seconds_until_event} seconds"
        )

        if seconds_until_event > 0:
            await asyncio.sleep(seconds_until_event)
            logger.info(f"Timer triggered for event {event.id}")
        else:
            logger.info(
                f"Event {event.id} start time has passed, processing immediately"
            )

        async for session in get_async_session():
            event = await EventRepository.get_event_by_id(session, event.id)
            if event:
                await process_event_notification(bot, event)
            else:
                logger.warning(
                    f"Event {event.id} not found in database, skipping notification"
                )
    except Exception as e:
        logger.error(
            f"Error in scheduled notification for event {event.id}: {e}", exc_info=True
        )


async def restore_timers(bot: Bot):
    try:
        if not os.path.exists(EVENT_TIMERS_FILE):
            logger.info(f"No timers file found: {EVENT_TIMERS_FILE}")
            return

        with open(EVENT_TIMERS_FILE, "r") as f:
            timers = json.load(f)

        logger.info(f"Restoring {len(timers)} event timers from file")

        async for session in get_async_session():
            for timer in timers:
                event_id = timer["event_id"]
                event = await EventRepository.get_event_by_id(session, event_id)
                if not event:
                    logger.warning(
                        f"Event {event_id} from timers file not found in database, skipping"
                    )
                    continue

                event_start = pendulum.datetime(
                    year=int(timer["event_date"].split("-")[0]),
                    month=int(timer["event_date"].split("-")[1]),
                    day=int(timer["event_date"].split("-")[2]),
                    hour=int(timer["event_time"].split(":")[0]),
                    minute=int(timer["event_time"].split(":")[1]),
                    second=int(timer["event_time"].split(":")[2]),
                    tz="Europe/Moscow",
                )

                participant_record = (
                    await EventParticipantRepository.get_participant_record(
                        session, event_id
                    )
                )
                if participant_record:
                    logger.debug(
                        f"Event {event_id} already processed, removing from timers"
                    )
                    try:
                        timers = [t for t in timers if t["event_id"] != event_id]
                        with open(EVENT_TIMERS_FILE, "w") as f:
                            json.dump(timers, f, indent=2)
                        logger.info(
                            f"Event {event_id} removed from timers file: {EVENT_TIMERS_FILE}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Error removing event {event_id} from timers file: {e}",
                            exc_info=True,
                        )
                    continue

                asyncio.create_task(
                    schedule_bartender_notification(bot, event, event_start)
                )
                logger.info(
                    f"Restored timer for event {event_id}: starts at {event_start}"
                )
    except Exception as e:
        logger.error(f"Error restoring timers: {e}", exc_info=True)


def start_background_tasks(bot: Bot):
    asyncio.create_task(restore_timers(bot))
    logger.info("Background tasks started")
