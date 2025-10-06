"""Rise, set, and transit calculations for apparent positions."""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from ...ephemeris.adapter import EphemerisAdapter, ObserverLocation
from .topocentric import MetConditions, horizontal_from_equatorial, topocentric_equatorial


@dataclass(frozen=True)
class EventOptions:
    """Common options for observational event solvers."""

    refraction: bool = True
    met: MetConditions = field(default_factory=MetConditions)
    horizon_dip_deg: float = 0.0


def _normalize_day(moment: datetime) -> datetime:
    utc = moment.astimezone(UTC) if moment.tzinfo else moment.replace(tzinfo=UTC)
    return utc.replace(hour=0, minute=0, second=0, microsecond=0)


def _altitude_minus(
    adapter: EphemerisAdapter,
    body: int,
    moment: datetime,
    observer: ObserverLocation,
    target_alt: float,
    opts: EventOptions,
) -> float:
    equ = topocentric_equatorial(adapter, body, moment, observer)
    horiz = horizontal_from_equatorial(
        equ.right_ascension_deg,
        equ.declination_deg,
        moment,
        observer,
        refraction=opts.refraction,
        met=opts.met,
        horizon_dip_deg=opts.horizon_dip_deg,
    )
    return horiz.altitude_deg - target_alt


def _hour_angle_sin(
    adapter: EphemerisAdapter,
    body: int,
    moment: datetime,
    observer: ObserverLocation,
) -> float:
    equ = topocentric_equatorial(adapter, body, moment, observer)
    # horizontal_from_equatorial already computes H internally; recover using sidereal time
    lst = _local_sidereal_deg(moment, observer.longitude_deg)
    H_deg = (lst - equ.right_ascension_deg + 540.0) % 360.0 - 180.0
    return math.sin(math.radians(H_deg))


def _local_sidereal_deg(moment: datetime, lon_deg: float) -> float:
    # Mirror helper from topocentric module to avoid circular import.
    from ...core.time import julian_day

    jd = julian_day(moment.astimezone(UTC) if moment.tzinfo else moment.replace(tzinfo=UTC))
    T = (jd - 2451545.0) / 36525.0
    gmst = (
        280.46061837
        + 360.98564736629 * (jd - 2451545.0)
        + 0.000387933 * T * T
        - (T ** 3) / 38710000.0
    )
    return (gmst + lon_deg) % 360.0


def _refine_root(
    func: Callable[[datetime], float],
    start: datetime,
    end: datetime,
    *,
    tolerance_seconds: float = 0.5,
    max_iter: int = 32,
) -> datetime:
    f0 = func(start)
    f1 = func(end)
    if f0 == 0:
        return start
    if f1 == 0:
        return end
    if f0 * f1 > 0:
        raise ValueError("root not bracketed")
    t0, t1 = start, end
    for _ in range(max_iter):
        mid = t0 + (t1 - t0) / 2
        fm = func(mid)
        if abs(fm) < 1e-9:
            return mid
        if fm * f0 < 0:
            t1 = mid
            f1 = fm
        else:
            t0 = mid
            f0 = fm
        if (t1 - t0).total_seconds() <= tolerance_seconds:
            break
    return t0 + (t1 - t0) / 2


def _scan_intervals(
    func: Callable[[datetime], float],
    start: datetime,
    end: datetime,
    step: timedelta,
) -> Iterable[tuple[datetime, datetime]]:
    prev_time = start
    prev_val = func(prev_time)
    current = start + step
    while current <= end:
        cur_val = func(current)
        if prev_val == 0:
            yield (prev_time, prev_time)
        elif cur_val == 0:
            yield (current, current)
        elif prev_val * cur_val < 0:
            yield (prev_time, current)
        prev_time = current
        prev_val = cur_val
        current += step


def transit_time(
    adapter: EphemerisAdapter,
    body: int,
    date: datetime,
    observer: ObserverLocation,
) -> datetime | None:
    """Return the UTC time of upper transit for ``body`` on ``date``."""

    base = _normalize_day(date)
    end = base + timedelta(days=1)
    step = timedelta(minutes=5)
    func = lambda t: _hour_angle_sin(adapter, body, t, observer)
    brackets = list(_scan_intervals(func, base, end, step))
    if not brackets:
        return None
    # Choose interval closest to midday if multiple roots
    def midpoint(interval: tuple[datetime, datetime]) -> datetime:
        return interval[0] + (interval[1] - interval[0]) / 2

    target = min(
        brackets,
        key=lambda iv: abs(
            (midpoint(iv) - (base + timedelta(hours=12))).total_seconds()
        ),
    )
    start, finish = target
    return _refine_root(func, start, finish)


def rise_set_times(
    adapter: EphemerisAdapter,
    body: int,
    date: datetime,
    observer: ObserverLocation,
    *,
    h0_deg: float = -0.5667,
    options: EventOptions | None = None,
) -> tuple[datetime | None, datetime | None]:
    """Return rise and set times (UTC) for ``body`` on ``date``."""

    opts = options or EventOptions()
    base = _normalize_day(date)
    end = base + timedelta(days=1)
    step = timedelta(minutes=5)

    def func(t: datetime) -> float:
        return _altitude_minus(adapter, body, t, observer, h0_deg, opts)

    brackets = list(_scan_intervals(func, base, end, step))
    if not brackets:
        return (None, None)
    rise: datetime | None = None
    set_: datetime | None = None
    for start, finish in brackets:
        f_start = func(start)
        f_end = func(finish)
        if f_start < f_end and rise is None:
            rise = _refine_root(func, start, finish)
        elif f_start > f_end and set_ is None:
            set_ = _refine_root(func, start, finish)
    return (rise, set_)


__all__ = ["EventOptions", "rise_set_times", "transit_time"]
