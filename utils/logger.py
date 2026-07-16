"""
utils/logger.py
================
Centralized logging configuration with rotating file handler.

Import `get_logger(__name__)` anywhere in the codebase to get a
correctly configured logger instance.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from config import Config

_LOG_DIR = "logs"
_LOG_FILE = os.path.join(_LOG_DIR, "app.log")
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB per log file
_BACKUP_COUNT = 5

_configured = False


def _configure_root_logger() -> None:
    """Configure the root logger once, with console + rotating file handlers."""
    global _configured
    if _configured:
        return

    os.makedirs(_LOG_DIR, exist_ok=True)

    level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        _LOG_FILE, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT
    )
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger instance for the given module name."""
    _configure_root_logger()
    return logging.getLogger(name)
