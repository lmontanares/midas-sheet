"""
Logging system configuration using Loguru.
"""

import sys
from pathlib import Path

from loguru import logger


def setup_logging(log_file: str | Path | None = None, level: str = "INFO") -> None:
    """
    Configures logging system with Loguru for centralized error tracking.

    Args:
        log_file: Path to log file (optional)
        level: Logging level (default INFO)
    """
    logger.remove()
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

    logger.add(sys.stdout, format=log_format, level=level, colorize=True)

    if log_file:
        if isinstance(log_file, str):
            log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_file,
            format=log_format,
            level=level,
            rotation="100 MB",
            retention="1 month",
            compression="zip",
        )

        logger.info(f"Logging configured. Saving logs to: {log_file}")
    else:
        logger.info("Logging configured. Console output only.")


# Export logger for use throughout the project
__all__ = ["logger", "setup_logging"]
