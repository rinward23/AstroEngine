from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable

from astroengine.canonical import BodyPosition
from astroengine.chart.config import ChartConfig
from astroengine.ephemeris import SwissEphemerisAdapter
from astroengine.ephemeris.utils import get_se_ephe_path

try:  # pragma: no cover - optional dependency
    import swisseph as swe  # type: ignore
except Exception:  # pragma: no cover
    swe = None  # type: ignore

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
    ) = (None,) * 10  # type: ignore[assignment]
    _PYMEEUS_AVAILABLE = False

from . import register_provider

_BODY_IDS = {
    "sun": swe.SUN if swe is not None else None,
    "moon": swe.MOON if swe is not None else None,
    "mercury": swe.MERCURY if swe is not None else None,
    "venus": swe.VENUS if swe is not None else None,
    "mars": swe.MARS if swe is not None else None,
    "jupiter": swe.JUPITER if swe is not None else None,
    "saturn": swe.SATURN if swe is not None else None,
    "uranus": swe.URANUS if swe is not None else None,
    "neptune": swe.NEPTUNE if swe is not None else None,
    "pluto": swe.PLUTO if swe is not None else None,
}


class SwissProvider:
    """Primary Swiss ephemeris-backed provider registered under ``"swiss"``."""

    def __init__(self) -> None:
        if swe is None:
            raise ImportError("pyswisseph is not installed")
        ephe_path = get_se_ephe_path()
        if ephe_path:
            swe.set_ephe_path(ephe_path)
        self._ephemeris_path = str(ephe_path) if ephe_path else None
        self._chart_config = ChartConfig()
        self._topocentric: bool | None = None
        self._observer: Any | None = None
        self._time_scale: Any | None = None
        self._adapter = SwissEphemerisAdapter(
            ephemeris_path=self._ephemeris_path,
            chart_config=self._chart_config,
        )

    def configure(
        self,
        *,
        sidereal: bool | None = None,
        ayanamsha: str | None = None,
        house_system: str | None = None,
        topocentric: bool | None = None,
        observer: Any | None = None,
        time_scale: Any | None = None,
        **_: Any,
    ) -> None:
        """Update zodiac configuration consumed by the provider."""

        config_kwargs = {
            "zodiac": self._chart_config.zodiac,
            "ayanamsha": self._chart_config.ayanamsha,
            "house_system": self._chart_config.house_system,
        }

        # Preserve extra configuration flags so repeated invocations keep the
        # previously requested context even if the current adapter does not yet
        # consume them directly.
        if topocentric is not None:
            config_kwargs["topocentric"] = topocentric
        if observer is not None:
            config_kwargs["observer"] = observer
        if time_scale is not None:
            config_kwargs["time_scale"] = time_scale

        if house_system is not None:
            config_kwargs["house_system"] = house_system

        if sidereal is not None:
            config_kwargs["zodiac"] = "sidereal" if sidereal else "tropical"
            if not sidereal:
                config_kwargs["ayanamsha"] = None

        if ayanamsha is not None:
            config_kwargs["ayanamsha"] = ayanamsha
            if config_kwargs.get("zodiac") != "sidereal":
                config_kwargs["zodiac"] = "sidereal"

        # ChartConfig does not accept these supplemental keys; strip them from
        # the initializer while retaining their values on the provider instance
        # so future adapter enhancements can honour the requested context.
        preserved_flags = {
            "topocentric": config_kwargs.pop("topocentric", None),
            "observer": config_kwargs.pop("observer", None),
            "time_scale": config_kwargs.pop("time_scale", None),
        }

        self._chart_config = ChartConfig(**config_kwargs)
        topocentric_value = (
            preserved_flags["topocentric"]
            if preserved_flags["topocentric"] is not None
            else self._topocentric
        )
        observer_value = (
            preserved_flags["observer"]
            if preserved_flags["observer"] is not None
            else self._observer
        )
        time_scale_value = (
            preserved_flags["time_scale"]
            if preserved_flags["time_scale"] is not None
            else self._time_scale
        )

        self._topocentric = topocentric_value
        self._observer = observer_value
        self._time_scale = time_scale_value
        self._adapter = SwissEphemerisAdapter(
            ephemeris_path=self._ephemeris_path,
            chart_config=self._chart_config,
        )

    @staticmethod
    def _normalize_iso(iso_utc: str) -> datetime:
        dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    def _julian_day(self, iso_utc: str) -> float:
        dt_utc = self._normalize_iso(iso_utc)
        return self._adapter.julian_day(dt_utc)

    def _body_id(self, name: str) -> int:
        code = _BODY_IDS.get(name.lower())
        if code is None:
            raise KeyError(name)
        return int(code)

    def positions_ecliptic(
        self, iso_utc: str, bodies: Iterable[str]
    ) -> Dict[str, Dict[str, float]]:
        if swe is None:
            raise RuntimeError("Swiss ephemeris not available; install astroengine[ephem]")

        jd_ut = self._julian_day(iso_utc)
        out: Dict[str, Dict[str, float]] = {}
        for name in bodies:
            try:
                body_code = self._body_id(name)
            except KeyError:
                continue
            pos = self._adapter.body_position(jd_ut, body_code, body_name=name)
            out[name] = {
                "lon": pos.longitude,
                "decl": pos.declination,
                "speed_lon": pos.speed_longitude,
            }
        return out

    def position(self, body: str, ts_utc: str) -> BodyPosition:
        jd_ut = self._julian_day(ts_utc)
        body_code = self._body_id(body)
        pos = self._adapter.body_position(jd_ut, body_code, body_name=body)
        return BodyPosition(
            lon=pos.longitude,
            lat=pos.latitude,
            dec=pos.declination,
            speed_lon=pos.speed_longitude,
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
            raise ImportError("PyMeeus fallback unavailable; install pyswisseph instead")

    @staticmethod
    def _to_epoch(iso_utc: str) -> "Epoch":
        dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
        dt_utc = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        hour = (
            dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0 + dt_utc.microsecond / 3.6e9
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
    def _coords_for(cls, body: str, epoch: "Epoch") -> tuple[float, float]:
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
    def _lon_speed(cls, body: str, epoch: "Epoch") -> float:
        delta = 1.0 / 24.0  # 1 hour in days
        epoch_minus = Epoch(epoch.jde() - delta)
        epoch_plus = Epoch(epoch.jde() + delta)
        lon_prev, _ = cls._coords_for(body, epoch_minus)
        lon_next, _ = cls._coords_for(body, epoch_plus)
        diff = cls._wrap_deg(lon_next - lon_prev)
        return diff / (2.0 * delta)

    def positions_ecliptic(
        self, iso_utc: str, bodies: Iterable[str]
    ) -> Dict[str, Dict[str, float]]:
        epoch = self._to_epoch(iso_utc)
        out: Dict[str, Dict[str, float]] = {}
        for name in bodies:
            try:
                lon_deg, lat_deg = self._coords_for(name, epoch)
                speed = self._lon_speed(name, epoch)
            except KeyError:
                continue
            out[name] = {"lon": lon_deg % 360.0, "decl": lat_deg, "speed_lon": speed}
        return out

    def position(self, body: str, ts_utc: str) -> BodyPosition:
        epoch = self._to_epoch(ts_utc)
        lon_deg, lat_deg = self._coords_for(body, epoch)
        speed = self._lon_speed(body, epoch)
        return BodyPosition(lon=lon_deg % 360.0, lat=lat_deg, dec=lat_deg, speed_lon=speed)


def _register() -> None:
    if swe is not None:
        register_provider("swiss", SwissProvider())
    elif _PYMEEUS_AVAILABLE:
        register_provider("swiss", SwissFallbackProvider())


_register()
# >>> AUTO-GEN END: AE Swiss Provider v1.0
