from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import replace
from datetime import UTC, datetime
from importlib import metadata as importlib_metadata

LOG = logging.getLogger(__name__)

from astroengine.canonical import BodyPosition
from astroengine.core.bodies import canonical_name
from astroengine.core.time import TimeConversion, to_tt
from astroengine.ephemeris import (
    EphemerisAdapter,
    EphemerisConfig,
    ObserverLocation,
    TimeScaleContext,
)
from astroengine.ephemeris.support import SupportIssue
from astroengine.ephemeris.swe import has_swe, swe
from astroengine.ephemeris.utils import get_se_ephe_path

from .swisseph_adapter import VariantConfig, se_body_id_for

_HAS_SWE = has_swe()

if not _HAS_SWE:
    LOG.info(
        "pyswisseph not installed",
        extra={"err_code": "SWISS_IMPORT"},
        exc_info=True,
    )

try:  # pragma: no cover - exercised via runtime fallback
    from pymeeus.Epoch import Epoch
    from pymeeus.Jupiter import Jupiter as _Jupiter
    from pymeeus.Mars import Mars as _Mars
    from pymeeus.Mercury import Mercury as _Mercury
    from pymeeus.Moon import Moon as _Moon
    from pymeeus.Neptune import Neptune as _Neptune
    from pymeeus.Pluto import Pluto as _Pluto
    from pymeeus.Saturn import Saturn as _Saturn
    from pymeeus.Sun import Sun as _Sun
    from pymeeus.Uranus import Uranus as _Uranus
    from pymeeus.Venus import Venus as _Venus

    _PYMEEUS_AVAILABLE = True
except ImportError:
    LOG.info(
        "pymeeus fallback unavailable",
        extra={"err_code": "PYMEEUS_IMPORT"},
        exc_info=True,
    )
    Epoch = None  # type: ignore[assignment]
    (
        _Mercury,
        _Venus,
        _Mars,
        _Jupiter,
        _Saturn,
        _Uranus,
        _Neptune,
        _Pluto,
        _Sun,
        _Moon,
    ) = (
        None,
    ) * 10  # type: ignore[assignment]
    _PYMEEUS_AVAILABLE = False

from . import ProviderMetadata, register_provider, register_provider_metadata

_BODY_IDS: dict[str, int] = {
    "sun": 0,
    "moon": 1,
    "mercury": 2,
    "venus": 3,
    "mars": 4,
    "jupiter": 5,
    "saturn": 6,
    "uranus": 7,
    "neptune": 8,
    "pluto": 9,
}


def _package_version(name: str) -> str | None:
    try:
        return importlib_metadata.version(name)
    except importlib_metadata.PackageNotFoundError:
        return None


def _swiss_metadata(
    *,
    available: bool,
    version: str | None,
    description: str,
    supports_declination: bool,
) -> ProviderMetadata:
    return ProviderMetadata(
        provider_id="swiss_ephemeris",
        version=version,
        supported_bodies=tuple(sorted(_BODY_IDS)),
        supported_frames=("ecliptic_true_date", "equatorial_true"),
        supports_declination=supports_declination,
        supports_light_time=False,
        cache_layout={"ephemeris": "runtime_configured"},
        extras_required=("ephem",),
        description=description,
        module="astroengine.providers.swiss_provider",
        available=available,
    )

if _HAS_SWE:  # pragma: no cover - depends on installed ephemeris
    swe_module = swe()
    for attr, name in (
        ("CERES", "ceres"),
        ("PALLAS", "pallas"),
        ("JUNO", "juno"),
        ("VESTA", "vesta"),
        ("CHIRON", "chiron"),
        ("PHOLUS", "pholus"),
        ("NESSUS", "nessus"),
        ("ERIS", "eris"),
        ("HAUMEA", "haumea"),
        ("MAKEMAKE", "makemake"),
        ("SEDNA", "sedna"),
        ("QUAOAR", "quaoar"),
        ("ORCUS", "orcus"),
        ("IXION", "ixion"),
    ):
        code = getattr(swe_module, attr, None)
        if code is not None:
            _BODY_IDS[name] = int(code)


