"""Swiss Ephemeris adapter with sidereal awareness and convenience helpers."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Optional

import swisseph as swe

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
    "BodyPosition",
    "EquatorialPosition",
    "HousePositions",
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
    """Container for house cusps and angles."""

    system: str
    cusps: tuple[float, ...]
    ascendant: float
    midheaven: float
    system_name: str | None = None
    fallback_from: Optional[str] = None

    def to_dict(self) -> Mapping[str, float | str | tuple[float, ...] | None]:
        payload: dict[str, float | str | tuple[float, ...] | None] = {
            "system": self.system,
            "cusps": self.cusps,
            "ascendant": self.ascendant,
            "midheaven": self.midheaven,
        }
        if self.system_name is not None:
            payload["system_name"] = self.system_name
        if self.fallback_from is not None:
            payload["fallback_from"] = self.fallback_from
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

        override_code, derived = self._variant_override(body_name)
        effective_code = override_code if override_code is not None else body_code

        self._apply_sidereal_mode()
        flags = self._calc_flags
        try:
            values, _ = swe.calc_ut(jd_ut, effective_code, flags)
        except Exception:
            flags = self._fallback_flags
            values, _ = swe.calc_ut(jd_ut, effective_code, flags)

        lon, lat, dist, speed_lon, speed_lat, speed_dist = values

        if derived:
            lon = (lon + 180.0) % 360.0
            lat = -lat
            speed_lat = -speed_lat

        equatorial = self.body_equatorial(jd_ut, effective_code)


        try:
            eq_values, _ = swe.calc_ut(jd_ut, effective_code, flags | swe.FLG_EQUATORIAL)
            _decl, _speed_decl = eq_values[1], eq_values[4]
        except Exception:
            _decl, _speed_decl = float("nan"), float("nan")


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

        requested_name, sys_code = self._resolve_house_system(system)
        code_token = sys_code.encode("ascii")
        fallback_from: str | None = None
        used_name = requested_name
        used_code = sys_code

        self._apply_sidereal_mode()
        try:
            cusps, angles = swe.houses_ex(jd_ut, latitude, longitude, code_token)
        except Exception:
            if requested_name != "whole_sign":
                try:
                    used_name, used_code = resolve_house_code("whole_sign")
                    code_token = used_code.encode("ascii")
                    cusps, angles = swe.houses_ex(
                        jd_ut, latitude, longitude, code_token
                    )
                    fallback_from = requested_name
                except Exception as exc:
                    raise RuntimeError(
                        f"House computation failed for system '{requested_name}'"
                    ) from exc
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

        system_label = used_code

        self._last_house_metadata = {
            "requested": requested_name,
            "used": used_name,
            "code": used_code,
        }
        if fallback_from:
            self._last_house_metadata["fallback"] = {
                "from": fallback_from,
                "to": used_name,
            }

        return HousePositions(
            system=system_label,
            cusps=tuple(cusps),
            ascendant=ascendant,
            midheaven=midheaven,
            system_name=used_name,
            fallback_from=fallback_from,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def is_sidereal(self) -> bool:
        return self._is_sidereal

    def _resolve_house_system(self, system: str | None) -> tuple[str, str]:
        """Return the canonical house system key and Swiss code."""

        candidate = system or self.chart_config.house_system
        name, code = resolve_house_code(candidate)
        return name, code
