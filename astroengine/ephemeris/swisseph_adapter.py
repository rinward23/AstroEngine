"""Swiss Ephemeris adapter with sidereal awareness and convenience helpers."""

from __future__ import annotations

import logging
import os
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from functools import lru_cache
from typing import TYPE_CHECKING, ClassVar, Final, Optional
from types import ModuleType

logger = logging.getLogger(__name__)

from .cache import calc_ut_cached
from .swe import swe as _swe


def get_swisseph() -> ModuleType:
    """Return the cached :mod:`swisseph` module, raising if unavailable."""

    return _swe()

from .sidereal import (
    DEFAULT_SIDEREAL_AYANAMSHA,
    SUPPORTED_AYANAMSHAS,
    normalize_ayanamsha_name,
)
from .utils import get_se_ephe_path
from ..core.bodies import canonical_name
from ..observability import EPHEMERIS_SWE_CACHE_HIT_RATIO

if TYPE_CHECKING:  # pragma: no cover - runtime import avoided for typing only

    from ..chart.config import ChartConfig

__all__ = [
    "swe_calc",
    "BodyPosition",
    "EquatorialPosition",
    "HousePositions",

    "FixedStarPosition",
    "RiseTransitResult",

    "SwissEphemerisAdapter",
    "VariantConfig",
    "resolve_house_code",
    "get_swisseph",
]


_SWE_CALC_CACHE_SIZE: Final[int] = 4096


_SweCalcKey = tuple[float, int, int, bool]
_SweCalcValue = tuple[tuple[float, ...], int, str]


_swe_calc_cache: OrderedDict[_SweCalcKey, _SweCalcValue] = OrderedDict()
_swe_calc_hits: int = 0
_swe_calc_misses: int = 0


def _update_swe_cache_hit_ratio() -> None:
    """Update the exported hit ratio gauge for the swe_calc cache."""

    total = _swe_calc_hits + _swe_calc_misses
    if not total:
        EPHEMERIS_SWE_CACHE_HIT_RATIO.set(0.0)
        return
    EPHEMERIS_SWE_CACHE_HIT_RATIO.set(_swe_calc_hits / total)


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


@lru_cache(maxsize=1)
def _node_variant_codes() -> Mapping[str, int]:
    swe = _swe()
    return {
        "mean": int(getattr(swe, "MEAN_NODE", 10)),
        "true": int(getattr(swe, "TRUE_NODE", 11)),
    }


@lru_cache(maxsize=1)
def _lilith_variant_codes() -> Mapping[str, int]:
    swe = _swe()
    return {
        "mean": int(getattr(swe, "MEAN_APOG", 12)),
        "true": int(getattr(swe, "OSCU_APOG", 13)),
    }


@lru_cache(maxsize=1)
def _rise_transit_events() -> Mapping[str, int]:
    swe = _swe()
    return {
        "rise": swe.CALC_RISE,
        "set": swe.CALC_SET,
        "transit": swe.CALC_MTRANSIT,
        "upper_transit": swe.CALC_MTRANSIT,
        "meridian_transit": swe.CALC_MTRANSIT,
        "culmination": swe.CALC_MTRANSIT,
        "antitransit": swe.CALC_ITRANSIT,
        "lower_transit": swe.CALC_ITRANSIT,
    }


@dataclass(frozen=True, slots=True)
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


@dataclass(frozen=True, slots=True)
class EquatorialPosition:
    """Right ascension and declination details for a body."""

    right_ascension: float
    declination: float
    speed_ra: float
    speed_declination: float


@dataclass(frozen=True, slots=True)
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


@dataclass(frozen=True, slots=True)
class VariantConfig:
    """Per-run variant selection for lunar nodes and Black Moon Lilith."""

    nodes_variant: str = "mean"
    lilith_variant: str = "mean"

    def normalized_nodes(self) -> str:
        return "true" if self.nodes_variant.lower() == "true" else "mean"

    def normalized_lilith(self) -> str:
        return "true" if self.lilith_variant.lower() == "true" else "mean"


@dataclass(frozen=True, slots=True)
class HousePositions:
    """Container for house cusps, angles, and provenance metadata."""

    system: str
    cusps: tuple[float, ...]
    ascendant: float
    midheaven: float
    vertex: float | None = None
    antivertex: float | None = None
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
        if self.vertex is not None:
            payload["vertex"] = self.vertex
        if self.antivertex is not None:
            payload["antivertex"] = self.antivertex
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


@dataclass(frozen=True, slots=True)
class FixedStarPosition:
    """Computed coordinates for a fixed star via Swiss Ephemeris."""

    name: str
    julian_day: float
    longitude: float
    latitude: float
    distance_au: float
    speed_longitude: float
    speed_latitude: float
    speed_distance: float
    flags: int
    computation_flags: int


