# >>> AUTO-GEN BEGIN: AE Swiss Provider v1.0
from __future__ import annotations
import os
from datetime import datetime, timezone
from typing import Dict, Iterable

try:
    import swisseph as swe  # pyswisseph imports the module name 'swisseph'
except Exception:  # pragma: no cover
    swe = None

from . import EphemerisProvider, register_provider


_BODY_IDS = {
    "sun": 0, "moon": 1, "mercury": 2, "venus": 3, "mars": 4,
    "jupiter": 5, "saturn": 6, "uranus": 7, "neptune": 8, "pluto": 9,
}


class SwissProvider:
    def __init__(self) -> None:
        if swe is None:
            raise ImportError("pyswisseph is not installed")
        eph = os.environ.get("SWE_EPH_PATH") or os.environ.get("SE_EPHE_PATH")
        if eph:
            swe.set_ephe_path(eph)

    def positions_ecliptic(self, iso_utc: str, bodies: Iterable[str]) -> Dict[str, Dict[str, float]]:
        dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
        dt_utc = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        hour = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0 + dt_utc.microsecond / 3.6e9
        jd_ut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour)
        flags = swe.FLG_SWIEPH | swe.FLG_SPEED
        out: Dict[str, Dict[str, float]] = {}
        for name in bodies:
            if name.lower() not in _BODY_IDS:
                continue
            ipl = _BODY_IDS[name.lower()]
            values, retflag = swe.calc_ut(jd_ut, ipl, flags)
            lon, lat, dist, lon_speed, lat_speed, dist_speed = values
            lon_ecl, lat_ecl = lon % 360.0, lat
            out[name] = {"lon": lon_ecl, "decl": lat_ecl, "speed_lon": lon_speed}
        return out


def _register() -> None:
    if swe is not None:
        register_provider("swiss", SwissProvider())


_register()
# >>> AUTO-GEN END: AE Swiss Provider v1.0
