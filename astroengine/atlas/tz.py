
"""Timezone lookup and conversion helpers for atlas workflows."""


from __future__ import annotations

from datetime import datetime, timedelta, timezone

import importlib
import importlib.util
from typing import Literal, NoReturn
from zoneinfo import ZoneInfo

_timezonefinder_spec = importlib.util.find_spec("timezonefinder")

if _timezonefinder_spec is not None:  # pragma: no cover - exercised via integration tests
    TimezoneFinder = importlib.import_module("timezonefinder").TimezoneFinder
else:
    class TimezoneFinder:  # type: ignore[override]
        """Fallback that surfaces a helpful error when timezonefinder is missing."""

        def _raise(self) -> NoReturn:
            raise ModuleNotFoundError(
                "timezonefinder is required for timezone lookups. Install the "
                "'timezonefinder' extra to enable astroengine.atlas.tz helpers."
            )

        def timezone_at(self, *, lng: float, lat: float) -> str | None:  # noqa: D401
            self._raise()

        def closest_timezone_at(self, *, lng: float, lat: float) -> str | None:  # noqa: D401
            self._raise()


Policy = Literal["earliest", "latest", "shift_forward", "raise"]

__all__ = [
    "Policy",

    "from_utc",
    "is_ambiguous",
    "is_nonexistent",
    "to_utc",
    "tzid_for",

]

_tf = TimezoneFinder()



def tzid_for(lat: float, lon: float) -> str:
    """Return the best guess timezone identifier for the provided coordinates."""

    tzid = _tf.timezone_at(lng=lon, lat=lat)
    if tzid:
        return tzid
    tzid = _tf.closest_timezone_at(lng=lon, lat=lat)
    if tzid:
        return tzid
    raise ValueError("Unable to resolve timezone for coordinates")


def _attach(local_naive: datetime, zone: ZoneInfo, fold: int) -> datetime:
    if local_naive.tzinfo is not None:
        raise ValueError("local_naive must be timezone-naive")
    return local_naive.replace(tzinfo=zone, fold=fold)


def is_ambiguous(local_naive: datetime, tzid: str) -> bool:
    """Return ``True`` when the local time is ambiguous (DST fall-back)."""

    zone = ZoneInfo(tzid)
    utc0 = _attach(local_naive, zone, 0).astimezone(timezone.utc)
    utc1 = _attach(local_naive, zone, 1).astimezone(timezone.utc)
    return utc0 != utc1 and utc0 < utc1


def is_nonexistent(local_naive: datetime, tzid: str) -> bool:
    """Return ``True`` when the local time is skipped (DST spring-forward)."""

    zone = ZoneInfo(tzid)
    utc0 = _attach(local_naive, zone, 0).astimezone(timezone.utc)
    utc1 = _attach(local_naive, zone, 1).astimezone(timezone.utc)
    return utc0 != utc1 and utc0 > utc1



def _dst_gap(local_naive: datetime, zone: ZoneInfo) -> timedelta:
    before = (local_naive - timedelta(hours=1)).replace(tzinfo=zone)
    after = (local_naive + timedelta(hours=1)).replace(tzinfo=zone)

    before_offset = before.utcoffset() or timedelta(0)
    after_offset = after.utcoffset() or timedelta(0)
    gap = after_offset - before_offset
    return gap if gap >= timedelta(0) else -gap



def to_utc(
    local_naive: datetime,
    lat: float,
    lon: float,
    *,
    policy: Policy = "earliest",
) -> datetime:

    """Convert a naive local timestamp into a timezone-aware UTC datetime."""

    if policy not in {"earliest", "latest", "shift_forward", "raise"}:
        raise ValueError(f"Unsupported policy: {policy}")
    if local_naive.tzinfo is not None:
        raise ValueError("local_naive must be timezone-naive")
    tzid = tzid_for(lat, lon)
    zone = ZoneInfo(tzid)

    if is_ambiguous(local_naive, tzid):
        if policy == "raise":
            raise ValueError("Ambiguous local time due to DST transition")
        fold = 0 if policy in {"earliest", "shift_forward"} else 1
        return _attach(local_naive, zone, fold).astimezone(timezone.utc)

    if is_nonexistent(local_naive, tzid):
        if policy == "raise":
            raise ValueError("Nonexistent local time due to DST transition")

        if policy == "shift_forward":
            gap = _dst_gap(local_naive, zone)
            adjusted = local_naive + gap
            return adjusted.replace(tzinfo=zone).astimezone(timezone.utc)

        return _attach(local_naive, zone, 0).astimezone(timezone.utc)


    return local_naive.replace(tzinfo=zone).astimezone(timezone.utc)


def from_utc(utc_dt: datetime, lat: float, lon: float) -> datetime:

    """Convert a UTC datetime into the local timezone for the coordinates."""

    tzid = tzid_for(lat, lon)
    if utc_dt.tzinfo is None:
        aware = utc_dt.replace(tzinfo=timezone.utc)
    else:
        aware = utc_dt.astimezone(timezone.utc)
    return aware.astimezone(ZoneInfo(tzid))

