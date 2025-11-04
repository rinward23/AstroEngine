"""House system canonicalization helpers shared across ephemeris modules."""

from __future__ import annotations

from collections.abc import Mapping

__all__ = [
    "HOUSE_CODE_BY_NAME",
    "HOUSE_CODE_BYTES_BY_NAME",
    "HOUSE_ALIASES",
    "resolve_house_code",
]


HOUSE_CODE_BY_NAME: Mapping[str, str] = {
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
    "equal_mc": "D",
}


HOUSE_ALIASES: Mapping[str, str] = {
    "ws": "whole_sign",
    "wholesign": "whole_sign",
    "whole": "whole_sign",
    "w": "whole_sign",
    "axial": "meridian",
    "meridian_axial": "meridian",
    "vehlow": "vehlow_equal",
    "sripathi": "sripati",
    "equalmc": "equal_mc",
    "topo": "topocentric",
}


HOUSE_CODE_BYTES_BY_NAME: Mapping[str, bytes] = {
    name: code.encode("ascii") for name, code in HOUSE_CODE_BY_NAME.items()
}


def resolve_house_code(name_or_code: str) -> tuple[str, str]:
    """Return the canonical name and Swiss house code for ``name_or_code``."""

    token = (name_or_code or "").strip()
    if not token:
        return "placidus", HOUSE_CODE_BY_NAME["placidus"]
    lowered = token.lower()
    if len(token) == 1 and token.upper() in {code for code in HOUSE_CODE_BY_NAME.values()}:
        code = token.upper()
        for name, mapped in HOUSE_CODE_BY_NAME.items():
            if mapped == code:
                return name, code
        return token.lower(), code
    canonical = HOUSE_ALIASES.get(lowered, lowered)
    if canonical in HOUSE_CODE_BY_NAME:
        return canonical, HOUSE_CODE_BY_NAME[canonical]
    raise ValueError(
        f"Unsupported house system '{name_or_code}'. Valid options: "
        f"{sorted(HOUSE_CODE_BY_NAME)}"
    )
