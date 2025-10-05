"""SVG export for the transit ↔ natal overlay."""
from __future__ import annotations

import math
from typing import Iterable, Mapping, Sequence

from ....viz import SvgDocument, SvgElement
from .aspects import AspectHit
from .engine import OverlayBodyState, TransitOverlayResult
from .layout import scale_au

__all__ = ["render_overlay_svg"]


_THEMES: Mapping[str, Mapping[str, str]] = {
    "light": {
        "background": "#ffffff",
        "orbit": "#d0d7de",
        "natal_helio": "#1f6feb",
        "transit_helio": "#d97706",
        "natal_geo": "#0f172a",
        "transit_geo": "#be123c",
        "aspect": "#7c3aed",
        "text": "#111827",
        "zodiac": "#9ca3af",
    },
    "dark": {
        "background": "#0b1120",
        "orbit": "#334155",
        "natal_helio": "#38bdf8",
        "transit_helio": "#fbbf24",
        "natal_geo": "#f8fafc",
        "transit_geo": "#fca5a5",
        "aspect": "#c084fc",
        "text": "#e2e8f0",
        "zodiac": "#475569",
    },
}

_ZODIAC_LABELS: Sequence[str] = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)

_BODY_GLYPHS: Mapping[str, str] = {
    "sun": "☉",
    "moon": "☽",
    "mercury": "☿",
    "venus": "♀",
    "mars": "♂",
    "jupiter": "♃",
    "saturn": "♄",
    "uranus": "♅",
    "neptune": "♆",
    "pluto": "♇",
    "mean_node": "☊",
    "true_node": "☊",
    "south_node": "☋",
    "asc": "Asc",
    "mc": "MC",
    "chiron": "⚷",
}


def render_overlay_svg(
    result: TransitOverlayResult,
    aspects: Sequence[AspectHit] | None = None,
    *,
    width: int = 900,
    height: int = 900,
    theme: str = "light",
) -> str:
    """Return an SVG string representing ``result``."""

    palette = _THEMES.get(theme, _THEMES["light"])
    doc = SvgDocument(
        width=width,
        height=height,
        viewbox=(0.0, 0.0, float(width), float(height)),
        background=palette["background"],
        metadata={
            "natal_timestamp": result.natal.timestamp.isoformat(),
            "transit_timestamp": result.transit.timestamp.isoformat(),
            "theme": theme,
        },
    )
    cx = width / 2.0
    cy = height / 2.0

    orbit_radii = _collect_orbit_radii(result)
    max_orbit = orbit_radii[-1] if orbit_radii else 200.0
    geoc_radius = max_orbit + 90.0
    zodiac_radius = geoc_radius + 28.0

    for radius in orbit_radii:
        doc.circle(cx, cy, radius, stroke=palette["orbit"], fill="none", stroke_width=1.2, opacity=0.8)

    _draw_heliocentric(doc, result.natal.heliocentric, cx, cy, palette["natal_helio"], solid=True)
    _draw_heliocentric(doc, result.transit.heliocentric, cx, cy, palette["transit_helio"], solid=False)

    doc.circle(cx, cy, geoc_radius, stroke=palette["orbit"], fill="none", stroke_width=1.6)
    _draw_geocentric(doc, result.natal.geocentric, cx, cy, geoc_radius - 6.0, palette["natal_geo"], solid=True)
    _draw_geocentric(doc, result.transit.geocentric, cx, cy, geoc_radius + 6.0, palette["transit_geo"], solid=False)

    _draw_zodiac(doc, cx, cy, geoc_radius, zodiac_radius, palette)
    _draw_aspects(doc, aspects or (), result, cx, cy, geoc_radius, palette)
    _draw_caption(doc, cx, height - 32.0, palette, result)
    return doc.to_string(pretty=True)


def _collect_orbit_radii(result: TransitOverlayResult) -> list[float]:
    radii: list[float] = []
    seen: set[float] = set()
    for frame in (result.natal, result.transit):
        for state in frame.heliocentric.values():
            radius_px = round(scale_au(max(state.radius_au, 0.0)), 6)
            if radius_px not in seen:
                radii.append(radius_px)
                seen.add(radius_px)
    radii.sort()
    return radii


def _draw_heliocentric(
    doc: SvgDocument,
    positions: Mapping[str, OverlayBodyState],
    cx: float,
    cy: float,
    color: str,
    *,
    solid: bool,
) -> None:
    for body, state in positions.items():
        radius = scale_au(max(state.radius_au, 0.0))
        x, y = _polar_to_xy(cx, cy, radius, state.lon_deg)
        label = _format_label(body, state)
        group = SvgElement("g", {"role": "img"})
        group.add(SvgElement("title", text=label))
        if solid:
            group.add(
                SvgElement("circle").set(
                    cx=x,
                    cy=y,
                    r=6.0,
                    fill=color,
                    stroke="#ffffff",
                    **{"stroke-width": 1.0},
                )
            )
        else:
            group.add(
                SvgElement("circle").set(
                    cx=x,
                    cy=y,
                    r=7.0,
                    fill="none",
                    stroke=color,
                    **{"stroke-width": 2.0},
                )
            )
        doc.add(group)


