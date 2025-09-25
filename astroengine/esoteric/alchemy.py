"""Classical alchemy stage correspondences for transformation work."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["AlchemyStage", "ALCHEMY_STAGES"]


@dataclass(frozen=True)
class AlchemyStage:
    """Seven-stage alchemical process as codified in European practice."""

    order: int
    name: str
    latin: str
    color: str
    themes: tuple[str, ...]
    operations: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "order": self.order,
            "name": self.name,
            "latin": self.latin,
            "color": self.color,
            "themes": list(self.themes),
            "operations": list(self.operations),
        }


ALCHEMY_STAGES: tuple[AlchemyStage, ...] = (
    AlchemyStage(
        order=1,
        name="Calcination",
        latin="Calcinatio",
        color="Black",
        themes=("purification", "ego reduction", "fire"),
        operations=("burning", "drying", "breaking down"),
    ),
    AlchemyStage(
        order=2,
        name="Dissolution",
        latin="Solutio",
        color="Indigo",
        themes=("softening", "release", "subconscious"),
        operations=("immersion", "dissolving", "surrender"),
    ),
    AlchemyStage(
        order=3,
        name="Separation",
        latin="Separatio",
        color="Blue",
        themes=("discernment", "analysis", "purity"),
        operations=("filtration", "identifying essentials", "clarifying"),
    ),
    AlchemyStage(
        order=4,
        name="Conjunction",
        latin="Coniunctio",
        color="Green",
        themes=("union", "balance", "integration"),
        operations=("marriage of opposites", "alignment", "gestation"),
    ),
    AlchemyStage(
        order=5,
        name="Fermentation",
        latin="Fermentatio",
        color="White",
        themes=("renewal", "inspiration", "spirit"),
        operations=("putrefaction", "rebirth", "inflaming"),
    ),
    AlchemyStage(
        order=6,
        name="Distillation",
        latin="Distillatio",
        color="Yellow",
        themes=("refinement", "clarity", "elevation"),
        operations=("evaporation", "circulation", "concentration"),
    ),
    AlchemyStage(
        order=7,
        name="Coagulation",
        latin="Coagulatio",
        color="Red",
        themes=("manifestation", "incarnation", "stone"),
        operations=("precipitation", "solidifying", "embodiment"),
    ),
)
