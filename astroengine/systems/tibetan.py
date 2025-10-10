"""Tibetan elemental cycle utilities anchored to the rabjung system.

The implementation follows the formulas outlined in Philippe Cornu's
*Tibetan Astrology* (Snow Lion, 2002) and the Royal Government of
Bhutan's *Druk Henkel* almanac.  The helper focuses on the 60-year
rabjung cycle (starting 1027 CE) that underpins Tibetan natal analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .chinese import (
    EARTHLY_BRANCHES,
    HEAVENLY_STEMS,
    SHENGXIAO_ANIMALS,
    chinese_sexagenary_cycle,
)

__all__ = [
    "TIBETAN_ELEMENTS",
    "TIBETAN_ANIMALS",
    "RABJUNG_TRIGRAMS",
    "TibetanYear",
    "gregorian_year_to_rabjung",
    "rabjung_to_gregorian_year",
]

TIBETAN_ELEMENTS: Mapping[str, str] = {
    "Wood": "associated with flexibility, planning, and medicinal growth",
    "Fire": "linked to charisma, vitality, and visionary leadership",
    "Earth": "grounding energy emphasising nourishment and alliances",
    "Metal": "clarity, discipline, and boundary-setting strength",
    "Water": "wisdom, empathy, and strategic adaptability",
}

TIBETAN_ANIMALS: tuple[str, ...] = SHENGXIAO_ANIMALS

RABJUNG_TRIGRAMS: Mapping[str, str] = {
    "Khen": "Heaven trigram — expansive leadership and authority",
    "Khon": "Earth trigram — stability, agriculture, and service",
    "Gin": "Mountain trigram — retreat, contemplation, and resilience",
    "Zin": "Water trigram — communication, bridges, and diplomacy",
    "Son": "Wind trigram — innovation, commerce, and travel",
    "Li": "Fire trigram — illumination, scholarship, and ritual",
    "Kha": "Sky trigram — ambition tempered by compassion",
    "Da": "Metal trigram — strategy, contracts, and guardianship",
}

_PARKHA_ORDER: tuple[str, ...] = (
    "Khen",
    "Khon",
    "Gin",
    "Zin",
    "Son",
    "Li",
    "Kha",
    "Da",
)


@dataclass(frozen=True)
class TibetanYear:
    """Summary of a rabjung year with element, animal, and parkha."""

    cycle: int
    year_in_cycle: int
    western_year: int
    stem: str
    branch: str
    element: str
    animal: str
    gender: str
    parkha: str
    mewa: int


def _cycle_position(year: int) -> tuple[int, int]:
    offset = year - 1027
    cycle, remainder = divmod(offset, 60)
    if offset < 0 and remainder:
        cycle -= 1
        remainder += 60
    return cycle + 1, remainder + 1


def _element_from_stem(stem: str) -> str:
    index = HEAVENLY_STEMS.index(stem)
    group = index // 2
    return ("Wood", "Fire", "Earth", "Metal", "Water")[group]


def _gender_from_stem(stem: str) -> str:
    index = HEAVENLY_STEMS.index(stem)
    return "male" if index % 2 == 0 else "female"


def _animal_from_branch(branch: str) -> str:
    index = EARTHLY_BRANCHES.index(branch)
    return TIBETAN_ANIMALS[index]


def _parkha_for_year(year: int) -> str:
    index = (year + 6) % 8
    return _PARKHA_ORDER[index]


def _mewa_for_year(year: int) -> int:
    return ((year + 6) % 9) + 1


def gregorian_year_to_rabjung(year: int) -> TibetanYear:
    """Convert a Gregorian year to the Tibetan rabjung cycle entry."""

    stem, branch = chinese_sexagenary_cycle(year)
    cycle, year_in_cycle = _cycle_position(year)
    element = _element_from_stem(stem)
    gender = _gender_from_stem(stem)
    animal = _animal_from_branch(branch)
    parkha = _parkha_for_year(year)
    mewa = _mewa_for_year(year)
    return TibetanYear(
        cycle=cycle,
        year_in_cycle=year_in_cycle,
        western_year=year,
        stem=stem,
        branch=branch,
        element=element,
        animal=animal,
        gender=gender,
        parkha=parkha,
        mewa=mewa,
    )


def rabjung_to_gregorian_year(cycle: int, year_in_cycle: int) -> int:
    """Return the Gregorian year that begins the requested rabjung year."""

    if cycle < 1:
        raise ValueError("Rabjung cycle numbering starts at 1")
    if not 1 <= year_in_cycle <= 60:
        raise ValueError("Rabjung cycle years range from 1 to 60")
    offset = (cycle - 1) * 60 + (year_in_cycle - 1)
    return 1027 + offset