class SwissProvider:
    def __init__(self) -> None:
        if not _HAS_SWE:
            raise ImportError("pyswisseph is not installed")
        eph = get_se_ephe_path()
        if eph:
            swe().set_ephe_path(eph)
        self._config = EphemerisConfig(ephemeris_path=str(eph) if eph else None)
        self._adapter = EphemerisAdapter(self._config)
        self._body_ids = dict(_BODY_IDS)
        self._variant_config = VariantConfig()
        self._last_support_issues: list[SupportIssue] = []

    def configure(
        self,
        *,
        topocentric: bool | None = None,
        observer: ObserverLocation | None = None,
        sidereal: bool | None = None,
        time_scale: TimeScaleContext | None = None,
        nodes_variant: str | None = None,
        lilith_variant: str | None = None,
    ) -> None:
        """Update ephemeris configuration used by the provider."""

        variant_updates: dict[str, str] = {}
        if nodes_variant:
            normalized = nodes_variant.lower()
            if normalized not in {"mean", "true"}:
                raise ValueError("nodes_variant must be 'mean' or 'true'")
            variant_updates["nodes_variant"] = normalized
        if lilith_variant:
            normalized = lilith_variant.lower()
            if normalized not in {"mean", "true"}:
                raise ValueError("lilith_variant must be 'mean' or 'true'")
            variant_updates["lilith_variant"] = normalized
        if variant_updates:
            self._variant_config = replace(self._variant_config, **variant_updates)

        cfg = self._config
        updates: dict[str, object] = {}
        if topocentric is not None:
            updates["topocentric"] = topocentric
        if observer is not None or (topocentric is False and cfg.observer is not None):
            updates["observer"] = observer
        if sidereal is not None:
            updates["sidereal"] = sidereal
        if time_scale is not None:
            updates["time_scale"] = time_scale
        if not updates:
            return

        new_config = replace(cfg, **updates)
        if new_config == self._config:
            return

        self._config = new_config
        try:
            self._adapter.reconfigure(new_config)
        except AttributeError:  # pragma: no cover - legacy adapter fallback
            self._adapter = EphemerisAdapter(new_config)

    @staticmethod
    def _normalize_iso(iso_utc: str) -> datetime:
        dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
        return dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)

    def _time_conversion(self, iso_utc: str) -> TimeConversion:
        return to_tt(self._normalize_iso(iso_utc))

    def _body_id(self, name: str) -> int:
        key = canonical_name(name)
        if key in self._body_ids:
            return self._body_ids[key]
        raise KeyError(key)

    def _position_from_sample(self, sample, *, derived: bool = False) -> BodyPosition:
        lon = sample.longitude % 360.0
        lat = sample.latitude
        dec = sample.declination
        if derived:
            lon = (lon + 180.0) % 360.0
            lat = -lat
            dec = -dec
        return BodyPosition(lon=lon, lat=lat, dec=dec, speed_lon=sample.speed_longitude)

    def _resolve_position(
        self, name: str, conversion: TimeConversion
    ) -> BodyPosition:
        canonical = canonical_name(name)
        if not canonical:
            raise KeyError(name)
        try:
            code = self._body_id(canonical)
        except KeyError:
            code, derived = se_body_id_for(canonical, self._variant_config)
            if code < 0:
                raise KeyError(canonical)
            sample = self._adapter.sample(code, conversion)
            return self._position_from_sample(sample, derived=derived)
        sample = self._adapter.sample(code, conversion)
        return self._position_from_sample(sample)

    def positions_ecliptic(
        self, iso_utc: str, bodies: Iterable[str]
    ) -> dict[str, dict[str, float]]:

        conversion = self._time_conversion(iso_utc)
        out: dict[str, dict[str, float]] = {}
        issues: list[SupportIssue] = []
        for name in bodies:
            try:
                pos = self._resolve_position(name, conversion)
            except KeyError as exc:
                issue = SupportIssue(body=str(name), reason=str(exc))
                issues.append(issue)
                LOG.warning(
                    "body_unsupported: %s (%s)",
                    issue.body,
                    issue.reason,
                    extra={"event": "body_unsupported", "body": issue.body, "reason": issue.reason},
                )
                continue

            out[name] = {
                "lon": pos.lon,
                "decl": pos.dec,
                "speed_lon": pos.speed_lon,
            }
        self._last_support_issues = issues
        return out

    def position(self, body: str, ts_utc: str) -> BodyPosition:
        conversion = self._time_conversion(ts_utc)
        return self._resolve_position(body, conversion)


