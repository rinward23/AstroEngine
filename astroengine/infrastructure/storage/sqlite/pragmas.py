"""Shared SQLite pragma configuration helpers."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

LOG = logging.getLogger(__name__)

_PRAGMA_STATEMENTS: tuple[str, ...] = (
    "PRAGMA journal_mode=WAL;",
    "PRAGMA synchronous=NORMAL;",
    "PRAGMA cache_size=-40000;",
    "PRAGMA temp_store=MEMORY;",
    "PRAGMA busy_timeout=5000;",
)


def _consume_cursor(cursor: Any) -> None:
    """Exhaust and close the cursor returned by a PRAGMA statement."""

    if cursor is None:
        return
    try:
        cursor.fetchall()
    except Exception as exc:  # pragma: no cover - cursor implementations vary
        LOG.debug("Unable to consume pragma cursor: %s", exc)
    finally:
        try:
            cursor.close()
        except Exception as exc:  # pragma: no cover - cursor implementations vary
            LOG.debug("Unable to close pragma cursor: %s", exc)


def apply_default_pragmas(dbapi_connection: Any) -> None:
    """Apply the project's default SQLite PRAGMA tuning options."""

    execute: Callable[[str], Any] | None = getattr(dbapi_connection, "execute", None)
    if execute is None:
        cursor_factory = getattr(dbapi_connection, "cursor", None)
        if cursor_factory is None:
            return
        cursor = cursor_factory()
        try:
            for statement in _PRAGMA_STATEMENTS:
                cursor.execute(statement)
        finally:
            cursor.close()
        return

    for statement in _PRAGMA_STATEMENTS:
        cursor = execute(statement)
        _consume_cursor(cursor)


__all__ = ["apply_default_pragmas"]
