
"""Timezone lookup and conversion helpers for atlas workflows."""


from __future__ import annotations

from dataclasses import dataclass
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
"""Deprecated compatibility alias for callers expecting the legacy policy name."""

FoldPolicy = Literal["earliest", "latest", "raise", "flag"]
GapPolicy = Literal["post", "pre", "raise"]


@dataclass(frozen=True, slots=True)
class LocalTimeResolution:
    """Snapshot describing how a naive local time maps onto UTC.

    Attributes
    ----------
    input:
        Original naive datetime supplied by the caller.
    tzid:
        Olson timezone identifier resolved from the provided coordinates.
    local:
        Timezone-aware datetime after applying the disambiguation policy.
    utc:
        UTC datetime corresponding to :attr:`local`.
    fold:
        Value assigned to :pyattr:`datetime.datetime.fold` when the instant was
        ambiguous. ``0`` selects the first occurrence, ``1`` selects the second.
    ambiguous:
        ``True`` when the input overlapped a DST fall-back transition.
    ambiguous_policy:
        Policy applied for ambiguous instants (``earliest``, ``latest``,
        ``flag`` or ``raise``).
    ambiguous_flagged:
        Indicates that ``ambiguous_policy`` was ``flag``. Callers should surface
        this state in UIs so operators know manual confirmation may be needed.
    nonexistent:
        ``True`` when the input fell inside a DST spring-forward gap.
    nonexistent_policy:
        Policy applied for nonexistent instants (``pre``, ``post`` or
        ``raise``).
    gap:
        Width of the DST gap as a positive :class:`~datetime.timedelta` when the
        instant was nonexistent. ``None`` otherwise.
    """

    input: datetime
    tzid: str
    local: datetime
    utc: datetime
    fold: int
    ambiguous: bool
    ambiguous_policy: FoldPolicy
    ambiguous_flagged: bool
    nonexistent: bool
    nonexistent_policy: GapPolicy
    gap: timedelta | None = None

    def as_utc(self) -> datetime:
        """Return the UTC datetime for convenience."""

        return self.utc

__all__ = [
    "GapPolicy",
    "FoldPolicy",
    "LocalTimeResolution",
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
    ambiguous: FoldPolicy = "earliest",
    nonexistent: GapPolicy = "post",
) -> LocalTimeResolution:

    """Resolve a naive local timestamp into UTC with explicit DST policies."""

    if ambiguous not in {"earliest", "latest", "raise", "flag"}:
        raise ValueError(f"Unsupported ambiguous policy: {ambiguous}")
    if nonexistent not in {"post", "pre", "raise"}:
        raise ValueError(f"Unsupported nonexistent policy: {nonexistent}")
    if local_naive.tzinfo is not None:
        raise ValueError("local_naive must be timezone-naive")

    tzid = tzid_for(lat, lon)
    zone = ZoneInfo(tzid)

    ambiguous_state = is_ambiguous(local_naive, tzid)
    nonexistent_state = is_nonexistent(local_naive, tzid)

    fold = 0
    flagged = False
    effective_naive = local_naive
    gap: timedelta | None = None

    if ambiguous_state:
        if ambiguous == "raise":
            raise ValueError("Ambiguous local time due to DST transition")
        if ambiguous == "latest":
            fold = 1
        elif ambiguous == "flag":
            fold = 0
            flagged = True
        else:  # earliest
            fold = 0

    if nonexistent_state:
        gap = _dst_gap(local_naive, zone)
        if nonexistent == "raise":
            raise ValueError("Nonexistent local time due to DST transition")
        if nonexistent == "post":
            effective_naive = local_naive + gap
        elif nonexistent == "pre":
            effective_naive = local_naive - gap

    local_aware = effective_naive.replace(tzinfo=zone, fold=fold)
    utc_dt = local_aware.astimezone(timezone.utc)

    return LocalTimeResolution(
        input=local_naive,
        tzid=tzid,
        local=local_aware,
        utc=utc_dt,
        fold=fold,
        ambiguous=ambiguous_state,
        ambiguous_policy=ambiguous,
        ambiguous_flagged=flagged,
        nonexistent=nonexistent_state,
        nonexistent_policy=nonexistent,
        gap=gap,
    )


def from_utc(utc_dt: datetime, lat: float, lon: float) -> datetime:

    """Convert a UTC datetime into the local timezone for the coordinates."""

    tzid = tzid_for(lat, lon)
    if utc_dt.tzinfo is None:
        aware = utc_dt.replace(tzinfo=timezone.utc)
    else:
        aware = utc_dt.astimezone(timezone.utc)
    return aware.astimezone(ZoneInfo(tzid))

