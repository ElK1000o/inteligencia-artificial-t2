"""
Structured logging configuration for MatEnergy-ML using structlog.

Produces JSON log lines in all environments.  Call ``configure_logging()``
exactly once during application startup (inside the FastAPI lifespan handler).

Usage after configuration:
    from app.core.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("event_name", key="value")
"""
from __future__ import annotations

import logging
import sys

import structlog

from app.core.config import settings

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_log_level(level_str: str) -> int:
    """Convert a string level name to its ``logging`` int constant."""
    level = getattr(logging, level_str.upper(), None)
    if not isinstance(level, int):
        # Fall back to INFO and warn about the bad value
        logging.warning(
            "Unknown LOG_LEVEL %r, defaulting to INFO", level_str
        )
        return logging.INFO
    return level


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def configure_logging() -> None:
    """
    Configure structlog for JSON-structured output.

    Must be called once before any logger is used.  Safe to call multiple
    times (idempotent after the first call due to structlog's internal cache,
    but we reset the cache to pick up any settings changes).

    Processor chain (in order):
      1. merge_contextvars  — propagates per-request context (e.g. request_id)
      2. add_log_level      — adds "level" key
      3. TimeStamper        — adds ISO-8601 "timestamp" key
      4. StackInfoRenderer  — renders stack_info if present
      5. format_exc_info    — renders exc_info as a string
      6. JSONRenderer       — serialises the final event dict to JSON
    """
    log_level = _resolve_log_level(settings.LOG_LEVEL)

    # Configure the standard library root logger so third-party libraries that
    # use stdlib logging also emit structured output at the right level.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    structlog.configure(
        processors=[
            # Merge any context variables bound via structlog.contextvars
            structlog.contextvars.merge_contextvars,
            # Standard processors
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            # Final renderer: always produce machine-readable JSON
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Return a structlog bound logger for *name*.

    This is the standard way to obtain a logger throughout the codebase.
    The returned object is a :class:`structlog.BoundLogger` which supports
    keyword arguments for structured key-value pairs, e.g.:

        logger.info("dataset_uploaded", dataset_id=str(ds.id), rows=1024)

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A structlog BoundLogger instance.
    """
    return structlog.get_logger(name)
