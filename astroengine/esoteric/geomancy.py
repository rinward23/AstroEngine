"""Classical Renaissance geomantic figure definitions and correspondences."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["GeomanticFigure", "GEOMANTIC_FIGURES"]


@dataclass(frozen=True)
class GeomanticFigure:
    """Definition for a single geomantic figure used in divinatory practice."""

    order: int
    name: str
    latin: str
    translation: str
    points: tuple[int, int, int, int]
    element: str
    planetary_ruler: str
    zodiacal_ruler: str
    keywords: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-serialisable payload for registry export."""

        return {
            "order": self.order,
            "name": self.name,
            "latin": self.latin,
            "translation": self.translation,
            "points": list(self.points),
            "element": self.element,
            "planetary_ruler": self.planetary_ruler,
            "zodiacal_ruler": self.zodiacal_ruler,
            "keywords": list(self.keywords),
        }


# NOTE: The figure "points" follow the fire–air–water–earth order with 1 representing
# a single (active) point and 0 representing a double (receptive) point. The sequence
# matches the ordering preserved in Heinrich Cornelius Agrippa's *De Occulta
# Philosophia* (1533) and the modern synthesis by John Michael Greer in *The Art and
# Practice of Geomancy* (1999).
GEOMANTIC_FIGURES: tuple[GeomanticFigure, ...] = (
    GeomanticFigure(
        1,
        "Via",
        "Via",
        "The Way",
        (1, 1, 1, 1),
        "Water",
        "Moon",
        "Cancer",
        ("transition", "pilgrimage", "fluid movement"),
    ),
    GeomanticFigure(
        2,
        "Populus",
        "Populus",
        "The People",
        (0, 0, 0, 0),
        "Water",
        "Moon",
        "Cancer",
        ("assemblies", "public mood", "receptivity"),
    ),
    GeomanticFigure(
        3,
        "Fortuna Major",
        "Fortuna Major",
        "Greater Fortune",
        (1, 0, 1, 1),
        "Fire",
        "Sun",
        "Leo",
        ("long-term success", "enduring power", "inner reserve"),
    ),
    GeomanticFigure(
        4,
        "Fortuna Minor",
        "Fortuna Minor",
        "Lesser Fortune",
        (1, 1, 0, 1),
        "Fire",
        "Sun",
        "Leo",
        ("short gains", "assistance", "swift opportunity"),
    ),
    GeomanticFigure(
        5,
        "Acquisitio",
        "Acquisitio",
        "Gain",
        (0, 1, 1, 1),
        "Air",
        "Jupiter",
        "Sagittarius",
        ("increase", "prosperity", "expansion"),
    ),
    GeomanticFigure(
        6,
        "Amissio",
        "Amissio",
        "Loss",
        (1, 1, 1, 0),
        "Earth",
        "Venus",
        "Taurus",
        ("release", "sacrifice", "redistribution"),
    ),
    GeomanticFigure(
        7,
        "Laetitia",
        "Laetitia",
        "Joy",
        (0, 1, 1, 0),
        "Water",
        "Jupiter",
        "Pisces",
        ("uplift", "optimism", "spiritual grace"),
    ),
    GeomanticFigure(
        8,
        "Tristitia",
        "Tristitia",
        "Sorrow",
        (1, 0, 0, 1),
        "Air",
        "Saturn",
        "Aquarius",
        ("gravity", "delays", "structural review"),
    ),
    GeomanticFigure(
        9,
        "Carcer",
        "Carcer",
        "Prison",
        (0, 0, 0, 1),
        "Earth",
        "Saturn",
        "Capricorn",
        ("containment", "discipline", "boundaries"),
    ),
    GeomanticFigure(
        10,
        "Conjunctio",
        "Conjunctio",
        "Conjunction",
        (1, 0, 1, 0),
        "Air",
        "Mercury",
        "Virgo",
        ("meetings", "negotiation", "alchemy"),
    ),
    GeomanticFigure(
        11,
        "Puella",
        "Puella",
        "The Maiden",
        (0, 1, 0, 0),
        "Air",
        "Venus",
        "Libra",
        ("diplomacy", "grace", "aesthetic judgment"),
    ),
    GeomanticFigure(
        12,
        "Puer",
        "Puer",
        "The Youth",
        (1, 0, 0, 0),
        "Fire",
        "Mars",
        "Aries",
        ("assertion", "combat", "initiative"),
    ),
    GeomanticFigure(
        13,
        "Rubeus",
        "Rubeus",
        "The Red One",
        (0, 0, 1, 0),
        "Water",
        "Mars",
        "Scorpio",
        ("passion", "danger", "purging"),
    ),
    GeomanticFigure(
        14,
        "Albus",
        "Albus",
        "The White One",
        (0, 1, 0, 1),
        "Air",
        "Mercury",
        "Gemini",
        ("clarity", "reason", "cooling"),
    ),
    GeomanticFigure(
        15,
        "Caput Draconis",
        "Caput Draconis",
        "Dragon's Head",
        (1, 1, 0, 0),
        "Earth",
        "North Node",
        "Virgo",
        ("threshold", "new cycles", "auspicious openings"),
    ),
    GeomanticFigure(
        16,
        "Cauda Draconis",
        "Cauda Draconis",
        "Dragon's Tail",
        (0, 0, 1, 1),
        "Fire",
        "South Node",
        "Pisces",
        ("closure", "expulsion", "karmic release"),
    ),
)
