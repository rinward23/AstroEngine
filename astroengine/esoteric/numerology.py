"""Pythagorean numerology correspondences aligned with planetary rulers."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "NumerologyNumber",
    "NUMEROLOGY_NUMBERS",
    "MASTER_NUMBERS",
]


@dataclass(frozen=True)
class NumerologyNumber:
    """Numerological vibration with planetary references."""

    value: int
    name: str
    planetary_ruler: str
    keywords: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "value": self.value,
            "name": self.name,
            "planetary_ruler": self.planetary_ruler,
            "keywords": list(self.keywords),
        }


NUMEROLOGY_NUMBERS: tuple[NumerologyNumber, ...] = (
    NumerologyNumber(
        value=0,
        name="Void / Source",
        planetary_ruler="Pluto",
        keywords=("potential", "emptiness", "gestation"),
    ),
    NumerologyNumber(
        value=1,
        name="Initiator",
        planetary_ruler="Sun",
        keywords=("leadership", "selfhood", "origin"),
    ),
    NumerologyNumber(
        value=2,
        name="Mediator",
        planetary_ruler="Moon",
        keywords=("partnership", "sensitivity", "balance"),
    ),
    NumerologyNumber(
        value=3,
        name="Creative",
        planetary_ruler="Jupiter",
        keywords=("expression", "optimism", "growth"),
    ),
    NumerologyNumber(
        value=4,
        name="Builder",
        planetary_ruler="Uranus",
        keywords=("foundation", "discipline", "structure"),
    ),
    NumerologyNumber(
        value=5,
        name="Traveler",
        planetary_ruler="Mercury",
        keywords=("adaptability", "curiosity", "change"),
    ),
    NumerologyNumber(
        value=6,
        name="Caretaker",
        planetary_ruler="Venus",
        keywords=("nurturing", "beauty", "responsibility"),
    ),
    NumerologyNumber(
        value=7,
        name="Seeker",
        planetary_ruler="Neptune",
        keywords=("mysticism", "reflection", "analysis"),
    ),
    NumerologyNumber(
        value=8,
        name="Executive",
        planetary_ruler="Saturn",
        keywords=("authority", "material mastery", "management"),
    ),
    NumerologyNumber(
        value=9,
        name="Humanitarian",
        planetary_ruler="Mars",
        keywords=("culmination", "service", "passion"),
    ),
)


MASTER_NUMBERS: tuple[NumerologyNumber, ...] = (
    NumerologyNumber(
        value=11,
        name="Master Visionary",
        planetary_ruler="Moon / Neptune",
        keywords=("illumination", "intuition", "channel"),
    ),
    NumerologyNumber(
        value=22,
        name="Master Builder",
        planetary_ruler="Saturn / Uranus",
        keywords=("manifestation", "architect", "global projects"),
    ),
    NumerologyNumber(
        value=33,
        name="Master Teacher",
        planetary_ruler="Jupiter / Venus",
        keywords=("compassion", "service", "creative healing"),
    ),
)
