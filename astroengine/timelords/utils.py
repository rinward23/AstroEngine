"""Utility helpers shared across timelord modules."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

__all__ = ["parse_iso", "isoformat", "clamp_end", "timedelta_from_days"]


def parse_iso(value: str) -> datetime:
    """Parse an ISO-8601 string into a timezone-aware ``datetime``."""

    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)
    return dt


def isoformat(moment: datetime) -> str:
    """Return a canonical ISO-8601 string in UTC."""

    return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")


def clamp_end(start: datetime, end: datetime) -> datetime:
    """Ensure ``end`` is strictly after ``start`` by at least one second."""

    if end <= start:
        return start + timedelta(seconds=1)
    return end


def timedelta_from_days(days: float) -> timedelta:
    """Return a :class:`datetime.timedelta` given a floating number of days."""

    return timedelta(seconds=days * 86400.0)
