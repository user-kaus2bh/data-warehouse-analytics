"""
logger.py — Structured logging setup using loguru.
All ETL modules import get_logger() from here.
"""

import sys
from pathlib import Path
from loguru import logger as _logger


def get_logger(name: str):
    """Return a loguru logger bound with the module name."""
    _logger.remove()

    # Console handler — human-readable with color
    _logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
               "<cyan>{extra[module]}</cyan> | {message}",
        level="DEBUG",
        colorize=True,
    )

    # File handler — full timestamps, rotation at 5 MB
    log_file = Path(__file__).resolve().parent.parent / "logs" / "etl.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    _logger.add(
        str(log_file),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[module]} | {message}",
        level="DEBUG",
        rotation="5 MB",
        retention="10 days",
        encoding="utf-8",
    )

    return _logger.bind(module=name)
