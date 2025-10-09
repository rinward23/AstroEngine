
"""Timezone lookup and conversion helpers for atlas workflows."""


from __future__ import annotations

import importlib
import importlib.util
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
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

    def to_metadata(self) -> dict[str, object]:
        """Serialise the resolution into a metadata dictionary."""

        payload: dict[str, object] = {
            "input_local": self.input.isoformat(),
            "tzid": self.tzid,
            "resolved_local": self.local.isoformat(),
            "utc": self.utc.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "fold": int(self.fold),
            "ambiguous": self.ambiguous,
            "ambiguous_policy": self.ambiguous_policy,
            "ambiguous_flagged": self.ambiguous_flagged,
            "nonexistent": self.nonexistent,
            "nonexistent_policy": self.nonexistent_policy,
        }
        if self.gap is not None:
            payload["gap_seconds"] = self.gap.total_seconds()
        return payload

__all__ = [
    "GapPolicy",
    "FoldPolicy",
    "LocalTimeResolution",
    "Policy",

    "from_utc",
    "is_ambiguous",
    "is_nonexistent",
    "to_utc",
    "to_utc_with_timezone",
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
    utc0 = _attach(local_naive, zone, 0).astimezone(UTC)
    utc1 = _attach(local_naive, zone, 1).astimezone(UTC)
    return utc0 != utc1 and utc0 < utc1


def is_nonexistent(local_naive: datetime, tzid: str) -> bool:
    """Return ``True`` when the local time is skipped (DST spring-forward)."""

    zone = ZoneInfo(tzid)
    utc0 = _attach(local_naive, zone, 0).astimezone(UTC)
    utc1 = _attach(local_naive, zone, 1).astimezone(UTC)
    return utc0 != utc1 and utc0 > utc1



def _dst_gap(local_naive: datetime, zone: ZoneInfo) -> timedelta:
    before = (local_naive - timedelta(hours=1)).replace(tzinfo=zone)
    after = (local_naive + timedelta(hours=1)).replace(tzinfo=zone)

    before_offset = before.utcoffset() or timedelta(0)
    after_offset = after.utcoffset() or timedelta(0)
    gap = after_offset - before_offset
    return gap if gap >= timedelta(0) else -gap



def _resolve_policies(ambiguous: FoldPolicy, nonexistent: GapPolicy) -> None:
    if ambiguous not in {"earliest", "latest", "raise", "flag"}:
        raise ValueError(f"Unsupported ambiguous policy: {ambiguous}")
    if nonexistent not in {"post", "pre", "raise"}:
        raise ValueError(f"Unsupported nonexistent policy: {nonexistent}")


def _apply_legacy_policy(
    policy: Policy | None,
    ambiguous: FoldPolicy,
    nonexistent: GapPolicy,
) -> tuple[FoldPolicy, GapPolicy]:
    if policy is None:
        return ambiguous, nonexistent
    if policy == "shift_forward":
        nonexistent = "post"
    elif policy in {"earliest", "latest", "raise"}:
        ambiguous = policy  # type: ignore[assignment]
    else:
        raise ValueError(f"Unsupported legacy policy: {policy}")
    return ambiguous, nonexistent


def _resolve_local_time(
    local_naive: datetime,
    tzid: str,
    zone: ZoneInfo,
    *,
    ambiguous: FoldPolicy,
    nonexistent: GapPolicy,
) -> LocalTimeResolution:
    if local_naive.tzinfo is not None:
        raise ValueError("local_naive must be timezone-naive")

    fold = 0
    flagged = False
    gap: timedelta | None = None
    effective_naive = local_naive

    aware_fold0 = local_naive.replace(tzinfo=zone, fold=0)
    aware_fold1 = local_naive.replace(tzinfo=zone, fold=1)
    utc_fold0 = aware_fold0.astimezone(UTC)
    utc_fold1 = aware_fold1.astimezone(UTC)

    ambiguous_state = utc_fold0 != utc_fold1 and utc_fold0 < utc_fold1
    nonexistent_state = utc_fold0 != utc_fold1 and utc_fold0 > utc_fold1

    if ambiguous_state:
        if ambiguous == "raise":
            raise ValueError("Ambiguous local time due to DST transition")
        if ambiguous == "latest":
            fold = 1
        elif ambiguous == "flag":
            flagged = True
            fold = 0
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
    utc_dt = local_aware.astimezone(UTC)

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


def to_utc(
    local_naive: datetime,
    lat: float,
    lon: float,
    *,
    ambiguous: FoldPolicy = "earliest",
    nonexistent: GapPolicy = "post",
    policy: Policy | None = None,
) -> LocalTimeResolution:

    """Resolve a naive local timestamp into UTC with explicit DST policies."""

    ambiguous, nonexistent = _apply_legacy_policy(policy, ambiguous, nonexistent)
    _resolve_policies(ambiguous, nonexistent)
    tzid = tzid_for(lat, lon)
    zone = ZoneInfo(tzid)
    return _resolve_local_time(
        local_naive,
        tzid,
        zone,
        ambiguous=ambiguous,
        nonexistent=nonexistent,
    )


def to_utc_with_timezone(
    local_naive: datetime,
    tzid: str,
    *,
    ambiguous: FoldPolicy = "earliest",
    nonexistent: GapPolicy = "post",
    policy: Policy | None = None,
) -> LocalTimeResolution:
    """Resolve a naive local timestamp using an explicit timezone identifier."""

    ambiguous, nonexistent = _apply_legacy_policy(policy, ambiguous, nonexistent)
    _resolve_policies(ambiguous, nonexistent)
    zone = ZoneInfo(tzid)
    return _resolve_local_time(
        local_naive,
        tzid,
        zone,
        ambiguous=ambiguous,
        nonexistent=nonexistent,
    )


def from_utc(utc_dt: datetime, lat: float, lon: float) -> datetime:

    """Convert a UTC datetime into the local timezone for the coordinates."""

    tzid = tzid_for(lat, lon)
    if utc_dt.tzinfo is None:
        aware = utc_dt.replace(tzinfo=UTC)
    else:
        aware = utc_dt.astimezone(UTC)
    return aware.astimezone(ZoneInfo(tzid))
