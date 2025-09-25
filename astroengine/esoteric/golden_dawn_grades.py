"""Hermetic Order of the Golden Dawn initiatory grade ladder."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["GoldenDawnGrade", "GOLDEN_DAWN_GRADES"]


@dataclass(frozen=True)
class GoldenDawnGrade:
    """Golden Dawn grade definition with sephirothic correspondences."""

    grade: str
    title: str
    sephira_number: int | None
    sephira_name: str | None
    element: str | None
    notes: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "grade": self.grade,
            "title": self.title,
            "sephira_number": self.sephira_number,
            "sephira_name": self.sephira_name,
            "element": self.element,
            "notes": list(self.notes),
        }


GOLDEN_DAWN_GRADES: tuple[GoldenDawnGrade, ...] = (
    GoldenDawnGrade(
        grade="0°=0□",
        title="Neophyte",
        sephira_number=10,
        sephira_name="Malkuth",
        element="Earth",
        notes=("Entrance to Outer Order", "Threshold purification"),
    ),
    GoldenDawnGrade(
        grade="1°=10□",
        title="Zelator",
        sephira_number=10,
        sephira_name="Malkuth",
        element="Earth",
        notes=("Grounding of force", "Elemental mastery of Earth"),
    ),
    GoldenDawnGrade(
        grade="2°=9□",
        title="Theoricus",
        sephira_number=9,
        sephira_name="Yesod",
        element="Air",
        notes=("Mind discipline", "Elemental mastery of Air"),
    ),
    GoldenDawnGrade(
        grade="3°=8□",
        title="Practicus",
        sephira_number=8,
        sephira_name="Hod",
        element="Water",
        notes=("Ritual intellect", "Elemental mastery of Water"),
    ),
    GoldenDawnGrade(
        grade="4°=7□",
        title="Philosophus",
        sephira_number=7,
        sephira_name="Netzach",
        element="Fire",
        notes=("Devotion and artistry", "Elemental mastery of Fire"),
    ),
    GoldenDawnGrade(
        grade="Portal",
        title="Portal Adeptus",
        sephira_number=None,
        sephira_name=None,
        element=None,
        notes=(
            "Transition between Outer and Inner Order",
            "Balances Netzach-Hod-Yesod",
        ),
    ),
    GoldenDawnGrade(
        grade="5°=6□",
        title="Adeptus Minor",
        sephira_number=6,
        sephira_name="Tiphareth",
        element="Sun",
        notes=("Inner Order entry", "Mystery of the Rosy Cross"),
    ),
    GoldenDawnGrade(
        grade="6°=5□",
        title="Adeptus Major",
        sephira_number=5,
        sephira_name="Geburah",
        element="Mars",
        notes=("Strength tempered by love", "Inner Order advancement"),
    ),
    GoldenDawnGrade(
        grade="7°=4□",
        title="Adeptus Exemptus",
        sephira_number=4,
        sephira_name="Chesed",
        element="Jupiter",
        notes=("Mercy and mastery", "Governing the Outer work"),
    ),
    GoldenDawnGrade(
        grade="8°=3□",
        title="Magister Templi",
        sephira_number=3,
        sephira_name="Binah",
        element="Saturn",
        notes=("Supernal understanding", "Link to the Secret Chiefs"),
    ),
    GoldenDawnGrade(
        grade="9°=2□",
        title="Magus",
        sephira_number=2,
        sephira_name="Chokmah",
        element="Zodiac",
        notes=("Wisdom and formulation", "Archetypal expression"),
    ),
    GoldenDawnGrade(
        grade="10°=1□",
        title="Ipsissimus",
        sephira_number=1,
        sephira_name="Kether",
        element="Primum Mobile",
        notes=("Hidden chief", "Union with the Crown"),
    ),
)
