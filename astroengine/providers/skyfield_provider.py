# >>> AUTO-GEN BEGIN: AE Skyfield Provider v1.0
from __future__ import annotations

import logging
from collections.abc import Iterable

LOG = logging.getLogger(__name__)

try:
    from skyfield.api import load
except ImportError:
    LOG.info(
        "skyfield load helper unavailable",
        extra={"err_code": "SKYFIELD_IMPORT", "provider": "skyfield"},
        exc_info=True,
    )
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
            LOG.warning(
                "skyfield not installed",
                extra={"err_code": "SKYFIELD_IMPORT", "provider": "skyfield"},
            )
            raise ImportError("skyfield/jplephem not installed")
        # Try common local kernels; do not fetch from internet.
        self.kernel = None
        for name in ("de440s.bsp", "de421.bsp", "de430t.bsp"):
            try:
                self.kernel = load(name)
                break
            except (OSError, ValueError, RuntimeError):
                LOG.warning(
                    "skyfield kernel unavailable",
                    extra={"err_code": "SKYFIELD_KERNEL_MISSING", "kernel": name},
                    exc_info=True,
                )
                self.kernel = None
        if self.kernel is None:
            LOG.error(
                "no local skyfield kernel found",
                extra={"err_code": "SKYFIELD_KERNEL_NOT_FOUND"},
            )
            raise FileNotFoundError("No local JPL kernel found (e.g., de440s.bsp)")
        try:
            self.ts = load.timescale()
        except (OSError, ValueError, RuntimeError) as exc:
            LOG.error(
                "failed to initialize skyfield timescale",
                extra={"err_code": "SKYFIELD_TIMESCALE"},
                exc_info=True,
            )
            raise RuntimeError("Failed to initialize skyfield timescale") from exc
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
            lat, lon, distance = (
                ecl.spherical_latlon()
            )  # skyfield returns (lat, lon, distance)
            out[name] = {"lon": float(lon.degrees % 360.0), "decl": float(lat.degrees)}
        return out


def _register() -> None:
    if load is not None:
        try:
            register_provider("skyfield", SkyfieldProvider())
        except FileNotFoundError:
            LOG.info(
                "skyfield provider registration skipped",
                extra={"err_code": "SKYFIELD_KERNEL_NOT_FOUND", "provider": "skyfield"},
                exc_info=True,
            )
        except ImportError:
            LOG.info(
                "skyfield provider import unavailable",
                extra={"err_code": "SKYFIELD_IMPORT", "provider": "skyfield"},
                exc_info=True,
            )
        except Exception:
            LOG.exception(
                "unexpected skyfield provider registration failure",
                extra={"err_code": "SKYFIELD_REGISTER_UNEXPECTED", "provider": "skyfield"},
            )


_register()
# >>> AUTO-GEN END: AE Skyfield Provider v1.0
