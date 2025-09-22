"""Shared constants and helpers for target frame selection."""

from __future__ import annotations

from typing import Dict, Iterable, List, Sequence

TARGET_FRAME_BODIES: Dict[str, Sequence[str]] = {
    "natal": (
        "Sun",
        "Moon",
        "Mercury",
        "Venus",
        "Mars",
        "Jupiter",
        "Saturn",
        "Uranus",
        "Neptune",
        "Pluto",
    ),
    "angles": ("ASC", "MC", "IC", "DSC"),
    "points": ("Fortune", "Spirit", "Vertex", "Antivertex"),
}

DEFAULT_TARGET_FRAMES: Sequence[str] = ("natal",)
DEFAULT_TARGET_SELECTION: Sequence[str] = ("Sun", "Moon", "ASC")


def available_frames() -> List[str]:
    """Return the sorted list of known target frames."""

    return sorted(TARGET_FRAME_BODIES.keys())


def expand_targets(frames: Iterable[str], bodies: Iterable[str]) -> List[str]:
    """Return fully-qualified target tokens for ``bodies`` within ``frames``."""

    resolved: List[str] = []
    frame_list = list(frames) or list(DEFAULT_TARGET_FRAMES)
    for body in bodies:
        symbol = str(body).strip()
        if not symbol:
            continue
        if "_" in symbol or ":" in symbol:
            token = symbol.replace(":", "_")
            if token not in resolved:
                resolved.append(token)
            continue
        for frame in frame_list:
            token = f"{frame}_{symbol}"
            if token not in resolved:
                resolved.append(token)
    return resolved


def frame_body_options(frames: Iterable[str] | None = None) -> Dict[str, Sequence[str]]:
    """Return available body options for the selected ``frames``."""

    if not frames:
        frames = DEFAULT_TARGET_FRAMES
    out: Dict[str, Sequence[str]] = {}
    for frame in frames:
        key = str(frame)
        bodies = TARGET_FRAME_BODIES.get(key)
        if bodies:
            out[key] = bodies
    return out


__all__ = [
    "DEFAULT_TARGET_FRAMES",
    "DEFAULT_TARGET_SELECTION",
    "TARGET_FRAME_BODIES",
    "available_frames",
    "expand_targets",
    "frame_body_options",
]
