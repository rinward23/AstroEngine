"""Sidereal ayanamsa helpers with Swiss Ephemeris backed presets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Final, Iterable, Iterator, Mapping

from ...ephemeris.sidereal import normalize_ayanamsha_name
from ...ephemeris.swisseph_adapter import SwissEphemerisAdapter, get_swisseph

__all__ = [
    "AyanamsaInfo",
    "AyanamsaPreset",
    "SIDEREAL_PRESETS",
    "PRIMARY_AYANAMSAS",
    "available_ayanamsas",
    "ayanamsa_metadata",
    "ayanamsa_value",
    "normalize_ayanamsa",
    "swe_ayanamsa",
]


class AyanamsaPreset(StrEnum):
    """Canonical ayanamsa presets supported by AstroEngine."""

    LAHIRI = "lahiri"
    KRISHNAMURTI = "krishnamurti"
    RAMAN = "raman"
    FAGAN_BRADLEY = "fagan_bradley"
    YUKTESHWAR = "yukteshwar"
    GALACTIC_CENTER_0_SAG = "galactic_center_0_sag"
    SASSANIAN = "sassanian"
    DELUCE = "deluce"


@dataclass(frozen=True)
class AyanamsaInfo:
    """Metadata returned for ayanamsa computations."""

    preset: AyanamsaPreset
    swe_mode: int
    label: str


class _LazySiderealPresets(Mapping[AyanamsaPreset, AyanamsaInfo]):
    """Lazy Swiss-backed ayanamsa metadata mapping."""

    _cache: Mapping[AyanamsaPreset, AyanamsaInfo] | None = None

    def _ensure(self) -> Mapping[AyanamsaPreset, AyanamsaInfo]:
        if self._cache is None:
            try:
                swe = get_swisseph()
            except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
                raise RuntimeError(
                    "Swiss Ephemeris (pyswisseph) is required for sidereal ayanamsa support."
                ) from exc
            mapping: dict[AyanamsaPreset, AyanamsaInfo] = {
                AyanamsaPreset.LAHIRI: AyanamsaInfo(
                    preset=AyanamsaPreset.LAHIRI,
                    swe_mode=int(swe.SIDM_LAHIRI),
                    label="Lahiri",
                ),
                AyanamsaPreset.KRISHNAMURTI: AyanamsaInfo(
                    preset=AyanamsaPreset.KRISHNAMURTI,
                    swe_mode=int(swe.SIDM_KRISHNAMURTI),
                    label="Krishnamurti",
                ),
                AyanamsaPreset.RAMAN: AyanamsaInfo(
                    preset=AyanamsaPreset.RAMAN,
                    swe_mode=int(swe.SIDM_RAMAN),
                    label="B. V. Raman",
                ),
                AyanamsaPreset.FAGAN_BRADLEY: AyanamsaInfo(
                    preset=AyanamsaPreset.FAGAN_BRADLEY,
                    swe_mode=int(swe.SIDM_FAGAN_BRADLEY),
                    label="Fagan/Bradley",
                ),
                AyanamsaPreset.YUKTESHWAR: AyanamsaInfo(
                    preset=AyanamsaPreset.YUKTESHWAR,
                    swe_mode=int(swe.SIDM_YUKTESHWAR),
                    label="Sri Yukteshwar",
                ),
                AyanamsaPreset.GALACTIC_CENTER_0_SAG: AyanamsaInfo(
                    preset=AyanamsaPreset.GALACTIC_CENTER_0_SAG,
                    swe_mode=int(swe.SIDM_GALCENT_0SAG),
                    label="Galactic Center 0° Sag",
                ),
                AyanamsaPreset.SASSANIAN: AyanamsaInfo(
                    preset=AyanamsaPreset.SASSANIAN,
                    swe_mode=int(swe.SIDM_SASSANIAN),
                    label="Sassanian",
                ),
                AyanamsaPreset.DELUCE: AyanamsaInfo(
                    preset=AyanamsaPreset.DELUCE,
                    swe_mode=int(swe.SIDM_DELUCE),
                    label="De Luce",
                ),
            }
            self._cache = mapping
        return self._cache

    def __getitem__(self, key: AyanamsaPreset) -> AyanamsaInfo:
        return self._ensure()[key]

    def __iter__(self) -> Iterator[AyanamsaPreset]:
        return iter(self._ensure())

    def __len__(self) -> int:
        return len(self._ensure())


SIDEREAL_PRESETS: Final[Mapping[AyanamsaPreset, AyanamsaInfo]] = _LazySiderealPresets()


PRIMARY_AYANAMSAS: Final[tuple[AyanamsaPreset, ...]] = (
    AyanamsaPreset.LAHIRI,
    AyanamsaPreset.RAMAN,
    AyanamsaPreset.KRISHNAMURTI,
    AyanamsaPreset.FAGAN_BRADLEY,
)


def normalize_ayanamsa(value: str | AyanamsaPreset) -> AyanamsaPreset:
    """Return the canonical :class:`AyanamsaPreset` for ``value``."""

    if isinstance(value, AyanamsaPreset):
        return value
    key = normalize_ayanamsha_name(value)
    for preset in AyanamsaPreset:
        if preset.value == key:
            return preset
    raise ValueError(
        f"Unsupported ayanamsa '{value}'. Valid options: "
        f"{', '.join(p.value for p in AyanamsaPreset)}"
    )


def _julian_day(moment: datetime) -> float:
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        raise ValueError("datetime must be timezone-aware")
    return SwissEphemerisAdapter.julian_day(moment.astimezone(UTC))


def ayanamsa_value(
    preset: AyanamsaPreset | str,
    moment: datetime,
) -> float:
    """Return the ayanamsa offset in degrees for ``moment``.

    The calculation is delegated to :mod:`pyswisseph` using the same
    sidereal modes that power the engine’s chart computations.
    """

    info = SIDEREAL_PRESETS[normalize_ayanamsa(preset)]
    jd_ut = _julian_day(moment)
    swe = get_swisseph()
    _ret, value = swe.get_ayanamsa_ex_ut(jd_ut, info.swe_mode)
    return value % 360.0


def ayanamsa_metadata(
    preset: AyanamsaPreset | str,
    moment: datetime,
) -> dict[str, object]:
    """Return metadata suitable for chart provenance payloads."""

    ayanamsha = normalize_ayanamsa(preset)
    value = ayanamsa_value(ayanamsha, moment)
    info = SIDEREAL_PRESETS[ayanamsha]
    return {
        "zodiac": "sidereal",
        "ayanamsa": ayanamsha.value,
        "ayanamsa_label": info.label,
        "ayanamsa_degrees": value,
        "ayanamsa_source": "swisseph",
    }


def available_ayanamsas() -> Iterable[AyanamsaPreset]:
    """Return all presets recognised by the engine."""

    return tuple(SIDEREAL_PRESETS.keys())


def swe_ayanamsa(
    moment: datetime,
    preset: AyanamsaPreset | str = AyanamsaPreset.LAHIRI,
) -> dict[str, object]:
    """Return Swiss Ephemeris ayanamsa data for ``moment``.

    The helper exposes the canonical presets backed by the Swiss Ephemeris
    constants, ensuring the common Lahiri, Raman, Krishnamurti, and
    Fagan/Bradley modes are easily accessible alongside the wider preset
    catalogue.
    """

    normalized = normalize_ayanamsa(preset)
    info = SIDEREAL_PRESETS[normalized]
    metadata = ayanamsa_metadata(normalized, moment)
    return {
        **metadata,
        "preset": normalized,
        "swe_mode": info.swe_mode,
    }
