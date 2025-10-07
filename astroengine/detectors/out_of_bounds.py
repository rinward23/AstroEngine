"""Detect declination out-of-bounds crossings for Moon and planets."""

from __future__ import annotations

from collections.abc import Sequence

from astroengine.ephemeris.swe import has_swe, swe

from ..ephemeris.cache import calc_ut_cached
from ..events import OutOfBoundsEvent
from .common import jd_to_iso, solve_zero_crossing

__all__ = ["find_out_of_bounds"]

_HAS_SWE = has_swe()

_BODY_CODES = {
    "moon": swe().MOON if _HAS_SWE else None,
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


def _declination(jd_ut: float, code: int) -> tuple[float, float]:
    flag = swe().FLG_SWIEPH | swe().FLG_SPEED | swe().FLG_EQUATORIAL
    xx = _vector(jd_ut, code, flag)
    dec = float(xx[1])
    speed_dec = float(xx[4]) if len(xx) > 4 else float("nan")
    return dec, speed_dec


def _tropic_limit(jd_ut: float) -> float:
    xx, ret_flag = calc_ut_cached(jd_ut, int(swe().ECL_NUT), 0)
    if ret_flag < 0:
        raise RuntimeError(f"Swiss ephemeris returned error code {ret_flag}")
    return abs(float(xx[0]))


def _oob_value(jd_ut: float, code: int) -> float:
    dec, _ = _declination(jd_ut, code)
    return abs(dec) - _tropic_limit(jd_ut)


def _sample(jd_ut: float, code: int) -> tuple[float, float, float, float]:
    dec, speed_dec = _declination(jd_ut, code)
    limit = _tropic_limit(jd_ut)
    return dec, speed_dec, limit, abs(dec) - limit


def find_out_of_bounds(
    start_jd: float,
    end_jd: float,
    bodies: Sequence[str] | None = None,
    *,
    step_hours: float = 3.0,
) -> list[OutOfBoundsEvent]:
    """Find out-of-bounds crossings for the supplied bodies."""

    if end_jd <= start_jd:
        return []
    if not _HAS_SWE:
        raise RuntimeError("Swiss ephemeris not available; install astroengine[ephem]")

    body_names = [
        b.lower() for b in (bodies if bodies is not None else _BODY_CODES.keys())
    ]
    step_days = step_hours / 24.0
    events: list[OutOfBoundsEvent] = []
    seen: set[tuple[str, int]] = set()

    for name in body_names:
        code = _BODY_CODES.get(name)
        if code is None:
            continue

        prev_jd = start_jd
        _, _, _, prev_val = _sample(prev_jd, code)

        jd = start_jd + step_days
        while jd <= end_jd + step_days:
            curr_dec, curr_speed, curr_limit, curr_val = _sample(jd, code)
            root: float | None = None

            if prev_val == 0.0:
                root = prev_jd
            elif prev_val * curr_val <= 0.0:
                try:
                    root = solve_zero_crossing(
                        lambda x, c=code: _oob_value(x, c),
                        prev_jd,
                        min(jd, end_jd),
                        tol=5e-6,
                        value_tol=5e-5,
                    )
                except ValueError:
                    root = None

            if root is not None and start_jd <= root <= end_jd:
                dec, speed_dec, limit, _ = _sample(root, code)
                hemisphere = "north" if dec >= 0 else "south"

                derivative = (1.0 if dec >= 0 else -1.0) * speed_dec
                if derivative > 0:
                    state = "enter"
                elif derivative < 0:
                    state = "exit"
                else:
                    # Fall back to surrounding samples if derivative is tiny.
                    state = "enter" if curr_val > prev_val else "exit"

                key = (name, int(round(root * 86400)))
                if key not in seen:
                    events.append(
                        OutOfBoundsEvent(
                            ts=jd_to_iso(root),
                            jd=root,
                            body=name.capitalize(),
                            state=state,
                            hemisphere=hemisphere,
                            declination=dec,
                            limit=limit,
                        )
                    )
                    seen.add(key)

            prev_jd, prev_val = jd, curr_val
            jd += step_days

    events.sort(key=lambda event: event.jd)
    return events
