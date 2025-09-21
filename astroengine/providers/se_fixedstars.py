# >>> AUTO-GEN BEGIN: se-fixedstars-adapter v1.0
"""Swiss Ephemeris fixed stars adapter (guarded, minimal).

Exposes get_star_lonlat(name, jd_ut). Requires pyswisseph and star names
supported by Swiss Ephemeris (e.g., "Aldebaran", "Regulus").
"""
from __future__ import annotations
from typing import Tuple

try:
    import swisseph as swe  # type: ignore
except Exception as e:  # pragma: no cover
    swe = None  # type: ignore


def get_star_lonlat(name: str, jd_ut: float) -> Tuple[float, float]:
    if swe is None:
        raise RuntimeError("pyswisseph not available; install astroengine[ephem]")
    # Swiss returns ecliptic lon/lat in degrees via fixstar2
    lon, lat, _dist = swe.fixstar2(name, jd_ut)
    return float(lon), float(lat)
# >>> AUTO-GEN END: se-fixedstars-adapter v1.0
