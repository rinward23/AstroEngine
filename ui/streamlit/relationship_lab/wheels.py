"""SVG helpers for rendering single-ring chart wheels."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

SIGN_GLYPHS = [
    "♈",
    "♉",
    "♊",
    "♋",
    "♌",
    "♍",
    "♎",
    "♏",
    "♐",
    "♑",
    "♒",
    "♓",
]

PLANET_GLYPHS = {
    "Sun": "☉",
    "Moon": "☽",
    "Mercury": "☿",
    "Venus": "♀",
    "Mars": "♂",
    "Jupiter": "♃",
    "Saturn": "♄",
    "Uranus": "♅",
    "Neptune": "♆",
    "Pluto": "♇",
    "Chiron": "⚷",
    "Node": "☊",
}


def _normalize_lon(lon: float) -> float:
    return float(lon) % 360.0


def _resolve_label(body: str) -> str:
    return PLANET_GLYPHS.get(body, body[:2].upper())


def render_wheel_svg(
    positions: Mapping[str, float] | Sequence[tuple[str, float]],
    *,
    size: int = 420,
    font_family: str = "'Segoe UI Symbol', 'Noto Sans Symbols', sans-serif",
) -> str:
    """Render a minimalist zodiac wheel for ``positions`` as inline SVG."""

    if isinstance(positions, Mapping):
        items = list(positions.items())
    else:
        items = list(positions)

    cx = cy = size / 2
    outer_r = size * 0.45
    glyph_r = outer_r - 38
    tick_r = outer_r - 10
    sign_r = outer_r - 24

    parts: list[str] = [
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
        "xmlns='http://www.w3.org/2000/svg'>",
        '<rect width="100%" height="100%" fill="white"/>',
        f'<circle cx="{cx}" cy="{cy}" r="{outer_r}" fill="none" stroke="#333" stroke-width="1"/>',
    ]

    for idx in range(12):
        ang = math.radians(idx * 30.0)
        x1 = cx + outer_r * math.cos(ang)
        y1 = cy + outer_r * math.sin(ang)
        x2 = cx + tick_r * math.cos(ang)
        y2 = cy + tick_r * math.sin(ang)
        parts.append(
            f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" stroke="#444" stroke-width="1"/>'
        )
        mid_ang = ang + math.radians(15.0)
        sx = cx + sign_r * math.cos(mid_ang)
        sy = cy + sign_r * math.sin(mid_ang)
        glyph = SIGN_GLYPHS[idx]
        parts.append(
            f'<text x="{sx:.3f}" y="{sy:.3f}" text-anchor="middle" dominant-baseline="middle" '
            f"font-size='16' font-family={font_family}>{glyph}</text>"
        )

    used_lons: list[float] = []
    for body, lon in items:
        lon = _normalize_lon(lon)
        while any(abs(((lon - other + 180.0) % 360.0) - 180.0) < 6.0 for other in used_lons):
            lon = (lon + 6.0) % 360.0
        used_lons.append(lon)
        theta = math.radians(lon)
        px = cx + glyph_r * math.cos(theta)
        py = cy + glyph_r * math.sin(theta)
        parts.append(
            f'<text x="{px:.3f}" y="{py:.3f}" text-anchor="middle" dominant-baseline="middle" '
            f"font-size='18' font-family={font_family}>{_resolve_label(str(body))}</text>"
        )

    parts.append("</svg>")
    return "".join(parts)
