"""Sidereal ayanamsa helpers with Swiss Ephemeris backed presets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Final, Iterable, Mapping

import swisseph as swe

from ...ephemeris.sidereal import normalize_ayanamsha_name
from ...ephemeris.swisseph_adapter import SwissEphemerisAdapter

__all__ = [
    "AyanamsaInfo",
    "AyanamsaPreset",
    "SIDEREAL_PRESETS",
    "ayanamsa_metadata",
    "ayanamsa_value",
    "normalize_ayanamsa",
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


SIDEREAL_PRESETS: Final[Mapping[AyanamsaPreset, AyanamsaInfo]] = {
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
