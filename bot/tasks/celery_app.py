# from celery import Celery
# import os
# from dotenv import load_dotenv
# from bot.utils.logger import setup_logger
#
# load_dotenv()
#
# logger = setup_logger(__name__)
# REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
#
# app = Celery(
#     "bot",
#     broker=REDIS_URL,
#     backend=REDIS_URL,
#     include=["bot.tasks.bartender_notification"],
# )
#
# app.conf.update(
#     task_serializer="json",
#     accept_content=["json"],
#     result_serializer="json",
#     timezone="Europe/Moscow",
#     enable_utc=False,
#     beat_schedule={},
#     beat_dburi=REDIS_URL,
#     broker_connection_retry_on_startup=True,
#     result_expires=3600,  # Expire task results after 1 hour
# )
#
# if __name__ == "__main__":
#     app.start()
from celery import Celery
from celery.schedules import crontab
import os
from dotenv import load_dotenv
from bot.utils.logger import setup_logger

load_dotenv()

logger = setup_logger(__name__)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

app = Celery(
    "bot",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["bot.tasks.bartender_notification", "bot.tasks.hero_notification"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=False,
    beat_schedule={
        "select-hero-every-day": {
            "task": "bot.tasks.hero_notification.process_hero_selection",
            "schedule": crontab(hour=15, minute=15),
        },
    },
    beat_dburi=REDIS_URL,
    broker_connection_retry_on_startup=True,
    result_expires=3600,  # Expire task results after 1 hour
)

if __name__ == "__main__":
    app.start()
