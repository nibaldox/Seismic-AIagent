"""Logging utilities — structured JSON logging + rotating file handler."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

try:
    from pythonjsonlogger import jsonlogger
    _HAS_JSONLOGGER = True
except ImportError:
    _HAS_JSONLOGGER = False

try:
    from logging.handlers import RotatingFileHandler
    _HAS_ROTATING = True
except ImportError:
    _HAS_ROTATING = logging.handlers.RotatingFileHandler if hasattr(logging, 'handlers') else None

LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
LOG_LEVEL = os.getenv("AGNO_LOG_LEVEL", "INFO").upper()
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", "10_000_000"))  # 10 MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))


class _JsonFormatter(jsonlogger.JsonFormatter if _HAS_JSONLOGGER else logging.Formatter):
    """JSON log formatter with trace/span context support."""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["timestamp"] = record.asctime
        # Remove default fields that pythonjsonlogger already includes
        for field in ("asctime", "levelname", "name", "message"):
            log_record.pop(field, None)


def _make_text_formatter() -> logging.Formatter:
    return logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def setup_logger(
    name: Optional[str] = None,
    enable_json: bool = False,
    log_dir: Path = LOG_DIR,
    level: str = LOG_LEVEL,
    log_to_file: bool = True,
) -> logging.Logger:
    """Configure and return a logger with console (+ optional file) handler.

    Args:
        name: Logger name (default: "seismo_analyzer")
        enable_json: Emit JSON-structured logs to file (default: True in production)
        log_dir: Directory for rotating log files
        level: Log level (INFO, DEBUG, etc.)
        log_to_file: Also write to rotating log file in log_dir
    """
    logger = logging.getLogger(name or "seismo_analyzer")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if logger.handlers:
        return logger  # already configured

    # Console handler — always plain text
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(getattr(logging, level.upper(), logging.INFO))
    ch.setFormatter(_make_text_formatter())
    logger.addHandler(ch)

    if log_to_file and log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "app.log"

        file_handler: logging.Handler
        if _HAS_ROTATING and _HAS_JSONLOGGER:
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=LOG_MAX_BYTES,
                backupCount=LOG_BACKUP_COUNT,
            )
            file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
            fmt = _JsonFormatter(
                fmt="%(asctime)s %(level)s %(name)s %(message)s",
                rename_fields={"levelname": "level", "asctime": "timestamp"},
            )
            file_handler.setFormatter(fmt)
        else:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
            file_handler.setFormatter(_make_text_formatter())

        logger.addHandler(file_handler)

    logger.propagate = False
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get an existing logger or create a new one with defaults."""
    logger = logging.getLogger(name or "seismo_analyzer")
    if not logger.handlers:
        return setup_logger(name)
    return logger


def log_request(logger: logging.Logger, path: str, method: str,
                trace_id: str, latency_ms: float, status_code: int) -> None:
    """Structured request log entry."""
    extra = {
        "trace_id": trace_id,
        "path": path,
        "method": method,
        "latency_ms": round(latency_ms, 2),
        "status_code": status_code,
    }
    if status_code >= 500:
        logger.error("request_error", extra=extra)
    elif status_code >= 400:
        logger.warning("request_client_error", extra=extra)
    else:
        logger.info("request", extra=extra)