"""Planetary station detector backed by Swiss ephemeris speeds."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from astroengine.ephemeris.swe import has_swe, swe

from ..ephemeris.cache import calc_ut_cached
from ..events import ShadowPeriod, StationEvent
from .common import delta_deg, jd_to_iso, solve_zero_crossing

__all__ = ["find_stations", "find_shadow_periods"]

_HAS_SWE = has_swe()

_BODY_CODES = {
    "mercury": swe().MERCURY if _HAS_SWE else None,
    "venus": swe().VENUS if _HAS_SWE else None,
    "mars": swe().MARS if _HAS_SWE else None,
    "jupiter": swe().JUPITER if _HAS_SWE else None,
    "saturn": swe().SATURN if _HAS_SWE else None,
    "uranus": swe().URANUS if _HAS_SWE else None,
    "neptune": swe().NEPTUNE if _HAS_SWE else None,
    "pluto": swe().PLUTO if _HAS_SWE else None,
}


def _vector(jd_ut: float, code: int, flag: int) -> tuple[float, ...]:
    values, ret_flag = calc_ut_cached(jd_ut, code, flag)
    if ret_flag < 0:
        raise RuntimeError(f"Swiss ephemeris returned error code {ret_flag}")
    return tuple(values)


def _speed(jd_ut: float, code: int) -> float:
    flag = swe().FLG_SWIEPH | swe().FLG_SPEED
    xx = _vector(jd_ut, code, flag)
    return float(xx[3])


def _longitude(jd_ut: float, code: int) -> float:
    flag = swe().FLG_SWIEPH | swe().FLG_SPEED
    xx = _vector(jd_ut, code, flag)
    return float(xx[0]) % 360.0


def find_stations(
    start_jd: float,
    end_jd: float,
    bodies: Sequence[str] | None = None,
    *,
    step_days: float = 0.5,
) -> list[StationEvent]:
    """Return planetary station events between ``start_jd`` and ``end_jd``."""

    if end_jd <= start_jd:
        return []
    if not _HAS_SWE:
        raise RuntimeError("Swiss ephemeris not available; install astroengine[ephem]")

    body_names = [
        b.lower() for b in (bodies if bodies is not None else _BODY_CODES.keys())
    ]

    events: list[StationEvent] = []
    seen: set[tuple[str, int]] = set()

    for name in body_names:
        code = _BODY_CODES.get(name)
        if code is None:
            continue

        prev_jd = start_jd
        prev_speed = _speed(prev_jd, code)
        current = start_jd + step_days

        while current <= end_jd + step_days:
            curr_speed = _speed(current, code)
            root: float | None = None

            if prev_speed == 0.0:
                root = prev_jd
            elif prev_speed * curr_speed <= 0.0:
                try:
                    root = solve_zero_crossing(
                        lambda x, c=code: _speed(x, c),
                        prev_jd,
                        min(current, end_jd),
                        tol=5e-6,
                        value_tol=5e-7,
                    )
                except ValueError:
                    root = None

            if root is not None and start_jd <= root <= end_jd:
                key = (name, int(round(root * 86400)))
                if key not in seen:
                    longitude = _longitude(root, code)
                    station_type = _classify_station(root, code)
                    if station_type not in {"retrograde", "direct"}:
                        station_type = None
                    events.append(
                        StationEvent(
                            ts=jd_to_iso(root),
                            jd=root,
                            body=name.capitalize(),
                            motion="stationary",
                            longitude=longitude,
                            speed_longitude=0.0,
                            station_type=station_type,
                        )
                    )
                    seen.add(key)

            prev_jd, prev_speed = current, curr_speed
            current += step_days

    events.sort(key=lambda event: event.jd)
    return events


def _classify_station(jd_ut: float, code: int) -> str:
    """Return ``"retrograde"`` or ``"direct"`` classification for a station."""

    offsets = (0.5 / 24.0, 1.0 / 24.0, 2.0 / 24.0)
    for delta in offsets:
        before = _speed(jd_ut - delta, code)
        after = _speed(jd_ut + delta, code)
        if before > 0 and after < 0:
            return "retrograde"
        if before < 0 and after > 0:
            return "direct"
    return "stationary"


def _locate_longitude_crossing(
    code: int,
    start_jd: float,
    target_longitude: float,
    *,
    direction: int,
    limit_jd: float,
    step_days: float,
) -> float | None:
    """Return the Julian day where longitude equals ``target_longitude``."""

    step = abs(step_days) if step_days > 0 else 0.5
    step *= 1 if direction >= 0 else -1

    prev_jd = start_jd
    prev_delta = delta_deg(_longitude(prev_jd, code), target_longitude)
    jd = prev_jd + step

    while (jd - limit_jd) * direction <= 0:
        curr_delta = delta_deg(_longitude(jd, code), target_longitude)
        root: float | None = None

        if prev_delta == 0.0:
            root = prev_jd
        elif prev_delta * curr_delta <= 0.0:
            left, right = sorted((prev_jd, jd))
            try:
                root = solve_zero_crossing(
                    lambda value, c=code, tgt=target_longitude: delta_deg(
                        _longitude(value, c), tgt
                    ),
                    left,
                    right,
                    tol=5e-6,
                    value_tol=5e-6,
                )
            except ValueError:
                root = None

        if root is not None:
            return root

        prev_jd = jd
        prev_delta = curr_delta
        jd += step

    return None


def _window_overlaps(
    start_a: float, end_a: float, start_b: float, end_b: float
) -> bool:
    return not (end_a < start_b or start_a > end_b)


def find_shadow_periods(
    start_jd: float,
    end_jd: float,
    bodies: Sequence[str] | None = None,
    *,
    step_days: float = 0.5,
) -> list[ShadowPeriod]:
    """Return shadow windows bracketing retrograde/direct stations."""

    if end_jd <= start_jd:
        return []
    if swe is None:
        raise RuntimeError("Swiss ephemeris not available; install astroengine[ephem]")

    body_names = [
        b.lower() for b in (bodies if bodies is not None else _BODY_CODES.keys())
    ]
    station_events = find_stations(
        start_jd - 60.0,
        end_jd + 60.0,
        bodies=body_names,
        step_days=step_days,
    )

    grouped: dict[str, list[StationEvent]] = defaultdict(list)
    for event in station_events:
        grouped[event.body.lower()].append(event)

    periods: list[ShadowPeriod] = []

    for name in body_names:
        code = _BODY_CODES.get(name)
        if code is None:
            continue

        stations = sorted(grouped.get(name, []), key=lambda evt: evt.jd)
        if not stations:
            continue

        typed: list[tuple[StationEvent, str]] = []
        for event in stations:
            kind = event.station_type or _classify_station(event.jd, code)
            if kind in {"retrograde", "direct"}:
                typed.append((event, kind))

        for idx in range(len(typed) - 1):
            retro_event, retro_kind = typed[idx]
            direct_event, direct_kind = typed[idx + 1]
            if retro_kind != "retrograde" or direct_kind != "direct":
                continue

            retro = retro_event
            direct = direct_event

            span = max(direct.jd - retro.jd, 20.0)
            pre_limit = retro.jd - (span * 1.5)
            post_limit = direct.jd + (span * 1.5)

            pre_start = _locate_longitude_crossing(
                code,
                retro.jd,
                direct.longitude,
                direction=-1,
                limit_jd=pre_limit,
                step_days=step_days,
            )

            if (
                pre_start is not None
                and _window_overlaps(pre_start, retro.jd, start_jd, end_jd)
            ):
                start_lon = _longitude(pre_start, code) % 360.0
                periods.append(
                    ShadowPeriod(
                        ts=jd_to_iso(pre_start),
                        jd=pre_start,
                        body=retro.body,
                        kind="pre",
                        end_ts=retro.ts,
                        end_jd=retro.jd,
                        retrograde_station_ts=retro.ts,
                        retrograde_station_jd=retro.jd,
                        retrograde_longitude=retro.longitude,
                        direct_station_ts=direct.ts,
                        direct_station_jd=direct.jd,
                        direct_longitude=direct.longitude,
                        start_longitude=start_lon,
                        end_longitude=retro.longitude,
                    )
                )

            post_end = _locate_longitude_crossing(
                code,
                direct.jd,
                retro.longitude,
                direction=1,
                limit_jd=post_limit,
                step_days=step_days,
            )

            if (
                post_end is not None
                and _window_overlaps(direct.jd, post_end, start_jd, end_jd)
            ):
                end_lon = _longitude(post_end, code) % 360.0
                periods.append(
                    ShadowPeriod(
                        ts=direct.ts,
                        jd=direct.jd,
                        body=direct.body,
                        kind="post",
                        end_ts=jd_to_iso(post_end),
                        end_jd=post_end,
                        retrograde_station_ts=retro.ts,
                        retrograde_station_jd=retro.jd,
                        retrograde_longitude=retro.longitude,
                        direct_station_ts=direct.ts,
                        direct_station_jd=direct.jd,
                        direct_longitude=direct.longitude,
                        start_longitude=direct.longitude,
                        end_longitude=end_lon,
                    )
                )

    periods.sort(key=lambda period: (period.jd, period.kind))
    return periods
