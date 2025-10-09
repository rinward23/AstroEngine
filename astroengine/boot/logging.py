"""Logging helpers for AstroEngine services and CLIs."""

from __future__ import annotations

import logging
import os
from typing import Any

__all__ = ["configure_logging"]

_DEFAULT_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
_DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"


def _coerce_level(value: str | int | None) -> int:
    """Return a logging level derived from ``value``.

    The ``LOG_LEVEL`` environment variable supports either the standard
    ``logging`` level names (case insensitive) or a numeric level. Invalid
    inputs fall back to :data:`logging.INFO` to keep output predictable.
    """

    if value is None:
        return logging.INFO

    if isinstance(value, int):
        return value

    candidate = value.strip()
    if not candidate:
        return logging.INFO

    if candidate.isdigit():
        return int(candidate)

    resolved = logging.getLevelName(candidate.upper())
    if isinstance(resolved, int):
        return resolved

    return logging.INFO


def configure_logging(*, level: str | int | None = None, **kwargs: Any) -> int:
    """Configure ``logging`` for AstroEngine entry points.

    Parameters
    ----------
    level:
        Optional log level override. When omitted the ``LOG_LEVEL``
        environment variable is consulted. ``kwargs`` are forwarded to
        :func:`logging.basicConfig`, allowing callers to customize handlers
        when needed.

    Returns
    -------
    int
        The effective logging level applied to the root logger.
    """

    env_level: str | int | None
    if level is None:
        env_level = os.environ.get("LOG_LEVEL")
    else:
        env_level = level

    effective_level = _coerce_level(env_level)

    logging.basicConfig(
        level=effective_level,
        format=kwargs.pop("format", _DEFAULT_FORMAT),
        datefmt=kwargs.pop("datefmt", _DEFAULT_DATEFMT),
        force=kwargs.pop("force", True),
        **kwargs,
    )

    return effective_level
