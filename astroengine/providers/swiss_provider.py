"""Swiss ephemeris provider integrating the :class:`SwissEphemerisAdapter`."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Iterable

from astroengine.canonical import BodyPosition
from astroengine.chart.config import ChartConfig
from astroengine.core.time import to_tt
from astroengine.ephemeris import ObserverLocation, TimeScaleContext, SwissEphemerisAdapter

try:  # pragma: no cover - optional dependency guard
    import swisseph as swe
except Exception:  # pragma: no cover
    swe = None

try:  # pragma: no cover - runtime fallback support
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

__all__ = ["SwissProvider"]

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
    """Ephemeris provider backed by :class:`SwissEphemerisAdapter`."""

    def __init__(self) -> None:
        if swe is None:
            raise ImportError("pyswisseph is not installed")
        self._chart_config = ChartConfig()
        self._topocentric = False
        self._observer: ObserverLocation | None = None
        self._time_scale = TimeScaleContext()
        self._adapter = self._create_adapter()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _create_adapter(self) -> SwissEphemerisAdapter:
        return SwissEphemerisAdapter(
            chart_config=self._chart_config,
            topocentric=self._topocentric,
            observer=self._observer,
            time_scale=self._time_scale,
        )

    @staticmethod
    def _normalize_iso(iso_utc: str) -> datetime:
        dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    def _reconfigure_chart(
        self,
        *,
        zodiac: str | None = None,
        ayanamsha: str | None = None,
        house_system: str | None = None,
    ) -> None:
        current = self._chart_config
        zodiac_target = (zodiac or current.zodiac).lower()
        house_target = house_system or current.house_system
        ayan_target: str | None = None
        if zodiac_target == "sidereal":
            ayan_target = ayanamsha or current.ayanamsha
        elif current.zodiac == "sidereal" and zodiac is None:
            ayan_target = ayanamsha or current.ayanamsha

        data = {"zodiac": zodiac_target, "house_system": house_target}
        if ayan_target is not None:
            data["ayanamsha"] = ayan_target
        self._chart_config = ChartConfig(**data)

    def _body_id(self, name: str) -> int:
        key = name.lower()
        value = _BODY_IDS.get(key)
        if value is None:
            raise KeyError(f"Unknown or unsupported body '{name}'")
        return int(value)

    def _refresh_adapter(self) -> None:
        self._adapter = self._create_adapter()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def configure(
        self,
        *,
        topocentric: bool | None = None,
        observer: ObserverLocation | None = None,
        sidereal: bool | None = None,
        ayanamsha: str | None = None,
        house_system: str | None = None,
        time_scale: TimeScaleContext | None = None,
    ) -> None:
        """Update ephemeris configuration used by the provider."""

        if topocentric is not None:
            if topocentric and observer is None and self._observer is None:
                raise ValueError("topocentric mode requires an observer location")
            self._topocentric = topocentric
            if not topocentric:
                self._observer = None
        if observer is not None:
            self._observer = observer
            if topocentric is None:
                self._topocentric = True
        if sidereal is not None:
            zodiac = "sidereal" if sidereal else "tropical"
        else:
            zodiac = None
        if time_scale is not None:
            self._time_scale = time_scale
        self._reconfigure_chart(
            zodiac=zodiac,
            ayanamsha=ayanamsha,
            house_system=house_system,
        )
        self._refresh_adapter()

    def positions_ecliptic(
        self, iso_utc: str, bodies: Iterable[str]
    ) -> Dict[str, Dict[str, float]]:
        conversion = to_tt(self._normalize_iso(iso_utc))
        jd_ut = conversion.jd_utc
        results: Dict[str, Dict[str, float]] = {}
        for name in bodies:
            try:
                body_id = self._body_id(name)
            except KeyError:
                continue
            position = self._adapter.body_position(jd_ut, body_id, body_name=name)
            results[name] = {
                "lon": position.longitude % 360.0,
                "decl": position.declination,
                "speed_lon": position.speed_longitude,
            }
        return results

    def position(self, body: str, ts_utc: str) -> BodyPosition:
        conversion = to_tt(self._normalize_iso(ts_utc))
        body_id = self._body_id(body)
        position = self._adapter.body_position(conversion.jd_utc, body_id, body_name=body)
        return BodyPosition(
            lon=position.longitude % 360.0,
            lat=position.latitude,
            dec=position.declination,
            speed_lon=position.speed_longitude,
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
