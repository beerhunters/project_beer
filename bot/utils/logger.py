import logging
import os
import pendulum


def setup_logger(
    name: str, log_file: str = os.getenv("LOG_FILE", "bot.log")
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.ERROR)

    log_directory = "logs"
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    file_handler = logging.FileHandler(os.path.join(log_directory, log_file))
    stream_handler = logging.StreamHandler()

    # Use UTC+3 (Europe/Moscow) for log timestamps
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %Z",
    )
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)

    logger.handlers = []
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    # Ensure logger uses UTC+3 timezone
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S %Z",
            defaults={"tz": pendulum.timezone("Europe/Moscow")},
        )
    )
    stream_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S %Z",
            defaults={"tz": pendulum.timezone("Europe/Moscow")},
        )
    )

    return logger
