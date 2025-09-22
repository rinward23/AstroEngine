"""Ritual and electional timing correspondences."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

__all__ = [
    "PlanetaryDay",
    "VoidOfCourseRule",
    "ElectionalWindow",
    "CHALDEAN_ORDER",
    "PLANETARY_DAYS",
    "PLANETARY_HOUR_TABLE",
    "VOID_OF_COURSE_RULES",
    "ELECTIONAL_WINDOWS",
]


@dataclass(frozen=True)
class PlanetaryDay:
    """Planetary day ruler and ritual themes."""

    weekday: str
    ruler: str
    themes: Tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "weekday": self.weekday,
            "ruler": self.ruler,
            "themes": list(self.themes),
        }


@dataclass(frozen=True)
class VoidOfCourseRule:
    """Guideline for filtering void-of-course lunar periods."""

    name: str
    description: str
    sources: Tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "sources": list(self.sources),
        }


@dataclass(frozen=True)
class ElectionalWindow:
    """Documented electional windows derived from traditional practice."""

    name: str
    criteria: Tuple[str, ...]
    notes: str
    sources: Tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "criteria": list(self.criteria),
            "notes": self.notes,
            "sources": list(self.sources),
        }


CHALDEAN_ORDER: Tuple[str, ...] = (
    "Saturn",
    "Jupiter",
    "Mars",
    "Sun",
    "Venus",
    "Mercury",
    "Moon",
)


def _build_hour_sequence(day_ruler: str) -> Tuple[str, ...]:
    if day_ruler not in CHALDEAN_ORDER:
        raise ValueError(f"Unknown day ruler: {day_ruler}")
    start = CHALDEAN_ORDER.index(day_ruler)
    sequence = []
    for hour in range(24):
        sequence.append(CHALDEAN_ORDER[(start + hour) % len(CHALDEAN_ORDER)])
    return tuple(sequence)


PLANETARY_DAYS: Tuple[PlanetaryDay, ...] = (
    PlanetaryDay("Sunday", "Sun", ("vitality", "clarity", "leadership")),
    PlanetaryDay("Monday", "Moon", ("intuition", "care", "rhythm")),
    PlanetaryDay("Tuesday", "Mars", ("courage", "initiative", "surgery")),
    PlanetaryDay("Wednesday", "Mercury", ("communication", "study", "commerce")),
    PlanetaryDay("Thursday", "Jupiter", ("abundance", "teaching", "legal affairs")),
    PlanetaryDay("Friday", "Venus", ("relationships", "art", "harmonising")),
    PlanetaryDay("Saturday", "Saturn", ("boundaries", "structure", "ancestor work")),
)


PLANETARY_HOUR_TABLE: Dict[str, Tuple[str, ...]] = {
    day.weekday: _build_hour_sequence(day.ruler)
    for day in PLANETARY_DAYS
}


VOID_OF_COURSE_RULES: Tuple[VoidOfCourseRule, ...] = (
    VoidOfCourseRule(
        name="Classical void-of-course",
        description="Moon considered void after its last Ptolemaic aspect before changing sign.",
        sources=(
            "William Lilly — Christian Astrology (1647)",
            "Olivia Barclay — Horary Astrology Rediscovered (1990)",
        ),
    ),
    VoidOfCourseRule(
        name="Modern extended void",
        description="Void begins after final major aspect regardless of sign change until next applying aspect.",
        sources=(
            "Alphee Lavoie — Void of Course Moon Research (1999)",
            "Bernadette Brady — The Eagle and the Lark (1992)",
        ),
    ),
)


ELECTIONAL_WINDOWS: Tuple[ElectionalWindow, ...] = (
    ElectionalWindow(
        name="Waxing Moon projects",
        criteria=(
            "Moon increasing in light",
            "Avoid void-of-course intervals",
            "Favour angular benefics (Venus/Jupiter)",
        ),
        notes="Traditional electional guidance for launching growth-oriented endeavours.",
        sources=(
            "Dorotheus of Sidon — Carmen Astrologicum (1st century)",
            "Christopher Warnock — The Mansions of the Moon (2010)",
        ),
    ),
    ElectionalWindow(
        name="Planetary hour reinforcement",
        criteria=(
            "Select planetary day matching operation",
            "Commence during hour of the same ruler",
            "Ensure ruler well dignified in chart",
        ),
        notes="Combines day and hour rulers to strengthen magical intent.",
        sources=(
            "Heinrich Cornelius Agrippa — Three Books of Occult Philosophy (1533)",
            "Picatrix (Ghayat al-Hakim) Book II",
        ),
    ),
    ElectionalWindow(
        name="Protection talisman window",
        criteria=(
            "Waxing Moon applying to benefic",
            "Mars and Saturn cadent or debilitated",
            "Ascendant ruler fortified",
        ),
        notes="Derived from Picatrix protocols for protective talismans.",
        sources=(
            "Picatrix (Ghayat al-Hakim) Book III",
            "Christopher Warnock — The Mansions of the Moon (2010)",
        ),
    ),
)
