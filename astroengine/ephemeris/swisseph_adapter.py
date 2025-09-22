from __future__ import annotations

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar, Optional, TYPE_CHECKING

import swisseph as swe

from .sidereal import (
    DEFAULT_SIDEREAL_AYANAMSHA,
    SUPPORTED_AYANAMSHAS,
    normalize_ayanamsha_name,
)
from .utils import get_se_ephe_path

if TYPE_CHECKING:  # pragma: no cover - avoid runtime import cycle
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

    _DEFAULT_PATHS = (
        Path("/usr/share/sweph"),
        Path("/usr/share/libswisseph"),
        Path.home() / ".sweph",
    )
    _DEFAULT_ZODIAC: ClassVar[str] = "tropical"
    _DEFAULT_AYANAMSHA: ClassVar[str | None] = DEFAULT_SIDEREAL_AYANAMSHA
    _DEFAULT_ADAPTER: ClassVar[Optional["SwissEphemerisAdapter"]] = None
    _AYANAMSHA_MODES: ClassVar[dict[str, int]] = {
        "lahiri": swe.SIDM_LAHIRI,
        "fagan_bradley": swe.SIDM_FAGAN_BRADLEY,
        "krishnamurti": swe.SIDM_KRISHNAMURTI,
        "raman": swe.SIDM_RAMAN,
        "deluce": swe.SIDM_DELUCE,
    }
    _HOUSE_SYSTEM_CODES: ClassVar[dict[str, bytes]] = {
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
        zodiac: str | None = None,
        ayanamsha: str | None = None,
        chart_config: ChartConfig | None = None,
    ) -> None:
        if chart_config is not None:
            zodiac = chart_config.zodiac
            ayanamsha = chart_config.ayanamsha

        zodiac_normalized = (zodiac or self._DEFAULT_ZODIAC).lower()
        if zodiac_normalized not in {"tropical", "sidereal"}:
            options = ", ".join(sorted({"tropical", "sidereal"}))
            raise ValueError(f"Unknown zodiac mode '{zodiac}'. Valid options: {options}")

        ayanamsha_normalized: str | None
        if zodiac_normalized == "sidereal":
            fallback = ayanamsha
            if fallback is None and chart_config is not None:
                fallback = chart_config.ayanamsha
            fallback = fallback or self._DEFAULT_AYANAMSHA or DEFAULT_SIDEREAL_AYANAMSHA
            ayanamsha_normalized = normalize_ayanamsha_name(fallback)
            if ayanamsha_normalized not in SUPPORTED_AYANAMSHAS:
                options = ", ".join(sorted(SUPPORTED_AYANAMSHAS))
                raise ValueError(
                    f"Unsupported ayanamsha '{fallback}'. Supported options: {options}"
                )
        else:
            ayanamsha_normalized = None

        if chart_config is not None:
            house_system = chart_config.house_system
        else:
            house_system = "placidus"

        self.zodiac = zodiac_normalized
        self.ayanamsha = ayanamsha_normalized
        self._house_system = house_system.lower()
        self._is_sidereal = zodiac_normalized == "sidereal"
        self._sidereal_mode: int | None = (
            self._resolve_sidereal_mode(ayanamsha_normalized) if self._is_sidereal else None
        )
        self._calc_flags = swe.FLG_SWIEPH | swe.FLG_SPEED
        self._fallback_flags = swe.FLG_MOSEPH | swe.FLG_SPEED
        if self._is_sidereal:
            self._calc_flags |= swe.FLG_SIDEREAL
            self._fallback_flags |= swe.FLG_SIDEREAL

        self.ephemeris_path = self._configure_ephemeris_path(ephemeris_path)
        if self._is_sidereal:
            self._apply_sidereal_mode()

    # ------------------------------------------------------------------
    # Class helpers
    # ------------------------------------------------------------------
    @classmethod
    def configure_defaults(
        cls,
        *,
        zodiac: str | None = None,
        ayanamsha: str | None = None,
        chart_config: ChartConfig | None = None,
    ) -> None:
        """Update default zodiac configuration for subsequently created adapters."""

        if chart_config is not None:
            zodiac = chart_config.zodiac
            ayanamsha = chart_config.ayanamsha

        if zodiac is not None:
            zodiac_normalized = zodiac.lower()
        else:
            zodiac_normalized = cls._DEFAULT_ZODIAC

        if zodiac_normalized not in {"tropical", "sidereal"}:
            options = ", ".join(sorted({"tropical", "sidereal"}))
            raise ValueError(f"Unknown zodiac mode '{zodiac}'. Valid options: {options}")

        cls._DEFAULT_ZODIAC = zodiac_normalized

        if zodiac_normalized == "sidereal":
            ayanamsha_value = ayanamsha or cls._DEFAULT_AYANAMSHA or DEFAULT_SIDEREAL_AYANAMSHA
            ayanamsha_normalized = normalize_ayanamsha_name(ayanamsha_value)
            if ayanamsha_normalized not in SUPPORTED_AYANAMSHAS:
                options = ", ".join(sorted(SUPPORTED_AYANAMSHAS))
                raise ValueError(
                    f"Unsupported ayanamsha '{ayanamsha_value}'. Supported options: {options}"
                )
            cls._DEFAULT_AYANAMSHA = ayanamsha_normalized
        else:
            cls._DEFAULT_AYANAMSHA = None

        cls._DEFAULT_ADAPTER = None

    @classmethod
    def get_default_adapter(cls) -> "SwissEphemerisAdapter":
        if cls._DEFAULT_ADAPTER is None:
            cls._DEFAULT_ADAPTER = cls()
        return cls._DEFAULT_ADAPTER

    @classmethod
    def from_chart_config(cls, config: ChartConfig) -> "SwissEphemerisAdapter":
        return cls(chart_config=config)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @classmethod
    def _resolve_sidereal_mode(cls, ayanamsha: str | None) -> int:
        assert ayanamsha is not None
        try:
            return cls._AYANAMSHA_MODES[ayanamsha]
        except KeyError as exc:  # pragma: no cover - guarded by validation upstream
            raise ValueError(f"Unsupported ayanamsha '{ayanamsha}'") from exc

    def _apply_sidereal_mode(self) -> None:
        if self._sidereal_mode is None:
            return
        swe.set_sid_mode(self._sidereal_mode, 0, 0)

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
            if candidate and candidate.exists():
                swe.set_ephe_path(str(candidate))
                return str(candidate)
        return None

    def _resolve_house_system(self, system: str | None) -> bytes:
        if system is None:
            key = self._house_system
            if len(key) == 1:
                return key.upper().encode("ascii")
        else:
            if len(system) == 1:
                return system.upper().encode("ascii")
            key = system.lower()
            code = self._HOUSE_SYSTEM_CODES.get(key)
            if code:
                return code
            raise ValueError(f"Unsupported house system '{system}'")

        code = self._HOUSE_SYSTEM_CODES.get(key)
        if code:
            return code
        raise ValueError(f"Unsupported house system '{key}'")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_ephemeris_path(self, ephemeris_path: str | os.PathLike[str]) -> str:
        """Explicitly set the ephemeris search path."""

        swe.set_ephe_path(str(ephemeris_path))
        self.ephemeris_path = str(ephemeris_path)
        return self.ephemeris_path

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
        self, jd_ut: float, body_code: int, body_name: str | None = None
    ) -> BodyPosition:
        """Compute longitude/latitude/speed data for a single body."""

        self._apply_sidereal_mode()

        flags = self._calc_flags
        try:
            values, _ = swe.calc_ut(jd_ut, body_code, flags)
        except Exception:
            flags = self._fallback_flags
            values, _ = swe.calc_ut(jd_ut, body_code, flags)

        lon, lat, dist, speed_lon, speed_lat, speed_dist = values

        try:
            eq_values, _ = swe.calc_ut(jd_ut, body_code, flags | swe.FLG_EQUATORIAL)
            decl, speed_decl = eq_values[1], eq_values[4]
        except Exception:
            decl, speed_decl = float("nan"), float("nan")

        lon = lon % 360.0

        return BodyPosition(
            body=body_name or str(body_code),
            julian_day=jd_ut,
            longitude=lon,
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
            name: self.body_position(jd_ut, code, body_name=name) for name, code in bodies.items()
        }

    def houses(
        self,
        jd_ut: float,
        latitude: float,
        longitude: float,
        system: str | None = None,
    ) -> HousePositions:
        """Compute house cusps for a given location."""

        sys_code = self._resolve_house_system(system)
        self._apply_sidereal_mode()

        cusps, angles = swe.houses_ex(jd_ut, latitude, longitude, sys_code)

        if self._is_sidereal:
            ayan = swe.get_ayanamsa_ut(jd_ut)
            cusps = [(c - ayan) % 360.0 for c in cusps]
            ascendant = (angles[0] - ayan) % 360.0
            midheaven = (angles[1] - ayan) % 360.0
        else:
            ascendant = angles[0]
            midheaven = angles[1]

        return HousePositions(
            system=sys_code.decode("ascii"),
            cusps=tuple(cusps),
            ascendant=ascendant,
            midheaven=midheaven,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def is_sidereal(self) -> bool:
        return self._is_sidereal

