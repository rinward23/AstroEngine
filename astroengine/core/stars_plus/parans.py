from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, Iterable, List, Tuple

from .catalog import Star
from .geometry import approximate_transit_times

PositionProvider = Callable[[datetime], Dict[str, float]]  # returns ecliptic longitudes for planets

@dataclass
class Location:
    lat_deg: float
    lon_east_deg: float  # east-positive

@dataclass
class ParanPair:
    star_name: str
    planet_name: str
    star_event: str     # 'rise'|'set'|'culminate'
    planet_event: str   # 'rise'|'set'|'culminate'

@dataclass
class ParanEvent:
    kind: str
    time: datetime
    meta: Dict[str, object]


def detect_parans(
    date_start: datetime,
    date_end: datetime,
    location: Location,
    stars: Dict[str, Star],
    provider_radec: Callable[[datetime, str], Tuple[float, float]],  # planet → (RA,Dec) provider
    pairs: Iterable[ParanPair],
    tol_minutes: float = 8.0,
    step_days: int = 1,
) -> List[ParanEvent]:
    """Scan dates [start,end] (UTC) for parans matching the `pairs` at `location`.

    MVP: For each UTC date, compute star and planet event times (rise/set/culm) using their RA/Dec
    and report matches when the absolute time difference ≤ tol_minutes.
    """
    out: List[ParanEvent] = []
    cur = date_start.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    end = date_end.astimezone(timezone.utc)

    while cur <= end:
        for pair in pairs:
            star = stars.get(pair.star_name)
            if not star:
                continue
            # Star events for this date
            st_events = approximate_transit_times(cur, location.lon_east_deg, star.ra_deg, star.dec_deg, location.lat_deg)

            # Planet RA/Dec at midday (approx across day)
            mid = cur + timedelta(hours=12)
            pra, pdec = provider_radec(mid, pair.planet_name)
            pl_events = approximate_transit_times(cur, location.lon_east_deg, pra, pdec, location.lat_deg)

            ts_star = st_events.get(pair.star_event)
            ts_plan = pl_events.get(pair.planet_event)
            if ts_star and ts_plan:
                dt_min = abs((ts_star - ts_plan).total_seconds()) / 60.0
                if dt_min <= tol_minutes:
                    out.append(ParanEvent(
                        kind="paran",
                        time=ts_star if ts_star < ts_plan else ts_plan,
                        meta={
                            "star": pair.star_name,
                            "planet": pair.planet_name,
                            "star_event": pair.star_event,
                            "planet_event": pair.planet_event,
                            "dt_diff_min": dt_min,
                        }
                    ))
        cur += timedelta(days=step_days)

    out.sort(key=lambda e: e.time)
    return out
