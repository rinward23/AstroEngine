"""Seven Ray correspondences from Alice A. Bailey's esoteric psychology."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["RayDefinition", "SEVEN_RAYS"]


@dataclass(frozen=True)
class RayDefinition:
    """Definition of a theosophical ray."""

    number: int
    name: str
    color: str
    planetary_rulers: tuple[str, ...]
    virtues: tuple[str, ...]
    vices: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "number": self.number,
            "name": self.name,
            "color": self.color,
            "planetary_rulers": list(self.planetary_rulers),
            "virtues": list(self.virtues),
            "vices": list(self.vices),
        }


SEVEN_RAYS: tuple[RayDefinition, ...] = (
    RayDefinition(
        number=1,
        name="Will or Power",
        color="Red",
        planetary_rulers=("Vulcan", "Pluto"),
        virtues=("strength", "courage", "steadfast leadership"),
        vices=("pride", "ambition", "cruelty"),
    ),
    RayDefinition(
        number=2,
        name="Love-Wisdom",
        color="Blue",
        planetary_rulers=("Jupiter", "Sun"),
        virtues=("love", "calm patience", "intuition"),
        vices=("coldness", "indifference", "over-absorption"),
    ),
    RayDefinition(
        number=3,
        name="Active Intelligence",
        color="Green",
        planetary_rulers=("Saturn", "Earth"),
        virtues=("clear intellect", "resourcefulness", "planning"),
        vices=("manipulation", "scattered effort", "over-activity"),
    ),
    RayDefinition(
        number=4,
        name="Harmony through Conflict",
        color="Yellow",
        planetary_rulers=("Mercury", "Moon"),
        virtues=("artistic insight", "sympathy", "perseverance"),
        vices=("restlessness", "self-pity", "lack of persistence"),
    ),
    RayDefinition(
        number=5,
        name="Concrete Knowledge",
        color="Orange",
        planetary_rulers=("Venus",),
        virtues=("scientific rigour", "accuracy", "keen observation"),
        vices=("dogmatism", "criticism", "narrowness"),
    ),
    RayDefinition(
        number=6,
        name="Devotion and Idealism",
        color="Rose",
        planetary_rulers=("Mars", "Neptune"),
        virtues=("loyalty", "faith", "spiritual aspiration"),
        vices=("fanaticism", "martyrdom complex", "jealousy"),
    ),
    RayDefinition(
        number=7,
        name="Ceremonial Order",
        color="Violet",
        planetary_rulers=("Uranus", "Earth"),
        virtues=("discipline", "organization", "practical mysticism"),
        vices=("rigidity", "superstition", "formalism"),
    ),
)
