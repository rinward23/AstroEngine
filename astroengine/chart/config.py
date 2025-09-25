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
    "HOUSE_SYSTEM_CHOICES",
    "VALID_HOUSE_SYSTEMS",
    "VALID_LILITH_VARIANTS",
    "VALID_NODE_VARIANTS",
    "normalize_ayanamsha_name",
]

VALID_ZODIAC_SYSTEMS = {"tropical", "sidereal"}

# Canonical Swiss house systems supported by the runtime.  A union of name
# aliases and Swiss single-letter codes are accepted; everything is normalised
# to the canonical key listed here.
_HOUSE_SYSTEM_CANONICAL_CODES = {
    "placidus": "P",
    "koch": "K",
    "regiomontanus": "R",
    "campanus": "C",
    "equal": "A",
    "whole_sign": "W",
    "porphyry": "O",
    "alcabitius": "B",
    "topocentric": "T",
    "morinus": "M",
    "meridian": "X",
    "vehlow_equal": "V",
    "sripati": "S",
    # Rare but exposed for completeness
    "equal_mc": "D",
}

_HOUSE_SYSTEM_ALIASES = {
    "p": "placidus",
    "plac": "placidus",
    "koch": "koch",
    "k": "koch",
    "regio": "regiomontanus",
    "r": "regiomontanus",
    "campanus": "campanus",
    "c": "campanus",
    "equal": "equal",
    "e": "equal",
    "whole_sign": "whole_sign",
    "wholesign": "whole_sign",
    "ws": "whole_sign",
    "w": "whole_sign",
    "porphyry": "porphyry",
    "o": "porphyry",
    "alcabitius": "alcabitius",
    "b": "alcabitius",
    "topocentric": "topocentric",
    "t": "topocentric",
    "morinus": "morinus",
    "m": "morinus",
    "meridian": "meridian",
    "axial": "meridian",
    "x": "meridian",
    "vehlow": "vehlow_equal",
    "vehlow_equal": "vehlow_equal",
    "v": "vehlow_equal",
    "sripati": "sripati",
    "sripathi": "sripati",
    "s": "sripati",
    "equal_mc": "equal_mc",
    "d": "equal_mc",
}

VALID_HOUSE_SYSTEMS = set(_HOUSE_SYSTEM_CANONICAL_CODES)
HOUSE_SYSTEM_CHOICES = sorted({*VALID_HOUSE_SYSTEMS, *(_HOUSE_SYSTEM_ALIASES.keys())})

VALID_NODE_VARIANTS = {"mean", "true"}
VALID_LILITH_VARIANTS = {"mean", "true"}


@dataclass(frozen=True)
class ChartConfig:
    """Container describing house system and zodiac configuration."""

    zodiac: str = "tropical"
    ayanamsha: str | None = None
    house_system: str = "placidus"
    nodes_variant: str = "mean"
    lilith_variant: str = "mean"

    def __post_init__(self) -> None:
        zodiac_normalized = self.zodiac.lower()
        object.__setattr__(self, "zodiac", zodiac_normalized)
        if zodiac_normalized not in VALID_ZODIAC_SYSTEMS:
            options = ", ".join(sorted(VALID_ZODIAC_SYSTEMS))
            raise ValueError(
                f"Unknown zodiac mode '{self.zodiac}'. Valid options: {options}"
            )

        house_normalized = self.house_system.lower()
        canonical_house = _HOUSE_SYSTEM_ALIASES.get(house_normalized, house_normalized)
        if canonical_house not in VALID_HOUSE_SYSTEMS:
            options = ", ".join(sorted(HOUSE_SYSTEM_CHOICES))
            raise ValueError(
                f"Unknown house system '{self.house_system}'. Valid options: {options}"
            )
        object.__setattr__(self, "house_system", canonical_house)

        nodes_variant = (self.nodes_variant or "mean").lower()
        if nodes_variant not in VALID_NODE_VARIANTS:
            options = ", ".join(sorted(VALID_NODE_VARIANTS))
            raise ValueError(
                f"Unknown nodes variant '{self.nodes_variant}'. Valid options: {options}"
            )
        object.__setattr__(self, "nodes_variant", nodes_variant)

        lilith_variant = (self.lilith_variant or "mean").lower()
        if lilith_variant not in VALID_LILITH_VARIANTS:
            options = ", ".join(sorted(VALID_LILITH_VARIANTS))
            raise ValueError(
                f"Unknown Lilith variant '{self.lilith_variant}'. Valid options: {options}"
            )
        object.__setattr__(self, "lilith_variant", lilith_variant)

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
