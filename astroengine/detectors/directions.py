# >>> AUTO-GEN BEGIN: detector-directions v2.0
from __future__ import annotations
from typing import Dict, List
from .common import iso_to_jd, jd_to_iso, sun_lon, moon_lon, body_lon, delta_deg, norm360
from ..events import DirectionEvent

_DEF_BODIES = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
SIDEREAL_YEAR = 365.2422


def _body_longitude(jd: float, body: str) -> float:
    name = body.lower()
    if name == "sun":
        return sun_lon(jd)
    if name == "moon":
        return moon_lon(jd)
    return body_lon(jd, name)


def solar_arc_directions(
    natal_ts: str,
    start_ts: str,
    end_ts: str,
    bodies: List[str] | None = None,
) -> List[DirectionEvent]:
    bodies = bodies or _DEF_BODIES
    natal = iso_to_jd(natal_ts)
    start = iso_to_jd(start_ts)
    end = iso_to_jd(end_ts)
    if start >= end:
        return []
    lon_sun_nat = sun_lon(natal)
    natal_positions: Dict[str, float] = {b: _body_longitude(natal, b) for b in bodies}
    out: List[DirectionEvent] = []
    years_start = int((start - natal) / SIDEREAL_YEAR)
    years_end = int((end - natal) / SIDEREAL_YEAR) + 1
    for y in range(max(0, years_start), max(0, years_end)):
        jd_time = natal + y * SIDEREAL_YEAR
        if jd_time < start or jd_time > end:
            continue
        jd_prog = natal + y  # progressed day for year y
        arc = delta_deg(sun_lon(jd_prog), lon_sun_nat)
        ts = jd_to_iso(jd_time)
        for b in bodies:
            natal_lon = natal_positions[b]
            directed_lon = norm360(natal_lon + arc)
            out.append(
                DirectionEvent(
                    method="solar_arc",
                    body=b,
                    ts=ts,
                    arc=arc,
                    directed_longitude=directed_lon,
                )
            )
    out.sort(key=lambda e: e.ts)
    return out
# >>> AUTO-GEN END: detector-directions v2.0
