# >>> AUTO-GEN BEGIN: AE Skyfield Provider v1.0
from __future__ import annotations

from collections.abc import Iterable

try:
    from skyfield.api import load
except Exception:  # pragma: no cover
    load = None

from . import register_provider

_PLANET_KEYS = {
    "sun": "sun",
    "moon": "moon",
    "mercury": "mercury",
    "venus": "venus",
    "mars": "mars",
    "jupiter": "jupiter barycenter",
    "saturn": "saturn barycenter",
    "uranus": "uranus barycenter",
    "neptune": "neptune barycenter",
    "pluto": "pluto barycenter",
}


class SkyfieldProvider:
    def __init__(self) -> None:
        if load is None:
            raise ImportError("skyfield/jplephem not installed")
        # Try common local kernels; do not fetch from internet.
        for name in ("de440s.bsp", "de421.bsp", "de430t.bsp"):
            try:
                self.kernel = load(name)
                break
            except Exception:
                self.kernel = None
        if self.kernel is None:
            raise FileNotFoundError("No local JPL kernel found (e.g., de440s.bsp)")
        self.ts = load.timescale()
        self.ecliptic = (
            None  # skyfield computes ecliptic-of-date via .ecliptic_position()
        )

    def positions_ecliptic(
        self, iso_utc: str, bodies: Iterable[str]
    ) -> dict[str, dict[str, float]]:
        t = self.ts.from_datetime64([iso_utc]).at(
            0
        )  # accepts numpy datetime64 or str in newer versions
        out: dict[str, dict[str, float]] = {}
        earth = self.kernel["earth"]
        for name in bodies:
            key = _PLANET_KEYS.get(name.lower())
            if not key:
                continue
            body = self.kernel[key]
            ecl = earth.at(t).observe(body).ecliptic_position()
            lon, lat, distance = (
                ecl.spherical_latlon()
            )  # skyfield returns lat, lon order
            out[name] = {"lon": float(lon.degrees % 360.0), "decl": float(lat.degrees)}
        return out


def _register() -> None:
    if load is not None:
        try:
            register_provider("skyfield", SkyfieldProvider())
        except Exception:
            # If kernel missing, skip registration to avoid noisy failures
            pass


_register()
# >>> AUTO-GEN END: AE Skyfield Provider v1.0
