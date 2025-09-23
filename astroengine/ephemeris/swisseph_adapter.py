"""Swiss Ephemeris wrapper exposing deterministic helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, ClassVar, Mapping, Optional, TYPE_CHECKING

import swisseph as swe

from .adapter import ObserverLocation, TimeScaleContext
from .sidereal import (
    DEFAULT_SIDEREAL_AYANAMSHA,
    SUPPORTED_AYANAMSHAS,
    normalize_ayanamsha_name,
)
from .utils import get_se_ephe_path

if TYPE_CHECKING:
    from ..chart.config import ChartConfig

__all__ = ["BodyPosition", "HousePositions", "SwissEphemerisAdapter"]


@dataclass(frozen=True)
class BodyPosition:
    """Structured ephemeris output for a single body."""

    body: str
    julian_day: float
    longitude: float
    latitude: float
    distance_au: float
    speed_longitude: float
    speed_latitude: float
    speed_distance: float
    declination: float
    speed_declination: float

    def to_dict(self) -> Mapping[str, float]:
        return {
            "body": self.body,
            "julian_day": self.julian_day,
            "longitude": self.longitude,
            "latitude": self.latitude,
            "distance_au": self.distance_au,
            "speed_longitude": self.speed_longitude,
            "speed_latitude": self.speed_latitude,
            "speed_distance": self.speed_distance,
            "declination": self.declination,
            "speed_declination": self.speed_declination,
        }


@dataclass(frozen=True)
class HousePositions:
    """Container for house cusps and angles."""

    system: str
    cusps: tuple[float, ...]
    ascendant: float
    midheaven: float

    def to_dict(self) -> Mapping[str, float | tuple[float, ...]]:
        return {
            "system": self.system,
            "cusps": self.cusps,
            "ascendant": self.ascendant,
            "midheaven": self.midheaven,
        }


class SwissEphemerisAdapter:
    """High-level adapter around :mod:`pyswisseph` with sidereal support."""

    _DEFAULT_PATHS: ClassVar[tuple[Path, ...]] = (
        Path("/usr/share/sweph"),
        Path("/usr/share/libswisseph"),
        Path.home() / ".sweph",
    )
    _DEFAULT_CONFIG: ClassVar["ChartConfig | None"] = None
    _DEFAULT_ADAPTER: ClassVar[Optional["SwissEphemerisAdapter"]] = None

    _AYANAMSHA_MODES: ClassVar[dict[str, int]] = {
        "lahiri": swe.SIDM_LAHIRI,
        "fagan_bradley": swe.SIDM_FAGAN_BRADLEY,
        "krishnamurti": swe.SIDM_KRISHNAMURTI,
        "raman": swe.SIDM_RAMAN,
        "deluce": swe.SIDM_DELUCE,
    }

    _HOUSE_SYSTEM_CODES: ClassVar[Mapping[str, bytes]] = {
        "placidus": b"P",
        "koch": b"K",
        "whole_sign": b"W",
        "equal": b"E",
        "porphyry": b"O",
    }

    def __init__(
        self,
        ephemeris_path: str | os.PathLike[str] | None = None,
        *,
        chart_config: ChartConfig | None = None,
        zodiac: str | None = None,
        ayanamsha: str | None = None,
        house_system: str | None = None,
        topocentric: bool = False,
        observer: ObserverLocation | None = None,
        time_scale: TimeScaleContext | None = None,
    ) -> None:
        config = self._resolve_config(
            chart_config=chart_config,
            zodiac=zodiac,
            ayanamsha=ayanamsha,
            house_system=house_system,
        )
        self.chart_config = config
        self.zodiac = config.zodiac
        self.ayanamsha = config.ayanamsha
        self.house_system = config.house_system
        self._topocentric = topocentric
        if self._topocentric and observer is None:
            raise ValueError("topocentric charts require an observer location")
        self._observer = observer
        self._time_scale = time_scale or TimeScaleContext()
        self._use_tt = self._time_scale.ephemeris_scale == "TT"
        self._is_sidereal = self.zodiac == "sidereal"
        self._sidereal_mode: int | None = (
            self._resolve_sidereal_mode(self.ayanamsha) if self._is_sidereal else None
        )
        self._calc_flags = swe.FLG_SWIEPH | swe.FLG_SPEED
        self._fallback_flags = swe.FLG_MOSEPH | swe.FLG_SPEED
        if self._is_sidereal:
            self._calc_flags |= swe.FLG_SIDEREAL
            self._fallback_flags |= swe.FLG_SIDEREAL
        if self._topocentric:
            self._calc_flags |= swe.FLG_TOPOCTR
            self._fallback_flags |= swe.FLG_TOPOCTR

        self.ephemeris_path = self._configure_ephemeris_path(ephemeris_path)
        self._configure_topocentric()
        if self._is_sidereal:
            self._apply_sidereal_mode()

    # ------------------------------------------------------------------
    # Class helpers
    # ------------------------------------------------------------------
    @classmethod
    def configure_defaults(
        cls,
        *,
        chart_config: "ChartConfig" | None = None,
        zodiac: str | None = None,
        ayanamsha: str | None = None,
        house_system: str | None = None,
    ) -> None:
        """Update default configuration for subsequently created adapters."""

        cls._DEFAULT_CONFIG = cls._resolve_config(
            chart_config=chart_config,
            zodiac=zodiac,
            ayanamsha=ayanamsha,
            house_system=house_system,
        )
        cls._DEFAULT_ADAPTER = None

    @classmethod
    def get_default_adapter(cls) -> "SwissEphemerisAdapter":
        if cls._DEFAULT_ADAPTER is None:
            cls._DEFAULT_ADAPTER = cls(chart_config=cls._default_chart_config())
        return cls._DEFAULT_ADAPTER

    @classmethod
    def from_chart_config(cls, config: ChartConfig) -> "SwissEphemerisAdapter":
        return cls(chart_config=config)

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------
    @staticmethod
    def julian_day(moment: datetime) -> float:
        """Return the Julian day for a timezone-aware :class:`datetime`."""

        if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
            raise ValueError("datetime must be timezone-aware in UTC or convertible to UTC")
        moment_utc = moment.astimezone(UTC)
        hour = (
            moment_utc.hour
            + moment_utc.minute / 60.0
            + moment_utc.second / 3600.0
            + moment_utc.microsecond / 3.6e9
        )
        return swe.julday(moment_utc.year, moment_utc.month, moment_utc.day, hour)

    def body_position(
        self, jd_ut: float, body_code: int, *, body_name: str | None = None
    ) -> BodyPosition:
        """Compute longitude/latitude/speed data for a single body."""

        self._configure_topocentric()
        self._apply_sidereal_mode()

        jd, calc = self._resolve_backend(jd_ut)
        flags = self._calc_flags
        try:
            values, _ = calc(jd, body_code, flags)
        except Exception:
            flags = self._fallback_flags
            values, _ = calc(jd, body_code, flags)

        lon, lat, dist, speed_lon, speed_lat, speed_dist = values

        try:
            eq_values, _ = calc(jd, body_code, flags | swe.FLG_EQUATORIAL)
            decl, speed_decl = eq_values[1], eq_values[4]
        except Exception:
            decl, speed_decl = float("nan"), float("nan")

        return BodyPosition(
            body=body_name or str(body_code),
            julian_day=jd_ut,
            longitude=lon % 360.0,
            latitude=lat,
            distance_au=dist,
            speed_longitude=speed_lon,
            speed_latitude=speed_lat,
            speed_distance=speed_dist,
            declination=decl,
            speed_declination=speed_decl,
        )

    def body_positions(self, jd_ut: float, bodies: Mapping[str, int]) -> dict[str, BodyPosition]:
        """Return positions for each body keyed by canonical name."""

        return {
            name: self.body_position(jd_ut, code, body_name=name)
            for name, code in bodies.items()
        }

    def houses(
        self,
        jd_ut: float,
        latitude: float,
        longitude: float,
        system: str | None = None,
    ) -> HousePositions:
        """Compute house cusps for a given location."""

        self._apply_sidereal_mode()
        sys_code = self._resolve_house_system(system)
        cusps_raw, angles = swe.houses_ex(jd_ut, latitude, longitude, sys_code)
        cusps = tuple(float(value) % 360.0 for value in list(cusps_raw)[1:13])
        ascendant = float(angles[0]) % 360.0
        midheaven = float(angles[1]) % 360.0

        if self._is_sidereal:
            ayan = swe.get_ayanamsa_ut(jd_ut)
            cusps = tuple((c - ayan) % 360.0 for c in cusps)
            ascendant = (ascendant - ayan) % 360.0
            midheaven = (midheaven - ayan) % 360.0

        resolved_code = sys_code.decode("ascii")
        return HousePositions(
            system=resolved_code,
            cusps=cusps,
            ascendant=ascendant,
            midheaven=midheaven,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def is_sidereal(self) -> bool:
        return self._is_sidereal

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @classmethod
    def _resolve_config(
        cls,
        *,
        chart_config: ChartConfig | None,
        zodiac: str | None,
        ayanamsha: str | None,
        house_system: str | None,
    ) -> ChartConfig:
        from ..chart.config import ChartConfig as _ChartConfig

        if chart_config is not None:
            return chart_config

        kwargs: dict[str, object] = {}
        if zodiac is not None:
            kwargs["zodiac"] = zodiac
        if ayanamsha is not None:
            kwargs["ayanamsha"] = ayanamsha
        if house_system is not None:
            kwargs["house_system"] = house_system
        if not kwargs:
            config = cls._DEFAULT_CONFIG
            if config is None:
                config = cls._default_chart_config()
            return config
        return _ChartConfig(**kwargs)

    @classmethod
    def _default_chart_config(cls) -> "ChartConfig":
        from ..chart.config import ChartConfig as _ChartConfig

        if cls._DEFAULT_CONFIG is None:
            cls._DEFAULT_CONFIG = _ChartConfig()
        return cls._DEFAULT_CONFIG

    def _apply_sidereal_mode(self) -> None:
        if self._sidereal_mode is None:
            return
        swe.set_sid_mode(self._sidereal_mode, 0.0, 0.0)

    def _configure_topocentric(self) -> None:
        if not self._topocentric:
            swe.set_topo(0.0, 0.0, 0.0)
            return
        assert self._observer is not None
        swe.set_topo(
            self._observer.longitude_deg,
            self._observer.latitude_deg,
            self._observer.elevation_m,
        )

    def _configure_ephemeris_path(
        self, ephemeris_path: str | os.PathLike[str] | None
    ) -> str | None:
        if ephemeris_path:
            swe.set_ephe_path(str(ephemeris_path))
            return str(ephemeris_path)

        env_path = get_se_ephe_path()
        if env_path:
            candidate = Path(env_path)
            if candidate.exists():
                swe.set_ephe_path(str(candidate))
                return str(candidate)

        for candidate in self._DEFAULT_PATHS:
            if candidate.exists():
                swe.set_ephe_path(str(candidate))
                return str(candidate)
        return None

    def set_ephemeris_path(self, ephemeris_path: str | os.PathLike[str]) -> str:
        """Explicitly set the ephemeris search path."""

        swe.set_ephe_path(str(ephemeris_path))
        self.ephemeris_path = str(ephemeris_path)
        return self.ephemeris_path

    def _resolve_backend(
        self, jd_ut: float
    ) -> tuple[float, Callable[[float, int, int], tuple[list[float], int]]]:
        """Return the Julian day and calc function honoring the configured time scale."""

        if self._use_tt:
            jd = jd_ut + swe.deltat(jd_ut)
            calc: Callable[[float, int, int], tuple[list[float], int]] = swe.calc
        else:
            jd = jd_ut
            calc = swe.calc_ut
        return jd, calc

    @classmethod
    def _resolve_sidereal_mode(cls, ayanamsha: str | None) -> int:
        if ayanamsha is None:
            ayanamsha = DEFAULT_SIDEREAL_AYANAMSHA
        normalized = normalize_ayanamsha_name(ayanamsha)
        if normalized not in SUPPORTED_AYANAMSHAS:
            options = ", ".join(sorted(SUPPORTED_AYANAMSHAS))
            raise ValueError(
                f"Unsupported ayanamsha '{ayanamsha}'. Supported options: {options}"
            )
        try:
            return cls._AYANAMSHA_MODES[normalized]
        except KeyError as exc:  # pragma: no cover - guarded upstream
            raise ValueError(f"Unsupported ayanamsha '{ayanamsha}'") from exc

    def _resolve_house_system(self, system: str | None) -> bytes:
        key = (system or self.house_system).lower()
        if len(key) == 1:
            return key.upper().encode("ascii")
        code = self._HOUSE_SYSTEM_CODES.get(key)
        if code is None:
            options = ", ".join(sorted(self._HOUSE_SYSTEM_CODES))
            raise ValueError(f"Unsupported house system '{system or self.house_system}'. Options: {options}")
        return code
