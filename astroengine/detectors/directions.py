from __future__ import annotations

from math import floor
from typing import Iterable, List, Sequence

from .common import body_lon, delta_deg, iso_to_jd, norm360
from ..events import DirectionEvent

_DEFAULT_BODIES: Sequence[str] = (
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
)

_SYNODIC_YEAR = 365.2422


def _iter_years(start_jd: float, end_jd: float, natal_jd: float) -> Iterable[int]:
    start_year = max(0, floor((start_jd - natal_jd) / _SYNODIC_YEAR))
    end_year = max(start_year, floor((end_jd - natal_jd) / _SYNODIC_YEAR) + 1)
    for year in range(int(start_year), int(end_year) + 1):
        life_jd = natal_jd + year * _SYNODIC_YEAR
        if life_jd < start_jd - 1 or life_jd > end_jd + 1:
            continue
        yield year


def solar_arc_directions(
    natal_ts: str,
    start_ts: str,
    end_ts: str,
    *,
    bodies: Sequence[str] | None = None,
) -> List[DirectionEvent]:
    bodies = tuple(bodies or _DEFAULT_BODIES)
    natal_jd = iso_to_jd(natal_ts)
    start_jd = iso_to_jd(start_ts)
    end_jd = iso_to_jd(end_ts)

    natal_positions = {body: body_lon(natal_jd, body) for body in bodies}

    events: List[DirectionEvent] = []
    for year in _iter_years(start_jd, end_jd, natal_jd):
        progressed_sun = body_lon(natal_jd + year, "sun")
        arc = delta_deg(progressed_sun, natal_positions["sun"])
        life_jd = natal_jd + year * _SYNODIC_YEAR
        if life_jd < start_jd or life_jd > end_jd:
            continue
        positions = {
            body: norm360(natal_positions[body] + arc) for body in bodies
        }
        events.append(
            DirectionEvent(
                ts=life_jd,
                age=float(year),
                positions=positions,
            )
        )
    events.sort(key=lambda ev: ev.ts)
    return events
