"""Shared helpers for configuring sidereal zodiac modes."""

from __future__ import annotations

from typing import Final

SUPPORTED_AYANAMSHAS: Final[set[str]] = {
    "lahiri",
    "fagan_bradley",
    "krishnamurti",
    "raman",
    "deluce",
}
DEFAULT_SIDEREAL_AYANAMSHA: Final[str] = "lahiri"


def normalize_ayanamsha_name(value: str) -> str:
    """Return a canonical key for the provided ayanamsha name."""

    return value.strip().lower().replace("-", "_").replace("/", "_").replace(" ", "_")
