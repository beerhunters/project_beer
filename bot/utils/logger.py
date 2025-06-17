import logging
import os
import pendulum
import traceback
from typing import Optional


class CustomFormatter(logging.Formatter):
    """Custom formatter with colorized console output and detailed error info"""

    grey = "\x1b[38;21m"
    green = "\x1b[32;1m"
    yellow = "\x1b[33;1m"
    red = "\x1b[31;1m"
    bold_red = "\x1b[41m"
    reset = "\x1b[0m"
    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: green + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset,
    }

    def format(self, record):
        if record.exc_info:
            stack = traceback.extract_tb(record.exc_info[2])
            if stack:
                filename = stack[-1].filename
                lineno = stack[-1].lineno
                code_line = stack[-1].line.strip() if stack[-1].line else "???"
                record.msg = (
                    f"{record.msg}\n"
                    f"File: {filename}, Line: {lineno}\n"
                    f"Code: {code_line}\n"
                    f"Traceback:\n{''.join(traceback.format_tb(record.exc_info[2]))}"
                )
        log_fmt = self.FORMATS.get(record.levelno, self.format_str)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S %Z")
        record.levelname = record.levelname.ljust(8)
        return formatter.format(record)


def setup_logger(
    name: str, log_file: str = os.getenv("LOG_FILE", "bot.log")
) -> logging.Logger:
    """Set up a logger with file and optional console handlers"""
    logger = logging.getLogger(name)
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    logger.handlers = []  # Clear existing handlers

    # Create logs directory if it doesn't exist
    log_directory = "logs"
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    # File handler for WARNING and above
    file_handler = logging.FileHandler(
        os.path.join(log_directory, log_file), encoding="utf-8"
    )
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(CustomFormatter())
    logger.addHandler(file_handler)

    # Console handler for the specified log level, if enabled
    console_logging = os.getenv("CONSOLE_LOGGING", "true").lower() == "true"
    if console_logging:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(getattr(logging, log_level, logging.INFO))
        stream_handler.setFormatter(CustomFormatter())
        logger.addHandler(stream_handler)

    logger.propagate = False
    return logger
