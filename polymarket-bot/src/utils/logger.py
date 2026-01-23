"""
Logging configuration.
"""

import logging
import sys
from .config import LOG_LEVEL


def setup_logging() -> logging.Logger:
    """Configure and return the root logger."""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("polymarket_bot")


logger = setup_logging()
