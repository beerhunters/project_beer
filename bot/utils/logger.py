import logging
import os
import pendulum
import traceback


def setup_logger(
    name: str, log_file: str = os.getenv("LOG_FILE", "bot.log")
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)  # Capture INFO and above
    logger.handlers = []  # Clear existing handlers

    # Custom formatter with traceback and timezone
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

    # File handler: WARNING and ERROR only
    log_directory = "logs"
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)
    file_handler = logging.FileHandler(os.path.join(log_directory, log_file))
    file_handler.setLevel(logging.WARNING)  # Only WARNING and ERROR
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Stream handler: INFO and above, disabled in production if CONSOLE_LOGGING=false
    console_logging = os.getenv("CONSOLE_LOGGING", "true").lower() == "true"
    if console_logging:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)  # INFO and above
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    return logger
