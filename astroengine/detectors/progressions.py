# >>> AUTO-GEN BEGIN: detector-progressions v2.0
from __future__ import annotations
from typing import List
from .common import iso_to_jd, jd_to_iso, sun_lon, moon_lon, body_lon, norm360
from ..events import ProgressionEvent

_DEF_BODIES = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
SIDEREAL_YEAR = 365.2422  # days; mapping 1 day -> 1 year


def _body_longitude(jd: float, body: str) -> float:
    name = body.lower()
    if name == "sun":
        return sun_lon(jd)
    if name == "moon":
        return moon_lon(jd)
    return body_lon(jd, name)


def secondary_progressions(
    natal_ts: str,
    start_ts: str,
    end_ts: str,
    bodies: List[str] | None = None,
) -> List[ProgressionEvent]:
    bodies = bodies or _DEF_BODIES
    natal = iso_to_jd(natal_ts)
    start = iso_to_jd(start_ts)
    end = iso_to_jd(end_ts)
    if start >= end:
        return []
    out: List[ProgressionEvent] = []
    # Sample each anniversary (integer years)
    years_start = int((start - natal) / SIDEREAL_YEAR)
    years_end = int((end - natal) / SIDEREAL_YEAR) + 1
    for y in range(max(0, years_start), max(0, years_end)):
        jd_prog_time = natal + y * SIDEREAL_YEAR  # real time at anniversary y
        if jd_prog_time < start or jd_prog_time > end:
            continue
        jd_prog_ephem = natal + y  # 1 day per year after birth
        ts = jd_to_iso(jd_prog_time)
        for b in bodies:
            lon = _body_longitude(jd_prog_ephem, b)
            out.append(
                ProgressionEvent(
                    method="secondary",
                    body=b,
                    ts=ts,
                    longitude=norm360(lon),
                )
            )
    out.sort(key=lambda e: e.ts)
    return out
# >>> AUTO-GEN END: detector-progressions v2.0
