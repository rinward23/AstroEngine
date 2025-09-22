"""Tarot correspondences beyond the decan overlays."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

__all__ = [
    "TarotMajorArcana",
    "TarotCourtCard",
    "TarotSpread",
    "TAROT_MAJORS",
    "TAROT_COURTS",
    "TAROT_SPREADS",
]


@dataclass(frozen=True)
class TarotMajorArcana:
    """Golden Dawn major arcana correspondences."""

    number: int
    name: str
    hebrew_letter: str
    path_number: int
    attribution: str
    keywords: Tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "number": self.number,
            "name": self.name,
            "hebrew_letter": self.hebrew_letter,
            "path_number": self.path_number,
            "attribution": self.attribution,
            "keywords": list(self.keywords),
        }


@dataclass(frozen=True)
class TarotCourtCard:
    """Court card correspondences including zodiacal spans."""

    rank: str
    suit: str
    elemental_quality: str
    zodiacal_attribution: str
    keywords: Tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "rank": self.rank,
            "suit": self.suit,
            "elemental_quality": self.elemental_quality,
            "zodiacal_attribution": self.zodiacal_attribution,
            "keywords": list(self.keywords),
        }


@dataclass(frozen=True)
class TarotSpread:
    """Documented tarot spread with positional meanings."""

    name: str
    cards: int
    description: str
    positions: Tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "cards": self.cards,
            "description": self.description,
            "positions": list(self.positions),
        }


TAROT_MAJORS: Tuple[TarotMajorArcana, ...] = (
    TarotMajorArcana(
        number=0,
        name="The Fool",
        hebrew_letter="Aleph",
        path_number=11,
        attribution="Air",
        keywords=("innocence", "leap of faith", "open horizon"),
    ),
    TarotMajorArcana(
        number=1,
        name="The Magician",
        hebrew_letter="Beth",
        path_number=12,
        attribution="Mercury",
        keywords=("focused intent", "skill", "communication"),
    ),
    TarotMajorArcana(
        number=2,
        name="The High Priestess",
        hebrew_letter="Gimel",
        path_number=13,
        attribution="Moon",
        keywords=("mystery", "intuition", "hidden knowledge"),
    ),
    TarotMajorArcana(
        number=3,
        name="The Empress",
        hebrew_letter="Daleth",
        path_number=14,
        attribution="Venus",
        keywords=("fertility", "nurture", "creativity"),
    ),
    TarotMajorArcana(
        number=4,
        name="The Emperor",
        hebrew_letter="Heh",
        path_number=15,
        attribution="Aries",
        keywords=("structure", "authority", "sovereignty"),
    ),
    TarotMajorArcana(
        number=5,
        name="The Hierophant",
        hebrew_letter="Vav",
        path_number=16,
        attribution="Taurus",
        keywords=("ritual", "tradition", "teaching"),
    ),
    TarotMajorArcana(
        number=6,
        name="The Lovers",
        hebrew_letter="Zayin",
        path_number=17,
        attribution="Gemini",
        keywords=("choice", "union", "alignment"),
    ),
    TarotMajorArcana(
        number=7,
        name="The Chariot",
        hebrew_letter="Cheth",
        path_number=18,
        attribution="Cancer",
        keywords=("victory", "guardianship", "directed will"),
    ),
    TarotMajorArcana(
        number=8,
        name="Strength",
        hebrew_letter="Teth",
        path_number=19,
        attribution="Leo",
        keywords=("courage", "heart", "integration"),
    ),
    TarotMajorArcana(
        number=9,
        name="The Hermit",
        hebrew_letter="Yod",
        path_number=20,
        attribution="Virgo",
        keywords=("inner guidance", "solitude", "analysis"),
    ),
    TarotMajorArcana(
        number=10,
        name="Wheel of Fortune",
        hebrew_letter="Kaph",
        path_number=21,
        attribution="Jupiter",
        keywords=("cycles", "destiny", "turning point"),
    ),
    TarotMajorArcana(
        number=11,
        name="Justice",
        hebrew_letter="Lamed",
        path_number=22,
        attribution="Libra",
        keywords=("balance", "law", "cause and effect"),
    ),
    TarotMajorArcana(
        number=12,
        name="The Hanged Man",
        hebrew_letter="Mem",
        path_number=23,
        attribution="Water",
        keywords=("suspension", "sacrifice", "reversal"),
    ),
    TarotMajorArcana(
        number=13,
        name="Death",
        hebrew_letter="Nun",
        path_number=24,
        attribution="Scorpio",
        keywords=("transformation", "ending", "rebirth"),
    ),
    TarotMajorArcana(
        number=14,
        name="Temperance",
        hebrew_letter="Samekh",
        path_number=25,
        attribution="Sagittarius",
        keywords=("moderation", "alchemy", "guidance"),
    ),
    TarotMajorArcana(
        number=15,
        name="The Devil",
        hebrew_letter="Ayin",
        path_number=26,
        attribution="Capricorn",
        keywords=("material mastery", "temptation", "bondage"),
    ),
    TarotMajorArcana(
        number=16,
        name="The Tower",
        hebrew_letter="Pe",
        path_number=27,
        attribution="Mars",
        keywords=("liberation", "upheaval", "awakening"),
    ),
    TarotMajorArcana(
        number=17,
        name="The Star",
        hebrew_letter="Tzaddi",
        path_number=28,
        attribution="Aquarius",
        keywords=("hope", "vision", "inspiration"),
    ),
    TarotMajorArcana(
        number=18,
        name="The Moon",
        hebrew_letter="Qoph",
        path_number=29,
        attribution="Pisces",
        keywords=("dreams", "cycles", "intuition"),
    ),
    TarotMajorArcana(
        number=19,
        name="The Sun",
        hebrew_letter="Resh",
        path_number=30,
        attribution="Sun",
        keywords=("vitality", "clarity", "joy"),
    ),
    TarotMajorArcana(
        number=20,
        name="Judgement",
        hebrew_letter="Shin",
        path_number=31,
        attribution="Fire",
        keywords=("awakening", "calling", "resolution"),
    ),
    TarotMajorArcana(
        number=21,
        name="The World",
        hebrew_letter="Tav",
        path_number=32,
        attribution="Saturn / Earth",
        keywords=("completion", "integration", "cosmos"),
    ),
)


TAROT_COURTS: Tuple[TarotCourtCard, ...] = (
    TarotCourtCard(
        rank="Knight",
        suit="Wands",
        elemental_quality="Fire of Fire",
        zodiacal_attribution="Scorpio 21°–30° & Sagittarius 0°–20°",
        keywords=("impulse", "adventure", "initiative"),
    ),
    TarotCourtCard(
        rank="Queen",
        suit="Wands",
        elemental_quality="Water of Fire",
        zodiacal_attribution="Pisces 21°–30° & Aries 0°–20°",
        keywords=("magnetism", "charisma", "creative flow"),
    ),
    TarotCourtCard(
        rank="Prince",
        suit="Wands",
        elemental_quality="Air of Fire",
        zodiacal_attribution="Cancer 21°–30° & Leo 0°–20°",
        keywords=("vision", "movement", "expression"),
    ),
    TarotCourtCard(
        rank="Princess",
        suit="Wands",
        elemental_quality="Earth of Fire",
        zodiacal_attribution="Kerubic quadrant of Fire signs (Aries, Leo, Sagittarius)",
        keywords=("manifest inspiration", "spark", "potential"),
    ),
    TarotCourtCard(
        rank="Knight",
        suit="Cups",
        elemental_quality="Fire of Water",
        zodiacal_attribution="Aquarius 21°–30° & Pisces 0°–20°",
        keywords=("questing heart", "romance", "spiritual search"),
    ),
    TarotCourtCard(
        rank="Queen",
        suit="Cups",
        elemental_quality="Water of Water",
        zodiacal_attribution="Gemini 21°–30° & Cancer 0°–20°",
        keywords=("empathy", "dreaming", "receptivity"),
    ),
    TarotCourtCard(
        rank="Prince",
        suit="Cups",
        elemental_quality="Air of Water",
        zodiacal_attribution="Libra 21°–30° & Scorpio 0°–20°",
        keywords=("desire", "magnetic allure", "reflection"),
    ),
    TarotCourtCard(
        rank="Princess",
        suit="Cups",
        elemental_quality="Earth of Water",
        zodiacal_attribution="Kerubic quadrant of Water signs (Cancer, Scorpio, Pisces)",
        keywords=("dream seeding", "emotional renewal", "intuition"),
    ),
    TarotCourtCard(
        rank="Knight",
        suit="Swords",
        elemental_quality="Fire of Air",
        zodiacal_attribution="Taurus 21°–30° & Gemini 0°–20°",
        keywords=("strategic action", "swift change", "courage"),
    ),
    TarotCourtCard(
        rank="Queen",
        suit="Swords",
        elemental_quality="Water of Air",
        zodiacal_attribution="Virgo 21°–30° & Libra 0°–20°",
        keywords=("clarity", "discernment", "truth"),
    ),
    TarotCourtCard(
        rank="Prince",
        suit="Swords",
        elemental_quality="Air of Air",
        zodiacal_attribution="Capricorn 21°–30° & Aquarius 0°–20°",
        keywords=("analysis", "innovation", "restless mind"),
    ),
    TarotCourtCard(
        rank="Princess",
        suit="Swords",
        elemental_quality="Earth of Air",
        zodiacal_attribution="Kerubic quadrant of Air signs (Gemini, Libra, Aquarius)",
        keywords=("manifest ideas", "news", "study"),
    ),
    TarotCourtCard(
        rank="Knight",
        suit="Pentacles",
        elemental_quality="Fire of Earth",
        zodiacal_attribution="Leo 21°–30° & Virgo 0°–20°",
        keywords=("applied force", "steadfast growth", "responsibility"),
    ),
    TarotCourtCard(
        rank="Queen",
        suit="Pentacles",
        elemental_quality="Water of Earth",
        zodiacal_attribution="Sagittarius 21°–30° & Capricorn 0°–20°",
        keywords=("nurturing resources", "practical wisdom", "harvest"),
    ),
    TarotCourtCard(
        rank="Prince",
        suit="Pentacles",
        elemental_quality="Air of Earth",
        zodiacal_attribution="Aries 21°–30° & Taurus 0°–20°",
        keywords=("planning", "method", "cultivation"),
    ),
    TarotCourtCard(
        rank="Princess",
        suit="Pentacles",
        elemental_quality="Earth of Earth",
        zodiacal_attribution="Kerubic quadrant of Earth signs (Taurus, Virgo, Capricorn)",
        keywords=("manifest potential", "study of matter", "stability"),
    ),
)


TAROT_SPREADS: Tuple[TarotSpread, ...] = (
    TarotSpread(
        name="Three-Card Progression",
        cards=3,
        description="Golden Dawn style triad mapping past, present, future impulses.",
        positions=("Past influence", "Present focus", "Unfolding trajectory"),
    ),
    TarotSpread(
        name="Celtic Cross (Waite)",
        cards=10,
        description="Waite's published Celtic Cross capturing inner and outer dynamics.",
        positions=(
            "Present focus",
            "Immediate challenge",
            "Subconscious foundation",
            "Recent past",
            "Crown / conscious aim",
            "Near future",
            "Self",
            "Environment",
            "Hopes and fears",
            "Outcome",
        ),
    ),
    TarotSpread(
        name="Elemental Balance",
        cards=5,
        description="Adapted Golden Dawn elemental check-in for ritual preparation.",
        positions=(
            "Fire / passion",
            "Water / feeling",
            "Air / thought",
            "Earth / body",
            "Spirit / synthesis",
        ),
    ),
)
