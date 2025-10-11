# >>> AUTO-GEN BEGIN: AE Skyfield Provider v1.0
from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from importlib import metadata as importlib_metadata

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

from astroengine.canonical import BodyPosition

from . import (
    ProviderMetadata,
    register_provider,
    register_provider_metadata,
)

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


def _package_version(name: str) -> str | None:
    try:
        return importlib_metadata.version(name)
    except importlib_metadata.PackageNotFoundError:
        return None


def _skyfield_metadata(*, available: bool) -> ProviderMetadata:
    return ProviderMetadata(
        provider_id="skyfield",
        version=_package_version("skyfield"),
        supported_bodies=tuple(sorted(_PLANET_KEYS)),
        supported_frames=("ecliptic_true_date", "equatorial_true"),
        supports_declination=True,
        supports_light_time=True,
        cache_layout={"kernels": "${ASTROENGINE_CACHE}/skyfield/de440s"},
        extras_required=("skyfield", "jplephem"),
        description="Skyfield DE ephemeris provider with cached kernels.",
        module="astroengine.providers.skyfield_provider",
        available=available,
    )


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

    @staticmethod
    def _normalize_iso(iso_utc: str) -> datetime:
        dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _skyfield_time_from_datetime(self, dt: datetime):
        seconds = dt.second + dt.microsecond / 1_000_000
        return self.ts.utc(
            dt.year,
            dt.month,
            dt.day,
            dt.hour,
            dt.minute,
            seconds,
        )

    def _skyfield_time(self, iso_utc: str):
        dt = self._normalize_iso(iso_utc)
        return self._skyfield_time_from_datetime(dt)

    @staticmethod
    def _wrap_angle_diff(a: float, b: float) -> float:
        diff = a - b
        return (diff + 180.0) % 360.0 - 180.0

    def _lon_lat_dec(self, time_obj, earth, body) -> tuple[float, float, float]:
        observation = earth.at(time_obj).observe(body)
        ecliptic = observation.ecliptic_position()
        lon_angle, lat_angle, _ = ecliptic.spherical_latlon()
        lon_deg = float(lon_angle.degrees % 360.0)
        lat_deg = float(lat_angle.degrees)
        apparent = observation.apparent()
        _, dec_angle, _ = apparent.radec()
        dec_deg = float(dec_angle.degrees)
        return lon_deg, lat_deg, dec_deg

    def positions_ecliptic(
        self, iso_utc: str, bodies: Iterable[str]
    ) -> dict[str, dict[str, float]]:
        t = self._skyfield_time(iso_utc)
        out: dict[str, dict[str, float]] = {}
        earth = self.kernel["earth"]
        earth_at_t = earth.at(t)
        for name in bodies:
            key = _PLANET_KEYS.get(name.lower())
            if not key:
                continue
            body = self.kernel[key]
            ecl = earth_at_t.observe(body).ecliptic_position()
            lat, lon, distance = (
                ecl.spherical_latlon()
            )  # skyfield returns (lat, lon, distance)
            out[name] = {"lon": float(lon.degrees % 360.0), "decl": float(lat.degrees)}
        return out

    def position(self, body: str, ts_utc: str) -> BodyPosition:
        normalized = body.lower()
        key = _PLANET_KEYS.get(normalized)
        if key is None:
            raise KeyError(normalized)

        earth = self.kernel["earth"]
        target = self.kernel[key]
        base_dt = self._normalize_iso(ts_utc)
        t = self._skyfield_time_from_datetime(base_dt)
        lon_deg, lat_deg, dec_deg = self._lon_lat_dec(t, earth, target)

        delta = timedelta(minutes=1)
        delta_days = delta.total_seconds() / 86400.0
        before_dt = base_dt - delta
        after_dt = base_dt + delta
        t_before = self._skyfield_time_from_datetime(before_dt)
        t_after = self._skyfield_time_from_datetime(after_dt)
        lon_before, _, _ = self._lon_lat_dec(t_before, earth, target)
        lon_after, _, _ = self._lon_lat_dec(t_after, earth, target)
        speed_lon = self._wrap_angle_diff(lon_after, lon_before) / (2.0 * delta_days)

        return BodyPosition(
            lon=lon_deg,
            lat=lat_deg,
            dec=dec_deg,
            speed_lon=speed_lon,
        )


def _register() -> None:
    metadata_template = _skyfield_metadata(available=False)
    if load is None:
        register_provider_metadata(metadata_template, overwrite=True)
        return

    try:
        provider = SkyfieldProvider()
    except FileNotFoundError:
        register_provider_metadata(metadata_template, overwrite=True)
        LOG.info(
            "skyfield provider registration skipped",
            extra={"err_code": "SKYFIELD_KERNEL_NOT_FOUND", "provider": "skyfield"},
            exc_info=True,
        )
    except ImportError:
        register_provider_metadata(metadata_template, overwrite=True)
        LOG.info(
            "skyfield provider import unavailable",
            extra={"err_code": "SKYFIELD_IMPORT", "provider": "skyfield"},
            exc_info=True,
        )
    except Exception:
        register_provider_metadata(metadata_template, overwrite=True)
        LOG.exception(
            "unexpected skyfield provider registration failure",
            extra={"err_code": "SKYFIELD_REGISTER_UNEXPECTED", "provider": "skyfield"},
        )
    else:
        metadata = replace(metadata_template, available=True)
        register_provider(
            "skyfield",
            provider,
            metadata=metadata,
            aliases=("skyfield_ephemeris",),
        )


_register()
# >>> AUTO-GEN END: AE Skyfield Provider v2.0
