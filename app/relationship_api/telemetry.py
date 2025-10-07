"""Logging utilities for the relationship API."""

from __future__ import annotations

import logging
import os

_LOGGER_NAME = "relationship_api"


def configure_logging() -> None:
    """Configure structured-ish logging once per process."""

    if getattr(configure_logging, "_configured", False):  # type: ignore[attr-defined]
        return
    level_name = os.getenv("RELATIONSHIP_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"
    )
    handler.setFormatter(formatter)
    root = logging.getLogger(_LOGGER_NAME)
    root.setLevel(level)
    root.propagate = False
    if not root.handlers:
        root.addHandler(handler)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    configure_logging._configured = True  # type: ignore[attr-defined]


def get_logger() -> logging.Logger:
    return logging.getLogger(_LOGGER_NAME)


__all__ = ["configure_logging", "get_logger"]
