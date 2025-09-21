# >>> AUTO-GEN BEGIN: detector-eclipses v2.0
from __future__ import annotations
from typing import List
from .common import iso_to_jd, moon_lat
from ..events import EclipseEvent
from .lunations import find_lunations

# Approx threshold for ecliptic latitude at lunation (deg)
_LAT_THRESH = 1.6


def find_eclipses(start_ut: float, end_ut: float) -> List[EclipseEvent]:
    out: List[EclipseEvent] = []
    # Re-use lunations (new + full)
    luns = find_lunations(start_ut, end_ut)
    for e in luns:
        if e.kind not in ("new", "full"):
            continue
        jd = iso_to_jd(e.ts)
        lat = abs(moon_lat(jd))
        if lat <= _LAT_THRESH:
            kind = "solar" if e.kind == "new" else "lunar"
            out.append(EclipseEvent(kind=kind, ts=e.ts, magnitude=None))
    return out
# >>> AUTO-GEN END: detector-eclipses v2.0
