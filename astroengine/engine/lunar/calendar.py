"""Shared lunar calendar helpers for Vedic and tropical systems."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from astroengine.detectors.ingresses import ZODIAC_SIGNS, sign_index
from astroengine.utils.angles import norm360

__all__ = [
    "MASA_SEQUENCE",
    "PakshaInfo",
    "MasaInfo",
    "masa_for_longitude",
    "paksha_from_longitudes",
]

# Month names follow the classical sequence that ties the lunar month to the
# solar sign of the Sun at the start of the Shukla paksha.  We intentionally
# keep the data minimal to avoid duplicating narratives that can drift by
# locale.
MASA_SEQUENCE: Sequence[str] = (
    "Chaitra",
    "Vaisakha",
    "Jyeshtha",
    "Ashadha",
    "Shravana",
    "Bhadrapada",
    "Ashvina",
    "Kartika",
    "Margashirsha",
    "Pausha",
    "Magha",
    "Phalguna",
)

_SHUKLA_TITHI_NAMES: Sequence[str] = (
    "Pratipada",
    "Dvitiya",
    "Tritiya",
    "Chaturthi",
    "Panchami",
    "Shashthi",
    "Saptami",
    "Ashtami",
    "Navami",
    "Dashami",
    "Ekadashi",
    "Dvadashi",
    "Trayodashi",
    "Chaturdashi",
    "Purnima",
)

_KRISHNA_TITHI_NAMES: Sequence[str] = (
    "Pratipada",
    "Dvitiya",
    "Tritiya",
    "Chaturthi",
    "Panchami",
    "Shashthi",
    "Saptami",
    "Ashtami",
    "Navami",
    "Dashami",
    "Ekadashi",
    "Dvadashi",
    "Trayodashi",
    "Chaturdashi",
    "Amavasya",
)


@dataclass(frozen=True)
class PakshaInfo:
    """Summary of the waxing/waning half of the synodic month."""

    name: Literal["Shukla", "Krishna"]
    waxing: bool
    tithi_index: int
    tithi_name: str
    day_in_paksha: int
    elongation_deg: float


@dataclass(frozen=True)
class MasaInfo:
    """Metadata describing the running lunar month."""

    index: int
    name: str
    sign_index: int
    sign_name: str
    zodiac: Literal["sidereal", "tropical"]
    longitude: float


def masa_for_longitude(sun_longitude: float, *, zodiac: Literal["sidereal", "tropical"]) -> MasaInfo:
    """Return the lunar month inferred from the Sun's longitude."""

    lon = norm360(float(sun_longitude))
    sign_idx = sign_index(lon)
    month_name = MASA_SEQUENCE[sign_idx]
    return MasaInfo(
        index=sign_idx + 1,
        name=month_name,
        sign_index=sign_idx,
        sign_name=ZODIAC_SIGNS[sign_idx],
        zodiac=zodiac,
        longitude=lon,
    )


def _tithi_name(index: int) -> str:
    if index < 15:
        return _SHUKLA_TITHI_NAMES[index]
    return _KRISHNA_TITHI_NAMES[index - 15]


def paksha_from_longitudes(moon_longitude: float, sun_longitude: float) -> PakshaInfo:
    """Return the waxing/waning state derived from Moon and Sun."""

    moon = norm360(float(moon_longitude))
    sun = norm360(float(sun_longitude))
    elongation = norm360(moon - sun)
    # Guard against floating point roundoff when elongation lands exactly on 360.
    if elongation >= 360.0:
        elongation = 0.0
    # Each tithi spans 12 degrees of elongation.
    tithi = int(elongation // 12.0)
    if tithi >= 30:
        tithi = 29
    paksha_name: Literal["Shukla", "Krishna"]
    paksha_name = "Shukla" if tithi < 15 else "Krishna"
    return PakshaInfo(
        name=paksha_name,
        waxing=paksha_name == "Shukla",
        tithi_index=tithi + 1,
        tithi_name=_tithi_name(tithi),
        day_in_paksha=(tithi % 15) + 1,
        elongation_deg=elongation,
    )