def _draw_geocentric(
    doc: SvgDocument,
    positions: Mapping[str, OverlayBodyState],
    cx: float,
    cy: float,
    radius: float,
    color: str,
    *,
    solid: bool,
) -> None:
    for body, state in positions.items():
        x, y = _polar_to_xy(cx, cy, radius, state.lon_deg)
        label = _format_label(body, state)
        glyph = _BODY_GLYPHS.get(body, body.title())
        group = SvgElement("g", {"role": "img"})
        group.add(SvgElement("title", text=label))
        if solid:
            group.add(
                SvgElement("circle").set(
                    cx=x,
                    cy=y,
                    r=5.0,
                    fill=color,
                    stroke="#ffffff",
                    **{"stroke-width": 1.0},
                )
            )
        else:
            group.add(
                SvgElement("circle").set(
                    cx=x,
                    cy=y,
                    r=6.0,
                    fill="none",
                    stroke=color,
                    **{"stroke-width": 1.6},
                )
            )
        group.add(
            SvgElement("text", text=glyph).set(
                x=x,
                y=y + 14.0,
                fill=color,
                **{"font-size": 11, "text-anchor": "middle", "dominant-baseline": "middle"},
            )
        )
        doc.add(group)


def _draw_zodiac(
    doc: SvgDocument,
    cx: float,
    cy: float,
    inner_radius: float,
    outer_radius: float,
    palette: Mapping[str, str],
) -> None:
    tick_group = doc.group(stroke=palette["zodiac"], fill="none", **{"stroke-width": 1.0})
    for sign, name in enumerate(_ZODIAC_LABELS):
        angle = sign * 30.0
        x1, y1 = _polar_to_xy(cx, cy, inner_radius, angle)
        x2, y2 = _polar_to_xy(cx, cy, outer_radius, angle)
        tick_group.add(SvgElement("line").set(x1=x1, y1=y1, x2=x2, y2=y2))
        label_angle = angle + 15.0
        lx, ly = _polar_to_xy(cx, cy, outer_radius + 20.0, label_angle)
        doc.text(lx, ly, name, fill=palette["text"], **{"text-anchor": "middle", "font-size": 11})

    doc.add(tick_group)


def _draw_aspects(
    doc: SvgDocument,
    aspects: Iterable[AspectHit],
    result: TransitOverlayResult,
    cx: float,
    cy: float,
    base_radius: float,
    palette: Mapping[str, str],
) -> None:
    for hit in aspects:
        natal_state = result.natal.geocentric.get(hit.body)
        transit_state = result.transit.geocentric.get(hit.body)
        if natal_state is None or transit_state is None:
            continue
        inner = base_radius - 18.0
        outer = base_radius + 18.0
        angle = _midpoint_angle(natal_state.lon_deg, transit_state.lon_deg)
        x1, y1 = _polar_to_xy(cx, cy, inner, angle)
        x2, y2 = _polar_to_xy(cx, cy, outer, angle)
        attrs = {
            "stroke": palette["aspect"],
            "stroke-width": 1.6,
        }
        if hit.kind.lower().startswith("opp"):
            attrs["stroke-dasharray"] = "6,4"
        doc.line(x1, y1, x2, y2, **attrs)


def _draw_caption(
    doc: SvgDocument,
    cx: float,
    y: float,
    palette: Mapping[str, str],
    result: TransitOverlayResult,
) -> None:
    caption = doc.group(fill=palette["text"])
    caption.add(
        SvgElement("text", text=(
            f"Natal: {result.natal.timestamp.isoformat()} • "
            f"Transit: {result.transit.timestamp.isoformat()}"
        )).set(x=cx, y=y, **{"text-anchor": "middle", "font-size": 14})
    )
    doc.add(caption)


def _format_label(body: str, state: OverlayBodyState) -> str:
    deg = state.lon_deg % 360.0
    d = int(deg)
    minutes = int(round((deg - d) * 60.0))
    if minutes == 60:
        d = (d + 1) % 360
        minutes = 0
    retro = " R" if state.retrograde else ""
    return f"{body} {d:03d}°{minutes:02d}′ • {state.frame}{retro}"


def _polar_to_xy(cx: float, cy: float, radius: float, lon_deg: float) -> tuple[float, float]:
    angle_rad = math.radians(lon_deg - 90.0)
    return (
        cx + radius * math.cos(angle_rad),
        cy + radius * math.sin(angle_rad),
    )


def _midpoint_angle(a: float, b: float) -> float:
    ax = math.cos(math.radians(a))
    ay = math.sin(math.radians(a))
    bx = math.cos(math.radians(b))
    by = math.sin(math.radians(b))
    mx = ax + bx
    my = ay + by
    if mx == 0.0 and my == 0.0:
        return (a + 180.0) % 360.0
    return (math.degrees(math.atan2(my, mx)) + 360.0) % 360.0