@dataclass(frozen=True, slots=True)
class RiseTransitResult:
    """Rise/set/transit metadata returned by Swiss Ephemeris."""

    body: str
    event: str
    julian_day: float | None
    datetime: datetime | None
    status: int
    rsmi: int
    flags: int


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
    _AYANAMSHA_MODES: ClassVar[dict[str, int] | None] = None


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

    @classmethod
    def _ayanamsha_modes(cls) -> dict[str, int]:
        if cls._AYANAMSHA_MODES is None:
            swe = _swe()
            cls._AYANAMSHA_MODES = {
                "lahiri": swe.SIDM_LAHIRI,
                "fagan_bradley": swe.SIDM_FAGAN_BRADLEY,
                "krishnamurti": swe.SIDM_KRISHNAMURTI,
                "raman": swe.SIDM_RAMAN,
                "deluce": swe.SIDM_DELUCE,
                "yukteshwar": swe.SIDM_YUKTESHWAR,
                "galactic_center_0_sag": swe.SIDM_GALCENT_0SAG,
                "sassanian": swe.SIDM_SASSANIAN,
            }
        return cls._AYANAMSHA_MODES


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

        swe = _swe()
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
            return cls._ayanamsha_modes()[ayanamsha]
        except KeyError as exc:  # pragma: no cover - guarded by validation upstream
            raise ValueError(f"Unsupported ayanamsha '{ayanamsha}'") from exc

    def _apply_sidereal_mode(self) -> None:
        if self._sidereal_mode is None:
            return
        swe = _swe()
        swe.set_sid_mode(self._sidereal_mode, 0.0, 0.0)

    def _configure_ephemeris_path(
        self, ephemeris_path: str | os.PathLike[str] | None
    ) -> str | None:
        swe = _swe()
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
            return type(self)._ayanamsha_modes()[key]
        except KeyError as exc:  # pragma: no cover - guarded by SUPPORTED_AYANAMSHAS
            raise ValueError(
                f"Swiss Ephemeris does not expose SIDM constant for '{key}'"
            ) from exc

    def _apply_sidereal_mode(self) -> None:
        if self._sidereal_mode is not None:
            swe = _swe()
            swe.set_sid_mode(self._sidereal_mode, 0.0, 0.0)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def set_ephemeris_path(self, ephemeris_path: str | os.PathLike[str]) -> str:
        """Explicitly set the ephemeris search path."""

        swe = _swe()
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
        swe = _swe()
        return swe.julday(moment_utc.year, moment_utc.month, moment_utc.day, hour)

    @staticmethod

    def from_julian_day(jd_ut: float) -> datetime:
        """Convert a Julian Day in UT back to a timezone-aware datetime."""

        swe = _swe()
        year, month, day, hour = swe.revjul(jd_ut, swe.GREG_CAL)
        base = datetime(year, month, day, tzinfo=UTC)
        seconds = hour * 3600.0
        return base + timedelta(seconds=seconds)


    def body_equatorial(self, jd_ut: float, body_code: int) -> EquatorialPosition:
        """Return right ascension/declination data for ``body_code``."""

        self._apply_sidereal_mode()

        swe = _swe()
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

        adapter_label = self.__class__.__name__
        start = perf_counter()
        override_code, derived = self._variant_override(body_name)
        effective_code = override_code if override_code is not None else body_code

        self._apply_sidereal_mode()
        swe = _swe()
        flags = self._calc_flags
        try:
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
        except Exception as exc:
            COMPUTE_ERRORS.labels(
                component="ephemeris_body",
                error=exc.__class__.__name__,
            ).inc()
            raise
        finally:
            duration = perf_counter() - start
            EPHEMERIS_BODY_COMPUTE_DURATION.labels(
                adapter=adapter_label,
                operation="single",
            ).observe(duration)

    def compute_bodies_many(
        self, jd_ut: float, bodies: Mapping[str, int]
    ) -> dict[str, BodyPosition]:
        """Return body positions for ``bodies`` using shared Swiss calls."""

        if not bodies:
            return {}

        self._apply_sidereal_mode()
        swe = _swe()
        calc_flags = self._calc_flags
        fallback_flags = self._fallback_flags
        equatorial_flag = swe.FLG_EQUATORIAL

        body_specs: list[tuple[str, int, bool]] = []
        unique_codes: set[int] = set()
        for name, raw_code in bodies.items():
            override_code, derived = self._variant_override(name)
            effective = int(override_code if override_code is not None else raw_code)
            body_specs.append((name, effective, derived))
            unique_codes.add(effective)

        def _compute_vector(code: int, primary: int, fallback: int) -> tuple[float, ...]:
            try:
                values, ret_flag = calc_ut_cached(jd_ut, code, primary)
            except Exception:
                values, ret_flag = calc_ut_cached(jd_ut, code, fallback)
            else:
                if ret_flag < 0 and fallback != primary:
                    values, ret_flag = calc_ut_cached(jd_ut, code, fallback)

            if ret_flag < 0:
                raise RuntimeError(f"Swiss ephemeris returned error code {ret_flag}")
            return tuple(values)

        ecliptic_data: dict[int, tuple[float, ...]] = {}
        equatorial_data: dict[int, tuple[float, ...]] = {}
        for code in unique_codes:
            ecliptic_data[code] = _compute_vector(code, calc_flags, fallback_flags)
            equatorial_data[code] = _compute_vector(
                code,
                calc_flags | equatorial_flag,
                fallback_flags | equatorial_flag,
            )

        positions: dict[str, BodyPosition] = {}
        for name, effective_code, derived in body_specs:
            lon, lat, dist, speed_lon, speed_lat, speed_dist = ecliptic_data[
                effective_code
            ]
            if derived:
                lon = (lon + 180.0) % 360.0
                lat = -lat
                speed_lat = -speed_lat

            eq_xx = equatorial_data[effective_code]
            _, decl, _, _, speed_decl, _ = eq_xx

            positions[name] = BodyPosition(
                body=name,
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

        return positions

    def body_positions(
        self, jd_ut: float, bodies: Mapping[str, int]
    ) -> dict[str, BodyPosition]:
        """Return positions for each body keyed by canonical name."""

        return self.compute_bodies_many(jd_ut, bodies)


    @staticmethod
    def planet_name(body_code: int) -> str:
        """Return the Swiss Ephemeris display name for ``body_code``."""

        swe = _swe()
        return swe.get_planet_name(body_code)

    def ayanamsa(self, jd_ut: float, *, true_longitude: bool = False) -> float:
        """Return the ayanamsa value for ``jd_ut`` in degrees."""

        self._apply_sidereal_mode()
        swe = _swe()
        if true_longitude:
            delta_t = swe.deltat(jd_ut)
            return swe.get_ayanamsa(jd_ut + delta_t)
        return swe.get_ayanamsa_ut(jd_ut)

    def ayanamsa_details(self, jd_ut: float) -> Mapping[str, float | int | None]:
        """Return ayanamsa metadata including Swiss mode flags."""

        self._apply_sidereal_mode()
        swe = _swe()
        if self._sidereal_mode is None:
            value = swe.get_ayanamsa_ut(jd_ut)
            return {"value": value, "mode": None, "flags": None}
        flags, value = swe.get_ayanamsa_ex_ut(jd_ut, self._sidereal_mode)
        return {"value": value, "mode": self._sidereal_mode, "flags": flags}

    def rise_transit(
        self,
        jd_ut: float,
        body: int | str,
        *,
        latitude: float,
        longitude: float,
        elevation: float = 0.0,
        event: str = "rise",
        pressure_hpa: float = 0.0,
        temperature_c: float = 0.0,
        flags: int | None = None,
        body_name: str | None = None,
    ) -> RiseTransitResult:
        """Compute the next rise/set/transit event for ``body`` after ``jd_ut``."""

        event_key = (event or "rise").lower()
        try:
            rsmi = _rise_transit_events()[event_key]
        except KeyError as exc:  # pragma: no cover - guarded by validation
            options = ", ".join(sorted(_rise_transit_events()))
            raise ValueError(f"Unknown rise/transit event '{event}'. Options: {options}") from exc

        override_code, _ = self._variant_override(body_name)
        effective_body: int | str = body
        if override_code is not None:
            effective_body = override_code

        label: str
        if body_name is not None:
            label = body_name
        elif isinstance(body, str):
            label = body
        elif isinstance(effective_body, int):
            try:
                label = self.planet_name(int(effective_body))
            except Exception:  # pragma: no cover - defensive
                label = str(effective_body)
        else:
            label = str(effective_body)

        flags_value = flags if flags is not None else self._calc_flags
        swe = _swe()
        if self._is_sidereal:
            flags_value |= swe.FLG_SIDEREAL

        self._apply_sidereal_mode()
        geopos = (float(longitude), float(latitude), float(elevation))
        status, tret = swe.rise_trans(
            jd_ut,
            effective_body,
            rsmi,
            geopos,
            pressure_hpa,
            temperature_c,
            flags_value,
        )

        event_jd = tret[0] if tret else None
        event_dt: datetime | None = None
        if status == 0 and event_jd is not None and event_jd != 0.0:
            event_dt = self.from_julian_day(event_jd)
        else:
            event_jd = None if status != 0 else event_jd

        return RiseTransitResult(
            body=label,
            event=event_key,
            julian_day=event_jd,
            datetime=event_dt,
            status=status,
            rsmi=rsmi,
            flags=flags_value,
        )

    def fixed_star(
        self,
        name: str,
        jd_ut: float,
        *,
        flags: int | None = None,
        use_ut: bool = True,
    ) -> FixedStarPosition:
        """Return longitude/latitude data for ``name`` at ``jd_ut``."""

        self._apply_sidereal_mode()
        flags_value = flags if flags is not None else self._calc_flags
        swe = _swe()
        if self._is_sidereal:
            flags_value |= swe.FLG_SIDEREAL

        if use_ut:
            values, resolved_name, retflags = swe.fixstar_ut(name, jd_ut, flags_value)
        else:
            values, resolved_name, retflags = swe.fixstar(name, jd_ut, flags_value)

        lon, lat, dist, speed_lon, speed_lat, speed_dist = values
        return FixedStarPosition(
            name=str(resolved_name).strip(),
            julian_day=jd_ut,
            longitude=lon % 360.0,
            latitude=lat,
            distance_au=dist,
            speed_longitude=speed_lon,
            speed_latitude=speed_lat,
            speed_distance=speed_dist,
            flags=retflags,
            computation_flags=flags_value,

        )

    def _variant_override(self, body_name: str | None) -> tuple[Optional[int], bool]:
        if not body_name:
            return None, False
        original = (body_name or "").strip()
        lowered = original.lower()
        canonical = canonical_name(original)

        node_variant = self._variant_config.normalized_nodes()
        if lowered in {"true_node", "true node"}:
            node_variant = "true"
        elif lowered in {"mean_node", "mean node"}:
            node_variant = "mean"
        elif lowered in {"true south node", "south node (true)"}:
            node_variant = "true"
        elif lowered in {"mean south node", "south node (mean)"}:
            node_variant = "mean"
        if canonical in {"mean_node", "true_node"} or lowered in {"node", "north_node", "nn"}:
            return _node_variant_codes()[node_variant], False
        if canonical == "south_node" or lowered in {"south_node", "sn", "mean south node", "true south node", "south node (true)", "south node (mean)"}:
            return _node_variant_codes()[node_variant], True

        lilith_variant = self._variant_config.normalized_lilith()
        if lowered in {"true_lilith", "true lilith"}:
            lilith_variant = "true"
        elif lowered in {"mean_lilith", "mean lilith"}:
            lilith_variant = "mean"
        if canonical in {"mean_lilith", "true_lilith"} or lowered in {"lilith", "black_moon_lilith", "black moon lilith", "black moon lilith (mean)", "black moon lilith (true)"}:
            return _lilith_variant_codes()[lilith_variant], False

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
            swe = _swe()
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
                swe = _swe()
                cusps, angles = swe.houses_ex(jd_ut, latitude, longitude, used_code)
            else:
                raise


        raw_vertex: float | None = None
        if len(angles) >= 4:
            raw_vertex = float(angles[3])

        if self._is_sidereal:
            ayan = self.ayanamsa(jd_ut)
            cusps = tuple((c - ayan) % 360.0 for c in cusps)
            ascendant = (angles[0] - ayan) % 360.0
            midheaven = (angles[1] - ayan) % 360.0
            vertex = ((raw_vertex - ayan) % 360.0) if raw_vertex is not None else None
        else:
            ascendant = angles[0]
            midheaven = angles[1]
            vertex = (raw_vertex % 360.0) if raw_vertex is not None else None

        antivertex = ((vertex + 180.0) % 360.0) if vertex is not None else None


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
            vertex=vertex,
            antivertex=antivertex,
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

    global _swe_calc_hits, _swe_calc_misses

    swe = _swe()

    cache_key: _SweCalcKey | None
    if _SWE_CALC_CACHE_SIZE > 0:
        cache_key = (jd_ut, planet_index, flag, use_tt)
        try:
            cached = _swe_calc_cache[cache_key]
        except KeyError:
            cached = None
        else:
            _swe_calc_hits += 1
            _swe_calc_cache.move_to_end(cache_key)
            _update_swe_cache_hit_ratio()
            return cached
    else:
        cache_key = None

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
    result: _SweCalcValue = (tuple(xx), ret_flag, serr)

    if cache_key is not None:
        _swe_calc_misses += 1
        _swe_calc_cache[cache_key] = result
        _swe_calc_cache.move_to_end(cache_key)
        if len(_swe_calc_cache) > _SWE_CALC_CACHE_SIZE:
            _swe_calc_cache.popitem(last=False)
        _update_swe_cache_hit_ratio()

    return result

