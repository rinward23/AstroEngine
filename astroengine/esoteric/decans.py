"""Golden Dawn style decan correspondences for natal analytics."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from ..ephemeris import BodyPosition

__all__ = [
    "DECANS",
    "DecanAssignment",
    "DecanDefinition",
    "assign_decans",
    "decan_for_longitude",
]

DEGREES_PER_SIGN = 30.0
DEGREES_PER_DECAN = 10.0
SIGNS = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)
SIGN_INDEX = {name: idx for idx, name in enumerate(SIGNS)}

# Data below follows the Hermetic Order of the Golden Dawn "Book T" sequence
# which pairs the 36 decans with planetary rulers (Chaldean order) and
# Minor Arcana pip cards. Each tuple is (sign, ruler, tarot card, tarot title).
_GOLDEN_DAWN_DECANS: Sequence[tuple[str, str, str, str]] = (
    ("Aries", "Mars", "Two of Wands", "Dominion"),
    ("Aries", "Sun", "Three of Wands", "Virtue"),
    ("Aries", "Venus", "Four of Wands", "Completion"),
    ("Taurus", "Mercury", "Five of Pentacles", "Worry"),
    ("Taurus", "Moon", "Six of Pentacles", "Success"),
    ("Taurus", "Saturn", "Seven of Pentacles", "Failure"),
    ("Gemini", "Jupiter", "Eight of Swords", "Interference"),
    ("Gemini", "Mars", "Nine of Swords", "Cruelty"),
    ("Gemini", "Sun", "Ten of Swords", "Ruin"),
    ("Cancer", "Venus", "Two of Cups", "Love"),
    ("Cancer", "Mercury", "Three of Cups", "Abundance"),
    ("Cancer", "Moon", "Four of Cups", "Luxury"),
    ("Leo", "Saturn", "Five of Wands", "Strife"),
    ("Leo", "Jupiter", "Six of Wands", "Victory"),
    ("Leo", "Mars", "Seven of Wands", "Valour"),
    ("Virgo", "Sun", "Eight of Pentacles", "Prudence"),
    ("Virgo", "Venus", "Nine of Pentacles", "Gain"),
    ("Virgo", "Mercury", "Ten of Pentacles", "Wealth"),
    ("Libra", "Moon", "Two of Swords", "Peace"),
    ("Libra", "Saturn", "Three of Swords", "Sorrow"),
    ("Libra", "Jupiter", "Four of Swords", "Truce"),
    ("Scorpio", "Mars", "Five of Cups", "Disappointment"),
    ("Scorpio", "Sun", "Six of Cups", "Pleasure"),
    ("Scorpio", "Venus", "Seven of Cups", "Debauch"),
    ("Sagittarius", "Mercury", "Eight of Wands", "Swiftness"),
    ("Sagittarius", "Moon", "Nine of Wands", "Strength"),
    ("Sagittarius", "Saturn", "Ten of Wands", "Oppression"),
    ("Capricorn", "Jupiter", "Two of Pentacles", "Change"),
    ("Capricorn", "Mars", "Three of Pentacles", "Works"),
    ("Capricorn", "Sun", "Four of Pentacles", "Power"),
    ("Aquarius", "Venus", "Five of Swords", "Defeat"),
    ("Aquarius", "Mercury", "Six of Swords", "Science"),
    ("Aquarius", "Moon", "Seven of Swords", "Futility"),
    ("Pisces", "Saturn", "Eight of Cups", "Indolence"),
    ("Pisces", "Jupiter", "Nine of Cups", "Happiness"),
    ("Pisces", "Mars", "Ten of Cups", "Satiety"),
)


@dataclass(frozen=True)
class DecanDefinition:
    """Definition for a single 10° decan."""

    index: int
    sign: str
    sign_index: int
    decan_index: int
    start_degree: float
    end_degree: float
    ruler: str
    tarot_card: str
    tarot_title: str

    def to_payload(self) -> dict[str, object]:
        """Return a serialisable representation of the decan metadata."""

        return {
            "index": self.index,
            "sign": self.sign,
            "sign_index": self.sign_index,
            "decan_index": self.decan_index,
            "start_degree": self.start_degree,
            "end_degree": self.end_degree,
            "ruler": self.ruler,
            "tarot_card": self.tarot_card,
            "tarot_title": self.tarot_title,
        }


@dataclass(frozen=True)
class DecanAssignment:
    """Mapping of a chart body to its corresponding decan."""

    body: str
    longitude: float
    decan: DecanDefinition

    def to_payload(self) -> dict[str, object]:
        """Return a serialisable snapshot for reporting."""

        return {
            "body": self.body,
            "longitude": self.longitude,
            "decan": self.decan.to_payload(),
        }


def _build_decan_table() -> tuple[DecanDefinition, ...]:
    definitions: list[DecanDefinition] = []
    for idx, (sign, ruler, tarot_card, tarot_title) in enumerate(_GOLDEN_DAWN_DECANS):
        sign_index = SIGN_INDEX[sign]
        decan_index = idx - sign_index * 3
        start_degree = sign_index * DEGREES_PER_SIGN + decan_index * DEGREES_PER_DECAN
        end_degree = start_degree + DEGREES_PER_DECAN
        definitions.append(
            DecanDefinition(
                index=idx,
                sign=sign,
                sign_index=sign_index,
                decan_index=decan_index,
                start_degree=start_degree,
                end_degree=end_degree,
                ruler=ruler,
                tarot_card=tarot_card,
                tarot_title=tarot_title,
            )
        )
    return tuple(definitions)


DECANS: tuple[DecanDefinition, ...] = _build_decan_table()


def _normalize_longitude(longitude: float) -> float:
    if not math.isfinite(longitude):
        raise ValueError("Longitude must be a finite number of degrees")
    # Python's modulo already returns values in [0, 360) for positive modulus.
    normalized = longitude % 360.0
    if normalized < 0.0:
        normalized += 360.0
    return normalized


def decan_for_longitude(
    longitude: float, *, table: Sequence[DecanDefinition] | None = None
) -> DecanDefinition:
    """Return the decan definition covering the supplied longitude."""

    decan_table = table or DECANS
    normalized = _normalize_longitude(longitude)
    index = int(normalized // DEGREES_PER_DECAN)
    if index >= len(decan_table):
        # ``normalized`` is in [0, 360), so this can only happen via rounding.
        index = len(decan_table) - 1
    return decan_table[index]


def assign_decans(
    positions: Mapping[str, BodyPosition] | Iterable[tuple[str, BodyPosition]],
    *,
    table: Sequence[DecanDefinition] | None = None,
) -> tuple[DecanAssignment, ...]:
    """Return decan assignments for a mapping of bodies."""

    if isinstance(positions, Mapping):
        items = positions.items()
    else:
        items = tuple(positions)
    decan_table = table or DECANS
    assignments: list[DecanAssignment] = []
    for name, pos in items:
        assignments.append(
            DecanAssignment(
                body=name,
                longitude=pos.longitude,
                decan=decan_for_longitude(pos.longitude, table=decan_table),
            )
        )
    return tuple(assignments)
