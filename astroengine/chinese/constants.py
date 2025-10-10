"""Lookup tables for Heavenly Stems and Earthly Branches."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class HeavenlyStem:
    """Representation of one of the ten Heavenly Stems (天干)."""

    name: str
    element: str
    polarity: str


@dataclass(frozen=True)
class EarthlyBranch:
    """Representation of one of the twelve Earthly Branches (地支)."""

    name: str
    animal: str
    element: str
    polarity: str


HEAVENLY_STEMS: Final[tuple[HeavenlyStem, ...]] = (
    HeavenlyStem("Jia", "Wood", "Yang"),
    HeavenlyStem("Yi", "Wood", "Yin"),
    HeavenlyStem("Bing", "Fire", "Yang"),
    HeavenlyStem("Ding", "Fire", "Yin"),
    HeavenlyStem("Wu", "Earth", "Yang"),
    HeavenlyStem("Ji", "Earth", "Yin"),
    HeavenlyStem("Geng", "Metal", "Yang"),
    HeavenlyStem("Xin", "Metal", "Yin"),
    HeavenlyStem("Ren", "Water", "Yang"),
    HeavenlyStem("Gui", "Water", "Yin"),
)


EARTHLY_BRANCHES: Final[tuple[EarthlyBranch, ...]] = (
    EarthlyBranch("Zi", "Rat", "Water", "Yang"),
    EarthlyBranch("Chou", "Ox", "Earth", "Yin"),
    EarthlyBranch("Yin", "Tiger", "Wood", "Yang"),
    EarthlyBranch("Mao", "Rabbit", "Wood", "Yin"),
    EarthlyBranch("Chen", "Dragon", "Earth", "Yang"),
    EarthlyBranch("Si", "Snake", "Fire", "Yin"),
    EarthlyBranch("Wu", "Horse", "Fire", "Yang"),
    EarthlyBranch("Wei", "Goat", "Earth", "Yin"),
    EarthlyBranch("Shen", "Monkey", "Metal", "Yang"),
    EarthlyBranch("You", "Rooster", "Metal", "Yin"),
    EarthlyBranch("Xu", "Dog", "Earth", "Yang"),
    EarthlyBranch("Hai", "Pig", "Water", "Yin"),
)


def stem_for_index(index: int) -> HeavenlyStem:
    """Return the Heavenly Stem for ``index`` (0-9)."""

    return HEAVENLY_STEMS[index % len(HEAVENLY_STEMS)]


def branch_for_index(index: int) -> EarthlyBranch:
    """Return the Earthly Branch for ``index`` (0-11)."""

    return EARTHLY_BRANCHES[index % len(EARTHLY_BRANCHES)]
