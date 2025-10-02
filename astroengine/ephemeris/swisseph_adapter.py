"""Swiss Ephemeris adapter with sidereal awareness and convenience helpers."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Optional

import swisseph as swe

logger = logging.getLogger(__name__)

from .sidereal import (
    DEFAULT_SIDEREAL_AYANAMSHA,
    SUPPORTED_AYANAMSHAS,
    normalize_ayanamsha_name,
)
from .utils import get_se_ephe_path
from ..core.bodies import canonical_name

if TYPE_CHECKING:  # pragma: no cover - runtime import avoided for typing only

    from ..chart.config import ChartConfig

__all__ = [
    "swe_calc",
    "BodyPosition",
    "EquatorialPosition",
    "HousePositions",
    "SolarCycleEvents",
    "SwissEphemerisAdapter",
    "VariantConfig",
    "resolve_house_code",
]


HOUSE_CODE_BY_NAME: Mapping[str, str] = {
    "placidus": "P",
    "koch": "K",
    "regiomontanus": "R",
    "campanus": "C",
    "equal": "A",
    "whole_sign": "W",
    "porphyry": "O",
    "alcabitius": "B",
    "topocentric": "T",
    "morinus": "M",
    "meridian": "X",
    "vehlow_equal": "V",
    "sripati": "S",
    "equal_mc": "D",
}

HOUSE_ALIASES: Mapping[str, str] = {
    "ws": "whole_sign",
    "wholesign": "whole_sign",
    "w": "whole_sign",
    "axial": "meridian",
    "vehlow": "vehlow_equal",
    "sripathi": "sripati",
    "equalmc": "equal_mc",
}


def resolve_house_code(name_or_code: str) -> tuple[str, str]:
    """Return the canonical name and Swiss code for ``name_or_code``."""

    token = (name_or_code or "").strip()
    if not token:
        return "placidus", HOUSE_CODE_BY_NAME["placidus"]
    lowered = token.lower()
    # Direct Swiss code (single letter)
    if len(token) == 1 and token.upper() in {code for code in HOUSE_CODE_BY_NAME.values()}:
        code = token.upper()
        for name, mapped in HOUSE_CODE_BY_NAME.items():
            if mapped == code:
                return name, code
        return token.lower(), code
    canonical = HOUSE_ALIASES.get(lowered, lowered)
    if canonical in HOUSE_CODE_BY_NAME:
        return canonical, HOUSE_CODE_BY_NAME[canonical]
    raise ValueError(
        f"Unsupported house system '{name_or_code}'. Valid options: "
        f"{sorted(HOUSE_CODE_BY_NAME)}"
    )


_NODE_VARIANT_CODES = {
    "mean": int(getattr(swe, "MEAN_NODE", 10)),
    "true": int(getattr(swe, "TRUE_NODE", 11)),
}

_LILITH_VARIANT_CODES = {
    "mean": int(getattr(swe, "MEAN_APOG", 12)),
    "true": int(getattr(swe, "OSCU_APOG", 13)),
}


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
class SolarCycleEvents:
    """Sunrise, sunset, and transit metadata for a single day."""

    sunrise: datetime | None
    sunset: datetime | None
    next_sunrise: datetime | None
    transit: datetime | None
    provenance: Mapping[str, object]

    def to_dict(self) -> Mapping[str, object | None]:
        """Return a serialisable mapping of the solar cycle."""

        payload: dict[str, object | None] = {
            "sunrise": self.sunrise.isoformat() if self.sunrise else None,
            "sunset": self.sunset.isoformat() if self.sunset else None,
            "next_sunrise": self.next_sunrise.isoformat() if self.next_sunrise else None,
            "transit": self.transit.isoformat() if self.transit else None,
            "provenance": dict(self.provenance),
        }
        return payload


@dataclass(frozen=True)
class VariantConfig:
    """Per-run variant selection for lunar nodes and Black Moon Lilith."""

    nodes_variant: str = "mean"
    lilith_variant: str = "mean"

    def normalized_nodes(self) -> str:
        return "true" if self.nodes_variant.lower() == "true" else "mean"

    def normalized_lilith(self) -> str:
        return "true" if self.lilith_variant.lower() == "true" else "mean"


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
    _DEFAULT_VARIANTS: ClassVar[VariantConfig] = VariantConfig()
    _AYANAMSHA_MODES: ClassVar[dict[str, int]] = {
        "lahiri": swe.SIDM_LAHIRI,
        "fagan_bradley": swe.SIDM_FAGAN_BRADLEY,
        "krishnamurti": swe.SIDM_KRISHNAMURTI,
        "raman": swe.SIDM_RAMAN,
        "deluce": swe.SIDM_DELUCE,
        "yukteshwar": swe.SIDM_YUKTESHWAR,
        "galactic_center_0_sag": swe.SIDM_GALCENT_0SAG,
        "sassanian": swe.SIDM_SASSANIAN,
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
        nodes_variant: str | None = None,
        lilith_variant: str | None = None,
        chart_config: ChartConfig | None = None,
    ) -> None:

        if chart_config is None:
            from ..chart.config import ChartConfig as _ChartConfig

            config_kwargs: dict[str, object] = {}
            if zodiac is not None:
                config_kwargs["zodiac"] = zodiac
            if ayanamsha is not None:
                config_kwargs["ayanamsha"] = ayanamsha
            if house_system is not None:
                config_kwargs["house_system"] = house_system
            default_variants = type(self)._DEFAULT_VARIANTS
            if nodes_variant is not None:
                config_kwargs["nodes_variant"] = nodes_variant
            else:
                config_kwargs.setdefault("nodes_variant", default_variants.nodes_variant)
            if lilith_variant is not None:
                config_kwargs["lilith_variant"] = lilith_variant
            else:
                config_kwargs.setdefault(
                    "lilith_variant", default_variants.lilith_variant
                )
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
            if house_system is not None and house_system.lower() != chart_config.house_system:
                raise ValueError(
                    "house system override must match chart_config.house_system"
                )
            if nodes_variant is not None and nodes_variant.lower() != chart_config.nodes_variant:
                raise ValueError(
                    "nodes_variant override must match chart_config.nodes_variant"
                )
            if (
                lilith_variant is not None
                and lilith_variant.lower() != chart_config.lilith_variant
            ):
                raise ValueError(
                    "lilith_variant override must match chart_config.lilith_variant"
                )

        self.chart_config = chart_config
        self.zodiac = chart_config.zodiac
        self.ayanamsha = chart_config.ayanamsha
        self._is_sidereal = self.zodiac == "sidereal"
        self._sidereal_mode: int | None = (
            self._resolve_sidereal_mode(self.ayanamsha) if self._is_sidereal else None
        )
        self._variant_config = VariantConfig(
            nodes_variant=chart_config.nodes_variant,
            lilith_variant=chart_config.lilith_variant,
        )
        self._last_house_metadata: Optional[dict[str, object]] = None

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
        house_system: str | None = None,
        nodes_variant: str | None = None,
        lilith_variant: str | None = None,
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
            if house_system is not None:
                config_kwargs["house_system"] = house_system
            if nodes_variant is not None:
                config_kwargs["nodes_variant"] = nodes_variant
            if lilith_variant is not None:
                config_kwargs["lilith_variant"] = lilith_variant
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
            if house_system is not None and house_system.lower() != chart_config.house_system:
                raise ValueError(
                    "house system override must match chart_config.house_system"
                )
            if nodes_variant is not None and nodes_variant.lower() != chart_config.nodes_variant:
                raise ValueError(
                    "nodes_variant override must match chart_config.nodes_variant"
                )
            if (
                lilith_variant is not None
                and lilith_variant.lower() != chart_config.lilith_variant
            ):
                raise ValueError(
                    "lilith_variant override must match chart_config.lilith_variant"
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
        cls._DEFAULT_VARIANTS = VariantConfig(
            nodes_variant=chart.nodes_variant,
            lilith_variant=chart.lilith_variant,
        )

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

    @staticmethod
    def _datetime_from_jd_ut(jd_ut: float) -> datetime:
        """Convert a UT-based Julian day to a timezone-aware datetime."""

        year, month, day, ut_hours = swe.revjul(jd_ut, swe.GREG_CAL)
        base = datetime(year, month, day, tzinfo=UTC)
        total_seconds = ut_hours * 3600.0
        seconds = int(total_seconds)
        microseconds = int(round((total_seconds - seconds) * 1_000_000))
        if microseconds >= 1_000_000:
            seconds += 1
            microseconds -= 1_000_000
        return base + timedelta(seconds=seconds, microseconds=microseconds)

    def body_equatorial(self, jd_ut: float, body_code: int) -> EquatorialPosition:
        """Return right ascension/declination data for ``body_code``."""

        self._apply_sidereal_mode()

        flags = self._calc_flags | swe.FLG_EQUATORIAL
        try:
            xx, _, serr = swe_calc(
                jd_ut=jd_ut, planet_index=body_code, flag=flags
            )
        except RuntimeError:
            flags = self._fallback_flags | swe.FLG_EQUATORIAL
            xx, _, serr = swe_calc(
                jd_ut=jd_ut, planet_index=body_code, flag=flags
            )
        if serr:
            raise RuntimeError(serr)

        ra, decl, _, speed_ra, speed_decl, _ = xx
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

        override_code, derived = self._variant_override(body_name)
        effective_code = override_code if override_code is not None else body_code

        self._apply_sidereal_mode()
        flags = self._calc_flags
        try:
            xx, _, serr = swe_calc(
                jd_ut=jd_ut, planet_index=effective_code, flag=flags
            )
        except RuntimeError:
            flags = self._fallback_flags
            xx, _, serr = swe_calc(
                jd_ut=jd_ut, planet_index=effective_code, flag=flags
            )
        if serr:
            raise RuntimeError(serr)

        lon, lat, dist, speed_lon, speed_lat, speed_dist = xx

        if derived:
            lon = (lon + 180.0) % 360.0
            lat = -lat
            speed_lat = -speed_lat

        equatorial = self.body_equatorial(jd_ut, effective_code)


        try:
            eq_xx, _, serr = swe_calc(
                jd_ut=jd_ut,
                planet_index=effective_code,
                flag=flags | swe.FLG_EQUATORIAL,
            )
            _decl, _speed_decl = eq_xx[1], eq_xx[4]
        except RuntimeError:
            _decl, _speed_decl = float("nan"), float("nan")
        else:
            if serr:
                raise RuntimeError(serr)


        return BodyPosition(
            body=body_name or str(effective_code),
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

    def sunrise_sunset(
        self,
        moment: datetime,
        *,
        longitude: float,
        latitude: float,
        elevation_m: float = 0.0,
        refraction: bool = False,
        pressure_mbar: float | None = None,
        temperature_c: float | None = None,
        disc_center: bool = True,
    ) -> SolarCycleEvents:
        """Return sunrise, sunset, next sunrise, and transit for the Sun."""

        if moment.tzinfo is None:
            moment_utc = moment.replace(tzinfo=UTC)
        else:
            moment_utc = moment.astimezone(UTC)

        jd_ut = self.julian_day(moment_utc)
        geopos = (float(longitude), float(latitude), float(elevation_m))

        flags = swe.FLG_SWIEPH
        if disc_center:
            flags |= swe.BIT_DISC_CENTER
        pressure = 0.0
        temperature = 0.0
        if refraction:
            flags &= ~swe.BIT_NO_REFRACTION
            pressure = float(pressure_mbar if pressure_mbar is not None else 1013.25)
            temperature = float(temperature_c if temperature_c is not None else 15.0)
        else:
            flags |= swe.BIT_NO_REFRACTION
            if pressure_mbar is not None:
                pressure = float(pressure_mbar)
            if temperature_c is not None:
                temperature = float(temperature_c)

        def _event(start_jd: float, event_flag: int) -> float | None:
            result, tret = swe.rise_trans(
                start_jd,
                swe.SUN,
                event_flag,
                geopos,
                pressure,
                temperature,
                flags,
            )
            if result == 0:
                return tret[0]
            if result == -2:
                return None
            raise RuntimeError(
                {
                    "event": "swisseph_rise_trans_error",
                    "code": int(result),
                    "event_flag": int(event_flag),
                    "start_jd_ut": start_jd,
                    "geopos": {
                        "longitude_deg": geopos[0],
                        "latitude_deg": geopos[1],
                        "elevation_m": geopos[2],
                    },
                }
            )

        sunrise_jd = _event(jd_ut - 1.0, swe.CALC_RISE)
        sunset_jd = _event(
            (sunrise_jd if sunrise_jd is not None else jd_ut) + 0.01,
            swe.CALC_SET,
        )
        next_sunrise_jd = _event(
            (sunrise_jd if sunrise_jd is not None else jd_ut) + 0.51,
            swe.CALC_RISE,
        )
        transit_jd = _event(jd_ut - 0.5, swe.CALC_MTRANSIT)

        metadata: Mapping[str, object] = {
            "body": "sun",
            "body_code": int(swe.SUN),
            "source": "swisseph.rise_trans",
            "start_jd_ut": jd_ut,
            "moment_utc": moment_utc.isoformat(),
            "flags": int(flags),
            "refraction": refraction,
            "disc_center": disc_center,
            "pressure_mbar": pressure,
            "temperature_c": temperature,
            "geopos": {
                "longitude_deg": geopos[0],
                "latitude_deg": geopos[1],
                "elevation_m": geopos[2],
            },
        }

        return SolarCycleEvents(
            sunrise=self._datetime_from_jd_ut(sunrise_jd)
            if sunrise_jd is not None
            else None,
            sunset=self._datetime_from_jd_ut(sunset_jd)
            if sunset_jd is not None
            else None,
            next_sunrise=self._datetime_from_jd_ut(next_sunrise_jd)
            if next_sunrise_jd is not None
            else None,
            transit=self._datetime_from_jd_ut(transit_jd)
            if transit_jd is not None
            else None,
            provenance=metadata,
        )

    def _variant_override(self, body_name: str | None) -> tuple[Optional[int], bool]:
        if not body_name:
            return None, False
        original = (body_name or "").strip()
        lowered = original.lower()
        canonical = canonical_name(original)

        node_variant = self._variant_config.normalized_nodes()
        if lowered == "true_node":
            node_variant = "true"
        elif lowered == "mean_node":
            node_variant = "mean"
        if canonical in {"mean_node", "true_node"} or lowered in {"node", "north_node", "nn"}:
            return _NODE_VARIANT_CODES[node_variant], False
        if canonical == "south_node" or lowered in {"south_node", "sn"}:
            return _NODE_VARIANT_CODES[node_variant], True

        lilith_variant = self._variant_config.normalized_lilith()
        if lowered == "true_lilith":
            lilith_variant = "true"
        elif lowered == "mean_lilith":
            lilith_variant = "mean"
        if canonical in {"mean_lilith", "true_lilith"} or lowered in {"lilith", "black_moon_lilith"}:
            return _LILITH_VARIANT_CODES[lilith_variant], False

        return None, False

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


        if isinstance(used_code, (bytes, bytearray)):
            system_label = used_code.decode("ascii")
        else:
            system_label = str(used_code)
        used_name = str(used_key)

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

        self._last_house_metadata = {
            "house_system": {
                "requested": requested_key,
                "used": used_key,
                "code": system_label,
            }
        }
        if fallback_from is not None:
            fallback_info = {"from": fallback_from, "to": "whole_sign"}
            if fallback_reason:
                fallback_info["reason"] = fallback_reason
            self._last_house_metadata["fallback"] = fallback_info

        used_name = used_key

        return HousePositions(
            system=system_label,
            cusps=tuple(cusps),
            ascendant=ascendant,
            midheaven=midheaven,
            system_name=used_name,

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

    def _resolve_house_system(self, system: str | None) -> tuple[str, str]:
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

def swe_calc(
    *, jd_ut: float, planet_index: int, flag: int, use_tt: bool = False
) -> tuple[tuple[float, ...], int, str]:
    """Invoke Swiss Ephemeris core calculation with normalized arguments."""

    if swe is None:  # pragma: no cover - import guard retained for safety
        raise RuntimeError("Swiss ephemeris not available; install astroengine[ephem]")

    try:
        calc_fn = swe.calc if use_tt else swe.calc_ut
        xx, ret_flag = calc_fn(jd_ut, planet_index, flag)
    except Exception as exc:  # pragma: no cover - pass through detailed context
        serr = str(exc)
        raise RuntimeError(
            f"Swiss ephemeris failed for body index {planet_index} at JD {jd_ut}: {serr}"
        ) from exc

    # ``swe.calc_ut`` mirrors the C ``swe_calc`` contract returning the calculation flag
    # and populating an error string for negative return codes.  ``pyswisseph`` surfaces
    # the flag directly, but the error text is only visible via the raised exception.
    # Maintain the ``serr`` placeholder for downstream callers to keep the canonical
    # tuple structure available during future PySwisseph updates.
    if ret_flag < 0:
        serr = f"Swiss ephemeris returned error code {ret_flag}"
        raise RuntimeError(serr)
    serr = ""
    return tuple(xx), ret_flag, serr

