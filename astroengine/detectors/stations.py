# >>> AUTO-GEN BEGIN: detector-stations v2.0
from __future__ import annotations
from typing import Iterable, List, Sequence

from .common import jd_to_iso, refine_zero_secant_bisect, _ensure_swiss
from ..events import StationEvent

_DEFAULT_BODIES: Sequence[str] = (
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
)
_STEP_DAYS = 1.0


def _body_codes():
    if not _ensure_swiss():
        raise RuntimeError("pyswisseph unavailable; install extras: astroengine[ephem]")
    import swisseph as swe  # type: ignore

    return {
        "mercury": swe.MERCURY,
        "venus": swe.VENUS,
        "mars": swe.MARS,
        "jupiter": swe.JUPITER,
        "saturn": swe.SATURN,
        "uranus": swe.URANUS,
        "neptune": swe.NEPTUNE,
        "pluto": swe.PLUTO,
    }, swe


def _speed_fn(swe_module, code: int):
    return lambda jd: float(swe_module.calc_ut(jd, code)[3])


def _lon_speed(swe_module, jd: float, code: int) -> tuple[float, float]:
    lon, lat, dist, speed_lon = swe_module.calc_ut(jd, code)
    return float(lon), float(speed_lon)


def find_stations(start_jd: float, end_jd: float, bodies: Iterable[str] | None = None) -> List[StationEvent]:
    body_codes, swe_module = _body_codes()
    body_list = list(bodies) if bodies is not None else list(_DEFAULT_BODIES)
    events: List[StationEvent] = []
    for body in body_list:
        key = body.lower()
        if key not in body_codes:
            continue
        code = body_codes[key]
        speed = _speed_fn(swe_module, code)
        prev_jd = start_jd
        prev_speed = speed(prev_jd)
        jd = start_jd + _STEP_DAYS
        while jd <= end_jd + _STEP_DAYS:
            curr_speed = speed(jd)
            root: float | None = None
            if prev_speed == 0.0:
                root = prev_jd
            elif curr_speed == 0.0:
                root = jd
            elif (prev_speed > 0 and curr_speed < 0) or (prev_speed < 0 and curr_speed > 0):
                root = refine_zero_secant_bisect(speed, prev_jd, jd, tol_deg=1e-5)
            if root is not None and start_jd <= root <= end_jd:
                lon, _ = _lon_speed(swe_module, root, code)
                if prev_speed > 0 and curr_speed < 0:
                    kind = "retrograde"
                elif prev_speed < 0 and curr_speed > 0:
                    kind = "direct"
                else:
                    kind = "station"
                events.append(
                    StationEvent(
                        body=body,
                        kind=kind,
                        ts=jd_to_iso(root),
                        longitude=lon,
                    )
                )
            prev_jd = jd
            prev_speed = curr_speed
            jd += _STEP_DAYS
    events.sort(key=lambda e: e.ts)
    return events
# >>> AUTO-GEN END: detector-stations v2.0
