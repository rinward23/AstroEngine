# >>> AUTO-GEN BEGIN: detector-stations v1.0
from __future__ import annotations
from typing import List, Optional, Sequence

from .common import body_lon, find_root, _ensure_swiss
from ..events import StationEvent

_DEFAULT_BODIES: Sequence[str] = (
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
)


def _body_speed(jd_ut: float, body_name: str) -> float:
    if not _ensure_swiss():  # pragma: no cover - guarded by swiss skip
        raise RuntimeError("Swiss ephemeris unavailable; install astroengine[ephem]")
    import swisseph as swe  # type: ignore

    code = {
        "sun": swe.SUN,
        "moon": swe.MOON,
        "mercury": swe.MERCURY,
        "venus": swe.VENUS,
        "mars": swe.MARS,
        "jupiter": swe.JUPITER,
        "saturn": swe.SATURN,
        "uranus": swe.URANUS,
        "neptune": swe.NEPTUNE,
        "pluto": swe.PLUTO,
    }[body_name.lower()]
    result, _ = swe.calc_ut(jd_ut, code)
    return float(result[3])


def _direction_after(jd_ut: float, body: str, end_jd: float, span: float = 0.5) -> str:
    probe = min(jd_ut + span, end_jd)
    if probe <= jd_ut:
        probe = jd_ut + 1e-3
    speed = _body_speed(probe, body)
    return "retrograde" if speed < 0 else "direct"


def find_stations(
    start_jd: float,
    end_jd: float,
    bodies: Optional[Sequence[str]] = None,
) -> List[StationEvent]:
    if end_jd <= start_jd:
        return []

    selected = tuple(b.lower() for b in (bodies or _DEFAULT_BODIES))
    events: List[StationEvent] = []
    step = 1.0
    for body in selected:
        t0 = start_jd
        speed0 = _body_speed(t0, body)
        while t0 < end_jd:
            t1 = min(t0 + step, end_jd)
            speed1 = _body_speed(t1, body)
            if abs(speed0) < 1e-5:
                root = t0
            elif speed0 * speed1 > 0:
                t0, speed0 = t1, speed1
                continue
            else:
                root = find_root(lambda jd: _body_speed(jd, body), t0, t1, tol=1e-6)
            longitude = body_lon(root, body)
            direction = _direction_after(root, body, end_jd)
            events.append(
                StationEvent(
                    ts=root,
                    body=body,
                    direction=direction,
                    longitude=longitude,
                    speed=0.0,
                )
            )
            t0 = t1
            speed0 = speed1
    events.sort(key=lambda ev: (ev.ts, ev.body))
    return events
# >>> AUTO-GEN END: detector-stations v1.0
