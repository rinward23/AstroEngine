"""Runtime configuration for chart computations."""

from __future__ import annotations

from dataclasses import dataclass

from ..ephemeris.sidereal import (
    DEFAULT_SIDEREAL_AYANAMSHA,
    SUPPORTED_AYANAMSHAS,
    normalize_ayanamsha_name,
)

__all__ = [
    "ChartConfig",
    "DEFAULT_SIDEREAL_AYANAMSHA",
    "SUPPORTED_AYANAMSHAS",
    "normalize_ayanamsha_name",
]


VALID_ZODIAC_SYSTEMS = {"tropical", "sidereal"}
VALID_HOUSE_SYSTEMS = {
    "alcabitius",
    "campanus",
    "equal",
    "equal_mc",
    "koch",
    "meridian",
    "morinus",
    "placidus",
    "porphyry",
    "regiomontanus",
    "sripati",
    "topocentric",
    "vehlow_equal",
    "whole_sign",
}


@dataclass(frozen=True)
class ChartConfig:
    """Container describing house system and zodiac configuration."""

    zodiac: str = "tropical"
    ayanamsha: str | None = None
    house_system: str = "placidus"

    def __post_init__(self) -> None:
        zodiac_normalized = self.zodiac.lower()
        object.__setattr__(self, "zodiac", zodiac_normalized)
        if zodiac_normalized not in VALID_ZODIAC_SYSTEMS:
            options = ", ".join(sorted(VALID_ZODIAC_SYSTEMS))
            raise ValueError(
                f"Unknown zodiac mode '{self.zodiac}'. Valid options: {options}"
            )

        house_normalized = self.house_system.lower()
        object.__setattr__(self, "house_system", house_normalized)
        if house_normalized not in VALID_HOUSE_SYSTEMS:
            options = ", ".join(sorted(VALID_HOUSE_SYSTEMS))
            raise ValueError(
                f"Unknown house system '{self.house_system}'. Valid options: {options}"
            )

        if zodiac_normalized == "tropical":
            if self.ayanamsha is not None:
                raise ValueError("Tropical charts do not accept ayanamsha parameters")
            object.__setattr__(self, "ayanamsha", None)
            return

        ayanamsha = self.ayanamsha or DEFAULT_SIDEREAL_AYANAMSHA
        ayanamsha_normalized = normalize_ayanamsha_name(ayanamsha)
        if ayanamsha_normalized not in SUPPORTED_AYANAMSHAS:
            options = ", ".join(sorted(SUPPORTED_AYANAMSHAS))
            raise ValueError(
                f"Unsupported ayanamsha '{ayanamsha}'. Supported options: {options}"
            )
        object.__setattr__(self, "ayanamsha", ayanamsha_normalized)
