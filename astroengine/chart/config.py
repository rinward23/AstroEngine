"""Runtime configuration for chart computations."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ChartConfig"]


VALID_ZODIAC_SYSTEMS = {"tropical", "sidereal"}
VALID_HOUSE_SYSTEMS = {
    "placidus",
    "koch",
    "whole_sign",
    "equal",
    "porphyry",
}


@dataclass(frozen=True)
class ChartConfig:
    """Container describing house system and zodiac configuration."""

    zodiac: str = "tropical"
    ayanamsha: str | None = None
    house_system: str = "placidus"

    def __post_init__(self) -> None:
        zodiac_normalized = self.zodiac.lower()
        if zodiac_normalized not in VALID_ZODIAC_SYSTEMS:
            options = ", ".join(sorted(VALID_ZODIAC_SYSTEMS))
            raise ValueError(f"Unknown zodiac mode '{self.zodiac}'. Valid options: {options}")

        house_normalized = self.house_system.lower()
        if house_normalized not in VALID_HOUSE_SYSTEMS:
            options = ", ".join(sorted(VALID_HOUSE_SYSTEMS))
            raise ValueError(
                f"Unknown house system '{self.house_system}'. Valid options: {options}"
            )

        if zodiac_normalized == "tropical" and self.ayanamsha is not None:
            raise ValueError("Tropical charts do not accept ayanamsha parameters")

        if zodiac_normalized == "sidereal" and not self.ayanamsha:
            raise ValueError("Sidereal charts require an ayanamsha name")
