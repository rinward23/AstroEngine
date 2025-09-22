"""Swiss Ephemeris wrapper exposing deterministic helpers."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import swisseph as swe

from .utils import get_se_ephe_path

if TYPE_CHECKING:  # pragma: no cover - avoid circular import at runtime
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
    """High-level adapter around :mod:`pyswisseph`."""

    _DEFAULT_PATHS = (
        Path("/usr/share/sweph"),
        Path("/usr/share/libswisseph"),
        Path.home() / ".sweph",
    )

    _HOUSE_SYSTEM_CODES: Mapping[str, bytes] = {
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
        chart_config: "ChartConfig" | None = None,
    ) -> None:
        if chart_config is None:
            from ..chart.config import ChartConfig as _ChartConfig

            self.chart_config = _ChartConfig()
        else:
            self.chart_config = chart_config
        self._sidereal = self.chart_config.zodiac.lower() == "sidereal"
        self._sidereal_flag = swe.FLG_SIDEREAL if self._sidereal else 0
        self.ephemeris_path = self._configure_ephemeris_path(ephemeris_path)
        self._configure_sidereal_mode()

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

        flags = swe.FLG_SWIEPH | swe.FLG_SPEED | self._sidereal_flag
        try:
            values, _ = swe.calc_ut(jd_ut, body_code, flags)
        except Exception:
            flags = swe.FLG_MOSEPH | swe.FLG_SPEED | self._sidereal_flag
            values, _ = swe.calc_ut(jd_ut, body_code, flags)

        lon, lat, dist, speed_lon, speed_lat, speed_dist = values

        try:
            eq_values, _ = swe.calc_ut(
                jd_ut, body_code, flags | swe.FLG_EQUATORIAL
            )
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
        cusps, angles = swe.houses_ex(jd_ut, latitude, longitude, sys_code)
        return HousePositions(
            system=sys_code.decode("ascii"),
            cusps=tuple(cusps),
            ascendant=angles[0],
            midheaven=angles[1],
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _configure_sidereal_mode(self) -> None:
        if not self._sidereal:
            return

        ayanamsha_name = self.chart_config.ayanamsha or ""
        code = self._resolve_ayanamsha_code(ayanamsha_name)
        swe.set_sid_mode(code, 0.0, 0.0)

    def _resolve_ayanamsha_code(self, name: str) -> int:
        normalized = name.strip().lower().replace(" ", "_").replace("-", "_")
        if not normalized:
            raise ValueError("Ayanamsha name required for sidereal charts")

        mapping: dict[str, int] = {}
        for attr in dir(swe):
            if not attr.startswith("SIDM_"):
                continue
            value = getattr(swe, attr)
            if not isinstance(value, int):
                continue
            key = attr[5:].lower()
            mapping[key] = value
            mapping[key.replace("_", "")] = value

        direct = mapping.get(normalized)
        if direct is not None:
            return direct

        compact = normalized.replace("_", "")
        if compact in mapping:
            return mapping[compact]

        raise ValueError(f"Unknown ayanamsha '{name}'")

    def _resolve_house_system(self, system: str | None) -> bytes:
        if system is None:
            key = self.chart_config.house_system.lower()
            code = self._HOUSE_SYSTEM_CODES.get(key)
            if not code:
                raise ValueError(f"Unsupported house system '{self.chart_config.house_system}'")
            return code

        if len(system) == 1:
            return system.upper().encode("ascii")

        key = system.lower()
        code = self._HOUSE_SYSTEM_CODES.get(key)
        if code:
            return code

        raise ValueError(f"Unsupported house system '{system}'")
