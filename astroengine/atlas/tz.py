"""Timezone resolution utilities for atlas workflows."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Literal

from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo

Policy = Literal["earliest", "latest", "shift_forward", "raise"]

__all__ = [
    "Policy",
    "tzid_for",
    "to_utc",
    "from_utc",
    "is_ambiguous",
    "is_nonexistent",
]

_tf = TimezoneFinder()


@lru_cache(maxsize=None)
def _get_zoneinfo(tzid: str) -> ZoneInfo:
    """Cache `ZoneInfo` instances for repeat lookups."""

    return ZoneInfo(tzid)


def tzid_for(lat: float, lon: float) -> str:
    """Return the canonical timezone identifier for the provided coordinates."""

    tz = _tf.timezone_at(lng=lon, lat=lat)
    if tz:
        return tz
    tz = _tf.closest_timezone_at(lng=lon, lat=lat)
    if tz:
        return tz
    raise ValueError("Unable to resolve timezone for coordinates")


def _attach(local_naive: datetime, tzid: str, fold: int) -> datetime:
    if local_naive.tzinfo is not None:
        raise ValueError("local_naive must be naive")
    return local_naive.replace(tzinfo=_get_zoneinfo(tzid), fold=fold)


def is_ambiguous(local_naive: datetime, tzid: str) -> bool:
    """Return ``True`` when ``local_naive`` occurs twice due to a DST fall-back."""

    aware0 = _attach(local_naive, tzid, 0)
    aware1 = _attach(local_naive, tzid, 1)
    offset0 = aware0.utcoffset()
    offset1 = aware1.utcoffset()
    return offset0 is not None and offset1 is not None and offset0 != offset1


def is_nonexistent(local_naive: datetime, tzid: str) -> bool:
    """Return ``True`` when ``local_naive`` falls inside a DST spring-forward gap."""

    zone = _get_zoneinfo(tzid)
    aware0 = _attach(local_naive, tzid, 0)
    aware1 = _attach(local_naive, tzid, 1)
    cand0 = aware0.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None)
    cand1 = aware1.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None)
    return cand0 != local_naive and cand1 != local_naive


def _dst_gap(local_naive: datetime, zone: ZoneInfo) -> timedelta:
    before = (local_naive - timedelta(hours=1)).replace(tzinfo=zone)
    after = (local_naive + timedelta(hours=1)).replace(tzinfo=zone)
    offset_before = before.utcoffset() or timedelta(0)
    offset_after = after.utcoffset() or timedelta(0)
    gap = offset_after - offset_before
    if gap < timedelta(0):
        gap = -gap
    return gap


_VALID_POLICIES = {"earliest", "latest", "shift_forward", "raise"}


def to_utc(
    local_naive: datetime,
    lat: float,
    lon: float,
    *,
    policy: Policy = "earliest",
) -> datetime:
    """Convert a naive local datetime to UTC using timezone rules at ``lat/lon``."""

    if policy not in _VALID_POLICIES:
        raise ValueError(f"Unsupported policy: {policy}")
    tzid = tzid_for(lat, lon)
    zone = _get_zoneinfo(tzid)

    if is_ambiguous(local_naive, tzid):
        fold = 0 if policy in {"earliest", "shift_forward"} else 1
        return _attach(local_naive, tzid, fold).astimezone(timezone.utc)

    if is_nonexistent(local_naive, tzid):
        if policy == "raise":
            raise ValueError("Nonexistent local time due to DST gap")
        if policy == "shift_forward":
            gap = _dst_gap(local_naive, zone)
            adjusted = local_naive + gap
            return adjusted.replace(tzinfo=zone).astimezone(timezone.utc)
        return _attach(local_naive, tzid, 0).astimezone(timezone.utc)

    return local_naive.replace(tzinfo=zone).astimezone(timezone.utc)


def from_utc(utc_dt: datetime, lat: float, lon: float) -> datetime:
    """Convert ``utc_dt`` to the local timezone indicated by ``lat/lon``."""

    tzid = tzid_for(lat, lon)
    zone = _get_zoneinfo(tzid)
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(zone)
