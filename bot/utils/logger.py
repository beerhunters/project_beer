import logging
import os
import pendulum
import traceback


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

    class CustomFormatter(logging.Formatter):
        def format(self, record):
            if record.exc_info:
                stack = traceback.extract_tb(record.exc_info[2])
                if stack:
                    filename = stack[-1].filename
                    lineno = stack[-1].lineno
                    record.msg = f"{record.msg} (file: {filename}, line: {lineno})"
            return super().format(record)

    formatter = CustomFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %Z",
    )
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    logger.handlers = []
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    file_handler.setFormatter(
        CustomFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S %Z",
            defaults={"tz": pendulum.timezone("Europe/Moscow")},
        )
    )
    stream_handler.setFormatter(
        CustomFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S %Z",
            defaults={"tz": pendulum.timezone("Europe/Moscow")},
        )
    )
    return logger
