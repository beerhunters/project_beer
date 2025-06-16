from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession
from bot.core.database import get_async_session
from bot.repositories.event_repo import EventRepository
from bot.repositories.beer_repo import BeerRepository
from bot.repositories.event_participant_repo import EventParticipantRepository
from bot.utils.logger import setup_logger
from aiogram import Bot
from bot.core.models import Event
from datetime import date
import pendulum
import os
from dotenv import load_dotenv

load_dotenv()
logger = setup_logger(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
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


@shared_task
def process_event_notification(event_id: int):
    logger.info(f"Test task for {event_id}")
    bot = None
    try:
        bot = Bot(token=BOT_TOKEN)

        async def run():
            async for session in get_async_session():
                event = await EventRepository.get_event_by_id(session, event_id)
                if not event:
                    logger.warning(f"Event {event_id} not found in database, skipping")
                    return
                participant_record = (
                    await EventParticipantRepository.get_participant_record(
                        session, event_id
                    )
                )
                if participant_record:
                    logger.debug(f"Event {event_id} already processed, skipping")
                    return
                participant_count, beer_counts = await count_beer_choices(
                    session, event, event.event_date
                )
                await send_bartender_notification(
                    bot, event, participant_count, beer_counts
                )
                await EventParticipantRepository.create_participant_record(
                    session, event_id, participant_count
                )
                logger.info(
                    f"Processed event {event_id}: {participant_count} participants"
                )

        import asyncio

        asyncio.run(run())
    except Exception as e:
        logger.error(
            f"Error processing event notification for event {event_id}: {e}",
            exc_info=True,
        )
    finally:
        if bot:
            import asyncio

            asyncio.run(bot.session.close())
