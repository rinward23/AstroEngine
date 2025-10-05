"""Utilities for strict UTC datetime validation across API payloads."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Annotated

from pydantic import PlainValidator, TypeAdapter, ValidationError


_DATETIME_ADAPTER = TypeAdapter(datetime)


def ensure_utc_datetime(value: Any) -> datetime:
    """Parse *value* and return a timezone-aware UTC :class:`datetime`.

    Accepts ``datetime`` instances or RFC3339 / ISO-8601 strings. Values must
    carry explicit timezone information; naive datetimes are rejected to avoid
    ambiguous interpretations around daylight saving transitions. Strings that
    cannot be parsed, including representations of leap seconds (``23:59:60``),
    raise :class:`ValueError`.
    """

    if isinstance(value, dict):
        # Support legacy payloads that wrap the timestamp in nested objects.
        for key in ("ts", "timestamp", "datetime", "utc"):
            if key in value:
                return ensure_utc_datetime(value[key])
        raise TypeError("Expected datetime or RFC3339 string")

    try:
        dt = _DATETIME_ADAPTER.validate_python(value)
    except ValidationError as exc:
        raise ValueError("Invalid RFC3339 datetime string") from exc

    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError("Datetime must include timezone information")

    return dt.astimezone(UTC)


UtcDateTime = Annotated[datetime, PlainValidator(ensure_utc_datetime)]


__all__ = ["UtcDateTime", "ensure_utc_datetime"]