class SwissFallbackProvider:
    """Pure-python ephemeris fallback powered by PyMeeus."""

    _PLANET_MAP = {
        "sun": lambda epoch: _Sun.apparent_geocentric_position(epoch),
        "mercury": lambda epoch: _Mercury.geocentric_position(epoch),
        "venus": lambda epoch: _Venus.geocentric_position(epoch),
        "mars": lambda epoch: _Mars.geocentric_position(epoch),
        "jupiter": lambda epoch: _Jupiter.geocentric_position(epoch),
        "saturn": lambda epoch: _Saturn.geocentric_position(epoch),
        "uranus": lambda epoch: _Uranus.geocentric_position(epoch),
        "neptune": lambda epoch: _Neptune.geocentric_position(epoch),
        "pluto": lambda epoch: _Pluto.geocentric_position(epoch),
    }

    def __init__(self) -> None:
        if not _PYMEEUS_AVAILABLE:
            raise ImportError(
                "PyMeeus fallback unavailable; install pyswisseph instead"
            )

    @staticmethod
    def _to_epoch(iso_utc: str) -> Epoch:
        dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
        dt_utc = dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)
        hour = (
            dt_utc.hour
            + dt_utc.minute / 60.0
            + dt_utc.second / 3600.0
            + dt_utc.microsecond / 3.6e9
        )
        return Epoch(dt_utc.year, dt_utc.month, dt_utc.day, hour, utc=True)

    @staticmethod
    def _angle_to_deg(angle) -> float:
        if hasattr(angle, "to_positive"):
            angle = angle.to_positive()
        return float(angle) % 360.0

    @staticmethod
    def _lat_to_deg(angle) -> float:
        return float(angle)

    @classmethod
    def _coords_for(cls, body: str, epoch: Epoch) -> tuple[float, float]:
        body = body.lower()
        if body == "moon":
            lon, lat, *_ = _Moon.geocentric_ecliptical_pos(epoch)
        elif body == "sun":
            lon, lat, *_ = cls._PLANET_MAP[body](epoch)
        else:
            fn = cls._PLANET_MAP.get(body)
            if fn is None:
                raise KeyError(body)
            lon, lat, *_ = fn(epoch)
        lon_deg = cls._angle_to_deg(lon)
        lat_deg = cls._lat_to_deg(lat)
        return lon_deg, lat_deg

    @staticmethod
    def _wrap_deg(diff: float) -> float:
        while diff <= -180.0:
            diff += 360.0
        while diff > 180.0:
            diff -= 360.0
        return diff

    @classmethod
    def _lon_speed(cls, body: str, epoch: Epoch) -> float:
        delta = 1.0 / 24.0  # 1 hour in days
        epoch_minus = Epoch(epoch.jde() - delta)
        epoch_plus = Epoch(epoch.jde() + delta)
        lon_prev, _ = cls._coords_for(body, epoch_minus)
        lon_next, _ = cls._coords_for(body, epoch_plus)
        diff = cls._wrap_deg(lon_next - lon_prev)
        return diff / (2.0 * delta)

    def positions_ecliptic(
        self, iso_utc: str, bodies: Iterable[str]
    ) -> dict[str, dict[str, float]]:
        epoch = self._to_epoch(iso_utc)
        out: dict[str, dict[str, float]] = {}
        for name in bodies:
            try:
                lon_deg, lat_deg = self._coords_for(name, epoch)
                speed = self._lon_speed(name, epoch)
            except KeyError:
                continue
            position = BodyPosition(
                lon=lon_deg,
                lat=lat_deg,
                dec=lat_deg,
                speed_lon=speed,
            )
            out[name] = {
                "lon": position.lon,
                "decl": position.dec,
                "speed_lon": position.speed_lon,
            }
        return out

    def position(self, body: str, ts_utc: str) -> BodyPosition:
        coords = self.positions_ecliptic(ts_utc, [body])
        if body not in coords:
            raise KeyError(body)
        data = coords[body]
        return BodyPosition(
            lon=float(data["lon"]),
            lat=float(data["decl"]),
            dec=float(data["decl"]),
            speed_lon=float(data.get("speed_lon", 0.0)),
        )


def _register() -> None:
    if _HAS_SWE:
        metadata = _swiss_metadata(
            available=True,
            version=_package_version("pyswisseph"),
            description="Swiss Ephemeris bridge via pyswisseph.",
            supports_declination=True,
        )
        register_provider(
            "swiss",
            SwissProvider(),
            metadata=metadata,
            aliases=("swiss_ephemeris",),
        )
    elif _PYMEEUS_AVAILABLE:
        metadata = _swiss_metadata(
            available=True,
            version=_package_version("pymeeus"),
            description="PyMeeus fallback with limited accuracy for Swiss Ephemeris",
            supports_declination=False,
        )
        register_provider(
            "swiss",
            SwissFallbackProvider(),
            metadata=metadata,
            aliases=("swiss_ephemeris",),
        )
    else:
        metadata = _swiss_metadata(
            available=False,
            version=None,
            description="Swiss Ephemeris provider unavailable (pyswisseph missing).",
            supports_declination=False,
        )
        register_provider_metadata(metadata, overwrite=True)


_register()
