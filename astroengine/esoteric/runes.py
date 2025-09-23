"""Elder Futhark rune correspondences for divination overlays."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

__all__ = ["Rune", "ELDER_FUTHARK_RUNES"]


@dataclass(frozen=True)
class Rune:
    """Definition of a rune in the Elder Futhark sequence."""

    order: int
    name: str
    transliteration: str
    phoneme: str
    meaning: str
    element: str
    keywords: Tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "order": self.order,
            "name": self.name,
            "transliteration": self.transliteration,
            "phoneme": self.phoneme,
            "meaning": self.meaning,
            "element": self.element,
            "keywords": list(self.keywords),
        }


ELDER_FUTHARK_RUNES: Tuple[Rune, ...] = (
    Rune(1, "Fehu", "F", "f", "Cattle / Wealth", "Fire", ("abundance", "mobility", "value")),
    Rune(2, "Uruz", "U", "u", "Aurochs", "Earth", ("strength", "vitality", "endurance")),
    Rune(3, "Thurisaz", "Th", "θ", "Giant / Thorn", "Fire", ("defence", "challenge", "awakening")),
    Rune(4, "Ansuz", "A", "a", "Odin / Mouth", "Air", ("communication", "inspiration", "ancestral guidance")),
    Rune(5, "Raidho", "R", "r", "Journey", "Air", ("travel", "rhythm", "order")),
    Rune(6, "Kenaz", "K", "k", "Torch", "Fire", ("illumination", "craft", "revelation")),
    Rune(7, "Gebo", "G", "g", "Gift", "Air", ("exchange", "partnership", "sacred contract")),
    Rune(8, "Wunjo", "W", "w", "Joy", "Water", ("pleasure", "harmony", "comfort")),
    Rune(9, "Hagalaz", "H", "h", "Hail", "Water", ("disruption", "natural forces", "transformation")),
    Rune(10, "Nauthiz", "N", "n", "Need", "Fire", ("constraint", "necessity", "innovation")),
    Rune(11, "Isa", "I", "i", "Ice", "Water", ("stillness", "focus", "preservation")),
    Rune(12, "Jera", "J", "j", "Year / Harvest", "Earth", ("cycles", "reward", "timing")),
    Rune(13, "Eihwaz", "EI", "ï", "Yew", "Fire", ("endurance", "initiation", "protection")),
    Rune(14, "Perthro", "P", "p", "Lot Cup", "Water", ("mystery", "fate", "hidden things")),
    Rune(15, "Algiz", "Z", "z", "Elk", "Air", ("protection", "higher self", "alertness")),
    Rune(16, "Sowilo", "S", "s", "Sun", "Fire", ("success", "wholeness", "guidance")),
    Rune(17, "Tiwaz", "T", "t", "Tyr", "Air", ("justice", "sacrifice", "courage")),
    Rune(18, "Berkano", "B", "b", "Birch", "Earth", ("birth", "growth", "family")),
    Rune(19, "Ehwaz", "E", "e", "Horse", "Air", ("partnership", "movement", "trust")),
    Rune(20, "Mannaz", "M", "m", "Man", "Air", ("humanity", "cooperation", "self-awareness")),
    Rune(21, "Laguz", "L", "l", "Water", "Water", ("intuition", "flow", "dreams")),
    Rune(22, "Ingwaz", "NG", "ŋ", "Seed / Ing", "Earth", ("gestation", "potential", "completion")),
    Rune(23, "Dagaz", "D", "d", "Day", "Fire", ("breakthrough", "clarity", "awakening")),
    Rune(24, "Othala", "O", "o", "Ancestral Land", "Earth", ("heritage", "legacy", "home")),
)
