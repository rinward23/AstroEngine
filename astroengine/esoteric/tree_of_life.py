"""Golden Dawn style Tree of Life correspondences."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "SephiraDefinition",
    "PathDefinition",
    "TREE_OF_LIFE_SEPHIROTH",
    "TREE_OF_LIFE_PATHS",
]


@dataclass(frozen=True)
class SephiraDefinition:
    """Definition for a single sephira on the Tree of Life."""

    number: int
    name: str
    title: str
    pillar: str
    sphere: str
    planetary_association: str
    keywords: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "number": self.number,
            "name": self.name,
            "title": self.title,
            "pillar": self.pillar,
            "sphere": self.sphere,
            "planetary_association": self.planetary_association,
            "keywords": list(self.keywords),
        }


@dataclass(frozen=True)
class PathDefinition:
    """Definition for a single path connecting two sephiroth."""

    path_number: int
    hebrew_letter: str
    tarot_key: str
    connects: tuple[int, int]
    attribution: str
    keywords: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "path_number": self.path_number,
            "hebrew_letter": self.hebrew_letter,
            "tarot_key": self.tarot_key,
            "connects": list(self.connects),
            "attribution": self.attribution,
            "keywords": list(self.keywords),
        }


TREE_OF_LIFE_SEPHIROTH: tuple[SephiraDefinition, ...] = (
    SephiraDefinition(
        number=1,
        name="Kether",
        title="The Crown",
        pillar="Middle",
        sphere="Primum Mobile",
        planetary_association="Primum Mobile",
        keywords=("unity", "source", "pure being"),
    ),
    SephiraDefinition(
        number=2,
        name="Chokmah",
        title="Wisdom",
        pillar="Right",
        sphere="Sphere of the Zodiac",
        planetary_association="Zodiac",
        keywords=("impulse", "dynamic force", "expansion"),
    ),
    SephiraDefinition(
        number=3,
        name="Binah",
        title="Understanding",
        pillar="Left",
        sphere="Saturn",
        planetary_association="Saturn",
        keywords=("structure", "form", "discipline"),
    ),
    SephiraDefinition(
        number=4,
        name="Chesed",
        title="Mercy",
        pillar="Right",
        sphere="Jupiter",
        planetary_association="Jupiter",
        keywords=("benevolence", "expansion", "stability"),
    ),
    SephiraDefinition(
        number=5,
        name="Geburah",
        title="Severity",
        pillar="Left",
        sphere="Mars",
        planetary_association="Mars",
        keywords=("strength", "discipline", "courage"),
    ),
    SephiraDefinition(
        number=6,
        name="Tiphareth",
        title="Beauty",
        pillar="Middle",
        sphere="Sun",
        planetary_association="Sun",
        keywords=("equilibrium", "sacrifice", "radiance"),
    ),
    SephiraDefinition(
        number=7,
        name="Netzach",
        title="Victory",
        pillar="Right",
        sphere="Venus",
        planetary_association="Venus",
        keywords=("endurance", "desire", "creativity"),
    ),
    SephiraDefinition(
        number=8,
        name="Hod",
        title="Splendour",
        pillar="Left",
        sphere="Mercury",
        planetary_association="Mercury",
        keywords=("analysis", "communication", "ritual"),
    ),
    SephiraDefinition(
        number=9,
        name="Yesod",
        title="Foundation",
        pillar="Middle",
        sphere="Moon",
        planetary_association="Moon",
        keywords=("imagination", "dreams", "substrate"),
    ),
    SephiraDefinition(
        number=10,
        name="Malkuth",
        title="Kingdom",
        pillar="Middle",
        sphere="Elements",
        planetary_association="Earth",
        keywords=("manifestation", "body", "integration"),
    ),
)


TREE_OF_LIFE_PATHS: tuple[PathDefinition, ...] = (
    PathDefinition(
        path_number=11,
        hebrew_letter="Aleph",
        tarot_key="0 – The Fool",
        connects=(1, 2),
        attribution="Air",
        keywords=("initiation", "limitless potential", "breath"),
    ),
    PathDefinition(
        path_number=12,
        hebrew_letter="Beth",
        tarot_key="I – The Magician",
        connects=(1, 3),
        attribution="Mercury",
        keywords=("will", "channel", "skill"),
    ),
    PathDefinition(
        path_number=13,
        hebrew_letter="Gimel",
        tarot_key="II – The High Priestess",
        connects=(1, 6),
        attribution="Moon",
        keywords=("mystery", "inner voice", "threshold"),
    ),
    PathDefinition(
        path_number=14,
        hebrew_letter="Daleth",
        tarot_key="III – The Empress",
        connects=(2, 3),
        attribution="Venus",
        keywords=("fertility", "abundance", "magnetic attraction"),
    ),
    PathDefinition(
        path_number=15,
        hebrew_letter="Heh",
        tarot_key="IV – The Emperor",
        connects=(2, 6),
        attribution="Aries",
        keywords=("authority", "order", "leadership"),
    ),
    PathDefinition(
        path_number=16,
        hebrew_letter="Vav",
        tarot_key="V – The Hierophant",
        connects=(2, 4),
        attribution="Taurus",
        keywords=("tradition", "ceremony", "persistence"),
    ),
    PathDefinition(
        path_number=17,
        hebrew_letter="Zayin",
        tarot_key="VI – The Lovers",
        connects=(3, 6),
        attribution="Gemini",
        keywords=("union", "choice", "relating"),
    ),
    PathDefinition(
        path_number=18,
        hebrew_letter="Cheth",
        tarot_key="VII – The Chariot",
        connects=(3, 5),
        attribution="Cancer",
        keywords=("guardianship", "victory", "directed will"),
    ),
    PathDefinition(
        path_number=19,
        hebrew_letter="Teth",
        tarot_key="VIII – Strength",
        connects=(4, 5),
        attribution="Leo",
        keywords=("fortitude", "heart", "integration of desire"),
    ),
    PathDefinition(
        path_number=20,
        hebrew_letter="Yod",
        tarot_key="IX – The Hermit",
        connects=(4, 6),
        attribution="Virgo",
        keywords=("inner light", "solitude", "analysis"),
    ),
    PathDefinition(
        path_number=21,
        hebrew_letter="Kaph",
        tarot_key="X – Wheel of Fortune",
        connects=(4, 7),
        attribution="Jupiter",
        keywords=("cycles", "expansion", "turning point"),
    ),
    PathDefinition(
        path_number=22,
        hebrew_letter="Lamed",
        tarot_key="XI – Justice",
        connects=(5, 6),
        attribution="Libra",
        keywords=("equilibrium", "ethics", "balance"),
    ),
    PathDefinition(
        path_number=23,
        hebrew_letter="Mem",
        tarot_key="XII – The Hanged Man",
        connects=(5, 8),
        attribution="Water",
        keywords=("surrender", "suspension", "contemplation"),
    ),
    PathDefinition(
        path_number=24,
        hebrew_letter="Nun",
        tarot_key="XIII – Death",
        connects=(6, 7),
        attribution="Scorpio",
        keywords=("transformation", "release", "regeneration"),
    ),
    PathDefinition(
        path_number=25,
        hebrew_letter="Samekh",
        tarot_key="XIV – Temperance",
        connects=(6, 9),
        attribution="Sagittarius",
        keywords=("alchemical blend", "guidance", "rhythm"),
    ),
    PathDefinition(
        path_number=26,
        hebrew_letter="Ayin",
        tarot_key="XV – The Devil",
        connects=(6, 8),
        attribution="Capricorn",
        keywords=("material mastery", "bondage", "shadow work"),
    ),
    PathDefinition(
        path_number=27,
        hebrew_letter="Pe",
        tarot_key="XVI – The Tower",
        connects=(7, 8),
        attribution="Mars",
        keywords=("awakening", "sudden change", "liberation"),
    ),
    PathDefinition(
        path_number=28,
        hebrew_letter="Tzaddi",
        tarot_key="XVII – The Star",
        connects=(7, 9),
        attribution="Aquarius",
        keywords=("inspiration", "hope", "vision"),
    ),
    PathDefinition(
        path_number=29,
        hebrew_letter="Qoph",
        tarot_key="XVIII – The Moon",
        connects=(7, 10),
        attribution="Pisces",
        keywords=("dreaming", "cycles", "intuition"),
    ),
    PathDefinition(
        path_number=30,
        hebrew_letter="Resh",
        tarot_key="XIX – The Sun",
        connects=(8, 9),
        attribution="Sun",
        keywords=("vitality", "clarity", "success"),
    ),
    PathDefinition(
        path_number=31,
        hebrew_letter="Shin",
        tarot_key="XX – Judgement",
        connects=(8, 10),
        attribution="Fire",
        keywords=("renewal", "awakening", "calling"),
    ),
    PathDefinition(
        path_number=32,
        hebrew_letter="Tav",
        tarot_key="XXI – The World",
        connects=(9, 10),
        attribution="Saturn / Earth",
        keywords=("completion", "manifest world", "wholeness"),
    ),
)
