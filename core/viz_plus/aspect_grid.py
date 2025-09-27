from __future__ import annotations
from typing import Dict, Iterable, List

from core.viz_plus.wheel_svg import build_aspect_hits

ASPECT_SYMBOLS = {
    "conjunction": "☌",
    "opposition": "☍",
    "trine": "△",
    "square": "□",
    "sextile": "✶",
    "quincunx": "⚻",
}


def render_aspect_grid(hits: List[Dict]) -> Dict[str, Dict[str, str]]:
    grid: Dict[str, Dict[str, str]] = {}
    for h in hits:
        a = h["a"]
        b = h["b"]
        grid.setdefault(a, {})[b] = h["aspect"]
    return grid


def aspect_grid_symbols(positions: Dict[str, float], aspects: Iterable[str], policy: Dict) -> Dict[str, Dict[str, str]]:
    hits = build_aspect_hits(positions, aspects, policy)
    grid: Dict[str, Dict[str, str]] = {}
    for h in hits:
        a, b, asp = h["a"], h["b"], h["aspect"]
        grid.setdefault(a, {})[b] = ASPECT_SYMBOLS.get(asp, asp)
    return grid
