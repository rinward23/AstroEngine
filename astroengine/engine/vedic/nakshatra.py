"""Nakshatra and pada calculations for sidereal longitudes."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

__all__ = [
    "NAKSHATRA_ARC_DEGREES",
    "PADA_ARC_DEGREES",
    "Nakshatra",
    "NakshatraPosition",
    "lord_of_nakshatra",
    "nakshatra_info",
    "nakshatra_of",
    "pada_of",
    "position_for",
]

NAKSHATRA_ARC_DEGREES = 360.0 / 27.0
PADA_ARC_DEGREES = NAKSHATRA_ARC_DEGREES / 4.0

LORD_SEQUENCE: Sequence[str] = (
    "Ketu",
    "Venus",
    "Sun",
    "Moon",
    "Mars",
    "Rahu",
    "Jupiter",
    "Saturn",
    "Mercury",
)

NAKSHATRA_DATA: Sequence[tuple[str, str, str]] = (
    ("Ashwini", "Horse's head", "Ashvini Kumaras"),
    ("Bharani", "Yoni", "Yama"),
    ("Krittika", "Flame", "Agni"),
    ("Rohini", "Chariot", "Brahma"),
    ("Mrigashira", "Deer's head", "Soma"),
    ("Ardra", "Teardrop", "Rudra"),
    ("Punarvasu", "Quiver", "Aditi"),
    ("Pushya", "Cow's udder", "Brihaspati"),
    ("Ashlesha", "Coiled serpent", "Nagas"),
    ("Magha", "Throne", "Pitrs"),
    ("Purva Phalguni", "Front legs of bed", "Bhaga"),
    ("Uttara Phalguni", "Back legs of bed", "Aryaman"),
    ("Hasta", "Hand", "Savitar"),
    ("Chitra", "Bright jewel", "Tvashtar"),
    ("Swati", "Coral", "Vayu"),
    ("Vishakha", "Triumphal arch", "Indra-Agni"),
    ("Anuradha", "Lotus", "Mitra"),
    ("Jyeshtha", "Earring", "Indra"),
    ("Mula", "Roots", "Nirriti"),
    ("Purva Ashadha", "Fan", "Apah"),
    ("Uttara Ashadha", "Plank", "Vishva Devas"),
    ("Shravana", "Ear", "Vishnu"),
    ("Dhanishta", "Drum", "Vasus"),
    ("Shatabhisha", "Veiling circle", "Varuna"),
    ("Purva Bhadrapada", "Front legs of funeral cot", "Aja Ekapada"),
    ("Uttara Bhadrapada", "Back legs of funeral cot", "Ahirbudhnya"),
    ("Revati", "Fish", "Pushan"),
)


@dataclass(frozen=True)
class Nakshatra:
    """Metadata describing a nakshatra."""

    index: int
    name: str
    symbol: str
    deity: str
    lord: str


@dataclass(frozen=True)
class NakshatraPosition:
    """Detailed placement of a longitude within a nakshatra."""

    nakshatra: Nakshatra
    pada: int
    degree_in_pada: float
    longitude: float


_NAKSHATRAS: Sequence[Nakshatra] = tuple(
    Nakshatra(index=idx, name=name, symbol=symbol, deity=deity, lord=LORD_SEQUENCE[idx % 9])
    for idx, (name, symbol, deity) in enumerate(NAKSHATRA_DATA)
)


def _normalize_longitude(longitude: float) -> float:
    return float(longitude) % 360.0


def nakshatra_of(longitude: float) -> int:
    """Return the zero-based nakshatra index for ``longitude`` in degrees."""

    lon = _normalize_longitude(longitude)
    return int(lon // NAKSHATRA_ARC_DEGREES)


def nakshatra_info(index: int) -> Nakshatra:
    """Return the :class:`Nakshatra` metadata for ``index``."""

    return _NAKSHATRAS[index % len(_NAKSHATRAS)]


def pada_of(longitude: float) -> int:
    """Return the zero-based pada index (0-3) for ``longitude``."""

    lon = _normalize_longitude(longitude)
    offset = lon % NAKSHATRA_ARC_DEGREES
    return int(offset // PADA_ARC_DEGREES)


def lord_of_nakshatra(index: int) -> str:
    """Return the nakshatra lord for ``index``."""

    return LORD_SEQUENCE[index % len(LORD_SEQUENCE)]


def position_for(longitude: float) -> NakshatraPosition:
    """Return a :class:`NakshatraPosition` for ``longitude``."""

    lon = _normalize_longitude(longitude)
    idx = nakshatra_of(lon)
    nak = nakshatra_info(idx)
    pada_idx = pada_of(lon)
    offset = lon - (idx * NAKSHATRA_ARC_DEGREES)
    deg_in_pada = offset - (pada_idx * PADA_ARC_DEGREES)
    return NakshatraPosition(
        nakshatra=nak,
        pada=pada_idx + 1,
        degree_in_pada=deg_in_pada,
        longitude=lon,
    )
