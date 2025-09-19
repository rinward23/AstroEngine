# >>> AUTO-GEN BEGIN: AE Swiss Fixed Stars v1.0
from __future__ import annotations
from typing import Dict, Tuple

try:
    import swisseph as swe
except Exception:  # pragma: no cover
    swe = None


def fixstar_lonlat(name: str, jd_ut: float) -> Tuple[float, float]:
    """Resolve a fixed star by common name via Swiss Ephemeris.
    Returns (ecliptic_longitude_deg, ecliptic_latitude_deg) true-of-date.
    """
    if swe is None:
        raise ImportError("pyswisseph not installed")
    xx, resolved, retflags = swe.fixstar2_ut(name, jd_ut)
    lon, lat, dist, lon_speed, lat_speed, dist_speed = xx
    return (lon % 360.0, lat)
# >>> AUTO-GEN END: AE Swiss Fixed Stars v1.0
