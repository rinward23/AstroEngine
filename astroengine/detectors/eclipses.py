from __future__ import annotations

from typing import List

from .common import _ensure_swiss
from ..events import EclipseEvent
from .lunations import find_lunations


_ECLIPSE_LATITUDE_THRESHOLD = 1.6  # degrees


def _moon_lat(jd_ut: float) -> float:
    if not _ensure_swiss():  # pragma: no cover - guarded via test skip
        raise RuntimeError("Swiss ephemeris unavailable; install astroengine[ephem]")
    import swisseph as swe  # type: ignore

    result, _ = swe.calc_ut(jd_ut, swe.MOON)
    return float(result[1])


def find_eclipses(start_jd: float, end_jd: float) -> List[EclipseEvent]:
    if end_jd <= start_jd:
        return []

    lunations = find_lunations(start_jd - 2.0, end_jd + 2.0)
    events: List[EclipseEvent] = []
    for lun in lunations:
        if lun.kind not in {"new", "full"}:
            continue
        lat = _moon_lat(lun.ts)
        if abs(lat) > _ECLIPSE_LATITUDE_THRESHOLD:
            continue
        kind = "solar" if lun.kind == "new" else "lunar"
        events.append(
            EclipseEvent(
                ts=lun.ts,
                kind=kind,
                separation_deg=abs(lat),
                phase=lun.kind,
            )
        )
    events.sort(key=lambda ev: ev.ts)
    return events
