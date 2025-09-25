from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from datetime import UTC, datetime

from astroengine.canonical import BodyPosition
from astroengine.core.time import TimeConversion, to_tt
from astroengine.ephemeris import (
    EphemerisAdapter,
    EphemerisConfig,
    ObserverLocation,
    TimeScaleContext,
)
from astroengine.ephemeris.utils import get_se_ephe_path

try:
    import swisseph as swe  # pyswisseph imports the module name 'swisseph'
except Exception:  # pragma: no cover
    swe = None

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
except Exception:  # pragma: no cover
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

from . import register_provider

_BODY_IDS = {
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


class SwissProvider:
    def __init__(self) -> None:
        if swe is None:
            raise ImportError("pyswisseph is not installed")
        eph = get_se_ephe_path()
        if eph:
            swe.set_ephe_path(eph)
        self._config = EphemerisConfig(ephemeris_path=str(eph) if eph else None)
        self._adapter = EphemerisAdapter(self._config)

    def configure(
        self,
        *,
        topocentric: bool | None = None,
        observer: ObserverLocation | None = None,
        sidereal: bool | None = None,
        time_scale: TimeScaleContext | None = None,
    ) -> None:
        """Update ephemeris configuration used by the provider."""

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
        key = name.lower()
        if key not in _BODY_IDS:
            raise KeyError(key)
        return _BODY_IDS[key]

    def positions_ecliptic(
        self, iso_utc: str, bodies: Iterable[str]
    ) -> dict[str, dict[str, float]]:

        conversion = self._time_conversion(iso_utc)
        out: dict[str, dict[str, float]] = {}
        for name in bodies:
            try:
                body_id = self._body_id(name)
            except KeyError:
                continue

            sample = self._adapter.sample(body_id, conversion)
            out[name] = {
                "lon": sample.longitude % 360.0,
                "decl": sample.declination,
                "speed_lon": sample.speed_longitude,
            }
        return out

    def position(self, body: str, ts_utc: str) -> BodyPosition:
        sample = self._adapter.sample(
            self._body_id(body), self._time_conversion(ts_utc)
        )
        return BodyPosition(
            lon=sample.longitude % 360.0,
            lat=sample.latitude,
            dec=sample.declination,
            speed_lon=sample.speed_longitude,
        )


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
            out[name] = {"lon": lon_deg % 360.0, "decl": lat_deg, "speed_lon": speed}
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
    if swe is not None:
        register_provider("swiss", SwissProvider())
    elif _PYMEEUS_AVAILABLE:
        register_provider("swiss", SwissFallbackProvider())


_register()
# >>> AUTO-GEN END: AE Swiss Provider v1.0
