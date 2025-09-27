"""Logging utilities for the application."""

from __future__ import annotations

import logging
import os
from typing import Optional

_DEFAULT_LOG_LEVEL = os.getenv("AGNO_LOG_LEVEL", "INFO").upper()


def setup_logger(name: Optional[str] = None) -> logging.Logger:
    """Configure and return a logger instance with the project defaults."""

    logger = logging.getLogger(name or "seismo_analyzer")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(_DEFAULT_LOG_LEVEL)
    logger.propagate = False
    return logger
