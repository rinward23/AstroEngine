"""Shared constants for the Relationship Lab UI."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class AspectInfo:
    key: str
    label: str
    degrees: float
    symbol: str
    family: str


ASPECTS: dict[str, AspectInfo] = {
    "conjunction": AspectInfo("conjunction", "Conjunction (0°)", 0.0, "☌", "neutral"),
    "sextile": AspectInfo("sextile", "Sextile (60°)", 60.0, "⚹", "harmonious"),
    "square": AspectInfo("square", "Square (90°)", 90.0, "□", "challenging"),
    "trine": AspectInfo("trine", "Trine (120°)", 120.0, "△", "harmonious"),
    "opposition": AspectInfo("opposition", "Opposition (180°)", 180.0, "☍", "challenging"),
    "quincunx": AspectInfo("quincunx", "Quincunx (150°)", 150.0, "⚻", "challenging"),
    "semisquare": AspectInfo("semisquare", "Semi-square (45°)", 45.0, "∠", "challenging"),
    "sesquisquare": AspectInfo("sesquisquare", "Sesqui-square (135°)", 135.0, "⚼", "challenging"),
    "quintile": AspectInfo("quintile", "Quintile (72°)", 72.0, "⚝", "harmonious"),
    "biquintile": AspectInfo("biquintile", "Bi-quintile (144°)", 144.0, "✶", "harmonious"),
}

MAJOR_ASPECTS: list[str] = [
    "conjunction",
    "sextile",
    "square",
    "trine",
    "opposition",
]

EXTENDED_ASPECTS: list[str] = MAJOR_ASPECTS + [
    "quincunx",
    "semisquare",
    "sesquisquare",
    "quintile",
    "biquintile",
]

FAMILY_LABELS = {
    "harmonious": "Harmonious",
    "challenging": "Challenging",
    "neutral": "Neutral",
}


def aspect_choices(keys: Iterable[str]) -> list[str]:
    return [ASPECTS[key].label for key in keys if key in ASPECTS]
