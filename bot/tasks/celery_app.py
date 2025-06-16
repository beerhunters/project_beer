from celery import Celery
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
    include=["bot.tasks.bartender_notification"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=False,
    beat_schedule={},
    beat_dburi=REDIS_URL,
    broker_connection_retry_on_startup=True,
)

logger.debug(f"Registered Celery tasks: {list(app.tasks.keys())}")

if __name__ == "__main__":
    app.start()
