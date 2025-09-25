"""Swiss Ephemeris adapter with sidereal awareness and convenience helpers."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

import swisseph as swe

logger = logging.getLogger(__name__)

from .sidereal import (
    DEFAULT_SIDEREAL_AYANAMSHA,
    SUPPORTED_AYANAMSHAS,
    normalize_ayanamsha_name,
)
from .utils import get_se_ephe_path

if TYPE_CHECKING:  # pragma: no cover - runtime import avoided for typing only

    from ..chart.config import ChartConfig

__all__ = [
    "BodyPosition",
    "EquatorialPosition",
    "HousePositions",
    "SwissEphemerisAdapter",
]


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


@dataclass(frozen=True)
class EquatorialPosition:
    """Right ascension and declination details for a body."""

    right_ascension: float
    declination: float
    speed_ra: float
    speed_declination: float


@dataclass(frozen=True)
class HousePositions:
    """Container for house cusps, angles, and provenance metadata."""

    system: str
    cusps: tuple[float, ...]
    ascendant: float
    midheaven: float
    system_name: str | None = None
    requested_system: str | None = None
    fallback_from: str | None = None
    fallback_reason: str | None = None
    provenance: Mapping[str, object] | None = None

    def to_dict(self) -> Mapping[str, float | str | tuple[float, ...] | None | Mapping[str, object]]:
        payload: dict[str, float | str | tuple[float, ...] | None | Mapping[str, object]] = {
            "system": self.system,
            "cusps": self.cusps,
            "ascendant": self.ascendant,
            "midheaven": self.midheaven,
        }
        if self.system_name is not None:
            payload["system_name"] = self.system_name
        if self.requested_system is not None:
            payload["requested_system"] = self.requested_system
        if self.fallback_from is not None:
            payload["fallback_from"] = self.fallback_from
        if self.fallback_reason is not None:
            payload["fallback_reason"] = self.fallback_reason
        if self.provenance is not None:
            payload["provenance"] = dict(self.provenance)
        return payload


class SwissEphemerisAdapter:
    """High level wrapper around :mod:`pyswisseph` with sane defaults."""

    _DEFAULT_PATHS: ClassVar[tuple[Path, ...]] = (
        Path("/usr/share/sweph"),
        Path("/usr/share/libswisseph"),
        Path.home() / ".sweph",
    )
    _DEFAULT_ZODIAC: ClassVar[str] = "tropical"
    _DEFAULT_AYANAMSHA: ClassVar[str | None] = DEFAULT_SIDEREAL_AYANAMSHA
    _DEFAULT_ADAPTER: ClassVar[SwissEphemerisAdapter | None] = None
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
        "regiomontanus": b"R",
        "campanus": b"C",
        "equal": b"A",
        "whole_sign": b"W",
        "porphyry": b"O",
        "alcabitius": b"B",
        "topocentric": b"T",
        "morinus": b"M",
        "meridian": b"X",
        "vehlow_equal": b"V",
        "sripati": b"S",
        "equal_mc": b"D",
    }
    _HOUSE_SYSTEM_ALIASES: ClassVar[Mapping[str, str]] = {
        "ws": "whole_sign",
        "wholesign": "whole_sign",
        "whole": "whole_sign",
        "equalmc": "equal_mc",
        "equal_mc": "equal_mc",
        "vehlow": "vehlow_equal",
        "axial": "meridian",
        "meridian_axial": "meridian",
        "topo": "topocentric",
    }

    def __init__(
        self,
        ephemeris_path: str | os.PathLike[str] | None = None,
        *,
        zodiac: str | None = None,
        ayanamsha: str | None = None,
        house_system: str | None = None,
        chart_config: ChartConfig | None = None,
    ) -> None:

        if chart_config is None:
            from ..chart.config import ChartConfig as _ChartConfig

            config_kwargs: dict[str, object] = {}
            if zodiac is not None:
                config_kwargs["zodiac"] = zodiac
            if ayanamsha is not None:
                config_kwargs["ayanamsha"] = ayanamsha
            chart_config = _ChartConfig(**config_kwargs)
        else:
            if zodiac is not None and zodiac.lower() != chart_config.zodiac.lower():
                raise ValueError(
                    "zodiac override must match chart_config.zodiac when both are provided"
                )
            if ayanamsha is not None:
                if chart_config.zodiac.lower() != "sidereal":
                    raise ValueError(
                        "ayanamsha can only be specified for sidereal charts"
                    )
                desired = normalize_ayanamsha_name(ayanamsha)
                configured = normalize_ayanamsha_name(chart_config.ayanamsha or desired)
                if desired != configured:
                    raise ValueError(
                        "ayanamsha override must match chart_config.ayanamsha "
                        "when both are provided"
                    )

        self.chart_config = chart_config
        self.zodiac = chart_config.zodiac
        self.ayanamsha = chart_config.ayanamsha
        self._is_sidereal = self.zodiac == "sidereal"
        self._sidereal_mode: int | None = (
            self._resolve_sidereal_mode(self.ayanamsha) if self._is_sidereal else None
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

        if chart_config is None:
            from ..chart.config import ChartConfig as _ChartConfig

            config_kwargs: dict[str, object] = {}
            if zodiac is not None:
                config_kwargs["zodiac"] = zodiac
            if ayanamsha is not None:
                config_kwargs["ayanamsha"] = ayanamsha
            chart = _ChartConfig(**config_kwargs)
        else:

            chart = chart_config
            if zodiac is not None and zodiac.lower() != chart_config.zodiac.lower():
                raise ValueError(
                    "zodiac override must match chart_config.zodiac when both are provided"
                )

            if ayanamsha is not None:
                if chart_config.zodiac.lower() != "sidereal":
                    raise ValueError(
                        "ayanamsha can only be specified for sidereal charts"
                    )
                desired = normalize_ayanamsha_name(ayanamsha)
                configured = normalize_ayanamsha_name(chart_config.ayanamsha or desired)
                if desired != configured:
                    raise ValueError(
                        "ayanamsha override must match chart_config.ayanamsha "
                        "when both are provided"
                    )

        zodiac_value = zodiac or chart.zodiac
        zodiac_normalized = (zodiac_value or cls._DEFAULT_ZODIAC).lower()
        if zodiac_normalized not in {"tropical", "sidereal"}:
            options = ", ".join(sorted({"tropical", "sidereal"}))
            raise ValueError(
                f"Unknown zodiac mode '{zodiac_value}'. Valid options: {options}"
            )
        cls._DEFAULT_ZODIAC = zodiac_normalized

        if zodiac_normalized == "sidereal":
            ayanamsha_value = (
                ayanamsha
                or chart.ayanamsha
                or cls._DEFAULT_AYANAMSHA
                or DEFAULT_SIDEREAL_AYANAMSHA
            )
            normalized = normalize_ayanamsha_name(ayanamsha_value)
            if normalized not in SUPPORTED_AYANAMSHAS:
                options = ", ".join(sorted(SUPPORTED_AYANAMSHAS))
                raise ValueError(
                    f"Unknown ayanamsha '{ayanamsha_value}'. Valid options: {options}"
                )
        else:
            normalized = chart.ayanamsha

        cls._DEFAULT_ZODIAC = chart.zodiac
        cls._DEFAULT_AYANAMSHA = normalized

        cls._DEFAULT_ADAPTER = None

    @classmethod
    def get_default_adapter(cls) -> SwissEphemerisAdapter:
        if cls._DEFAULT_ADAPTER is None:
            cls._DEFAULT_ADAPTER = cls()
        return cls._DEFAULT_ADAPTER

    @classmethod
    def from_chart_config(cls, config: ChartConfig) -> SwissEphemerisAdapter:
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
        swe.set_sid_mode(self._sidereal_mode, 0.0, 0.0)

    def _configure_ephemeris_path(
        self, ephemeris_path: str | os.PathLike[str] | None
    ) -> str | None:
        if ephemeris_path is not None:
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

    def _resolve_sidereal_mode(self, ayanamsha: str | None) -> int:
        if not ayanamsha:
            raise ValueError("Ayanamsha is required for sidereal mode")
        key = normalize_ayanamsha_name(ayanamsha)
        if key not in SUPPORTED_AYANAMSHAS:
            options = ", ".join(sorted(SUPPORTED_AYANAMSHAS))
            raise ValueError(
                f"Unsupported ayanamsha '{ayanamsha}'. Supported options: {options}"
            )
        try:
            return self._AYANAMSHA_MODES[key]
        except KeyError as exc:  # pragma: no cover - guarded by SUPPORTED_AYANAMSHAS
            raise ValueError(
                f"Swiss Ephemeris does not expose SIDM constant for '{key}'"
            ) from exc

    def _apply_sidereal_mode(self) -> None:
        if self._sidereal_mode is not None:
            swe.set_sid_mode(self._sidereal_mode, 0.0, 0.0)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def set_ephemeris_path(self, ephemeris_path: str | os.PathLike[str]) -> str:
        """Explicitly set the ephemeris search path."""

        swe.set_ephe_path(str(ephemeris_path))
        self.ephemeris_path = str(ephemeris_path)
        return self.ephemeris_path

    # ------------------------------------------------------------------
    # Core public API
    # ------------------------------------------------------------------
    @staticmethod
    def julian_day(moment: datetime) -> float:
        """Return the Julian day for a timezone-aware :class:`datetime`."""

        if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
            raise ValueError(
                "datetime must be timezone-aware in UTC or convertible to UTC"
            )
        moment_utc = moment.astimezone(UTC)
        hour = (
            moment_utc.hour
            + moment_utc.minute / 60.0
            + moment_utc.second / 3600.0
            + moment_utc.microsecond / 3.6e9
        )
        return swe.julday(moment_utc.year, moment_utc.month, moment_utc.day, hour)

    def body_equatorial(self, jd_ut: float, body_code: int) -> EquatorialPosition:
        """Return right ascension/declination data for ``body_code``."""

        self._apply_sidereal_mode()

        flags = self._calc_flags | swe.FLG_EQUATORIAL
        try:
            values, _ = swe.calc_ut(jd_ut, body_code, flags)
        except Exception:
            flags = self._fallback_flags | swe.FLG_EQUATORIAL
            values, _ = swe.calc_ut(jd_ut, body_code, flags)

        ra, decl, _, speed_ra, speed_decl, _ = values
        return EquatorialPosition(
            right_ascension=ra % 360.0,
            declination=decl,
            speed_ra=speed_ra,
            speed_declination=speed_decl,
        )

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

        equatorial = self.body_equatorial(jd_ut, body_code)


        try:
            eq_values, _ = swe.calc_ut(jd_ut, body_code, flags | swe.FLG_EQUATORIAL)
            _decl, _speed_decl = eq_values[1], eq_values[4]
        except Exception:
            _decl, _speed_decl = float("nan"), float("nan")


        return BodyPosition(
            body=body_name or str(body_code),
            julian_day=jd_ut,
            longitude=lon % 360.0,
            latitude=lat,
            distance_au=dist,
            speed_longitude=speed_lon,
            speed_latitude=speed_lat,
            speed_distance=speed_dist,
            declination=equatorial.declination,
            speed_declination=equatorial.speed_declination,
        )

    def body_positions(
        self, jd_ut: float, bodies: Mapping[str, int]
    ) -> dict[str, BodyPosition]:
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
        *,
        system: str | None = None,
    ) -> HousePositions:
        """Compute house cusps for a given location."""

        requested_key, requested_code = self._resolve_house_system(system)

        self._apply_sidereal_mode()

        used_key = requested_key
        used_code = requested_code
        fallback_from: str | None = None
        fallback_reason: str | None = None

        try:
            cusps, angles = swe.houses_ex(jd_ut, latitude, longitude, used_code)
        except Exception as exc:
            # Certain quadrant systems fail at extreme latitudes; fallback to Whole Sign.
            if used_key != "whole_sign":
                fallback_from = used_key
                fallback_reason = str(exc)
                used_key = "whole_sign"
                used_code = self._HOUSE_SYSTEM_CODES["whole_sign"]
                logger.warning(
                    {
                        "event": "house_system_fallback",
                        "from": fallback_from,
                        "to": "whole_sign",
                        "latitude": latitude,
                        "longitude": longitude,
                        "reason": fallback_reason,
                    }
                )
                cusps, angles = swe.houses_ex(jd_ut, latitude, longitude, used_code)
            else:
                raise

        if self._is_sidereal:
            ayan = swe.get_ayanamsa_ut(jd_ut)
            cusps = tuple((c - ayan) % 360.0 for c in cusps)
            ascendant = (angles[0] - ayan) % 360.0
            midheaven = (angles[1] - ayan) % 360.0
        else:
            ascendant = angles[0]
            midheaven = angles[1]

        if isinstance(used_code, bytes | bytearray):
            system_label = used_code.decode("ascii")
        else:
            system_label = str(used_code)

        provenance: dict[str, object] = {
            "house_system": {
                "requested": requested_key,
                "used": used_key,
                "code": system_label,
            }
        }
        if fallback_from is not None:
            fallback_info: dict[str, object] = {"from": fallback_from, "to": "whole_sign"}
            if fallback_reason:
                fallback_info["reason"] = fallback_reason
            provenance["house_fallback"] = fallback_info

        return HousePositions(
            system=system_label,
            cusps=tuple(cusps),
            ascendant=ascendant,
            midheaven=midheaven,
            system_name=used_key,
            requested_system=requested_key,
            fallback_from=fallback_from,
            fallback_reason=fallback_reason,
            provenance=provenance,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def is_sidereal(self) -> bool:
        return self._is_sidereal

    def _resolve_house_system(self, system: str | None) -> tuple[str, bytes]:
        """Return the canonical house system key and Swiss code."""

        if system is None:
            key = self.chart_config.house_system.lower()
        else:
            key = system.strip().lower()

        alias = self._HOUSE_SYSTEM_ALIASES.get(key, key)

        code = self._HOUSE_SYSTEM_CODES.get(alias)
        if code is not None:
            return alias, code

        if len(key) == 1:
            code = key.upper().encode("ascii")
            canonical = next(
                (
                    name
                    for name, candidate in self._HOUSE_SYSTEM_CODES.items()
                    if candidate == code
                ),
                key.lower(),
            )
            return canonical, code

        options = ", ".join(sorted(self._HOUSE_SYSTEM_CODES))
        raise ValueError(
            "Unsupported house system "
            f"'{system or self.chart_config.house_system}'. Valid options: {options}"
        )
