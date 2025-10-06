from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from core.aspects_plus.harmonics import BASE_ASPECTS
from core.aspects_plus.matcher import angular_sep_deg
from core.aspects_plus.orb_policy import orb_limit

# --------------------------- Helpers ---------------------------------------

def _norm360(x: float) -> float:
    v = x % 360.0
    return v + 360.0 if v < 0 else v


def _pol2cart(angle_deg: float, r: float, cx: float, cy: float) -> tuple[float, float]:
    # SVG 0° points to the right (x+), positive angles go **counterclockwise**
    a = math.radians(angle_deg)
    return cx + r * math.cos(a), cy - r * math.sin(a)


def _lon_to_angle_svg(lon: float) -> float:
    # Place 0° Aries at +X axis; increase CCW. Common in wheels.
    return _norm360(0.0 - lon)


@dataclass
class WheelOptions:
    size: int = 800
    margin: int = 20
    ring_outer: float = 0.48  # fraction of size
    ring_inner: float = 0.36
    show_degree_ticks: bool = True
    show_house_lines: bool = True
    show_aspects: bool = True
    aspects: Iterable[str] = ("conjunction", "opposition", "square", "trine", "sextile")
    policy: dict | None = None


# --------------------------- Aspects (public helper) -----------------------

def build_aspect_hits(positions: dict[str, float], aspects: Iterable[str], policy: dict) -> list[dict]:
    names = list(positions.keys())
    hits: list[dict] = []
    for i, a in enumerate(names):
        for j in range(i + 1, len(names)):
            b = names[j]
            delta = angular_sep_deg(positions[a], positions[b])
            best = None
            for asp in aspects:
                ang = BASE_ASPECTS.get(asp.lower())
                if ang is None:
                    continue
                orb = abs(delta - float(ang))
                limit = orb_limit(a, b, asp.lower(), policy)
                if orb <= limit + 1e-9:
                    cand = {
                        "a": a,
                        "b": b,
                        "aspect": asp.lower(),
                        "angle": float(ang),
                        "delta": float(delta),
                        "orb": float(orb),
                        "limit": float(limit),
                    }
                    if best is None or cand["orb"] < best["orb"]:
                        best = cand
            if best:
                hits.append(best)
    hits.sort(key=lambda h: (h["orb"], h["a"], h["b"]))
    return hits


# --------------------------- SVG wheel -------------------------------------

ROMAN_NUMERALS = [
    "I",
    "II",
    "III",
    "IV",
    "V",
    "VI",
    "VII",
    "VIII",
    "IX",
    "X",
    "XI",
    "XII",
]


def _midpoint_angle(a: float, b: float) -> float:
    delta = (b - a + 540.0) % 360.0 - 180.0
    return _norm360(a + 0.5 * delta)


def render_chart_wheel(
    positions: dict[str, float],
    houses: list[float] | None = None,
    angles: dict[str, float] | None = None,
    options: WheelOptions | None = None,
    aspects_hits: list[dict] | None = None,
) -> str:
    """Return an SVG string for a basic chart wheel.

    - `positions`: name → longitude (deg)
    - `houses`: list of 12 house cusp longitudes (optional)
    - `options`: layout & visibility toggles
    - `aspects_hits`: precomputed aspects (optional); if None and show_aspects=True, compute using options.aspects & options.policy
    """
    opt = options or WheelOptions()
    size = opt.size
    cx = cy = size / 2
    outer_r = opt.ring_outer * size
    inner_r = opt.ring_inner * size

    svg: list[str] = []
    def add(el: str):
        svg.append(el)

    add(f"<svg xmlns='http://www.w3.org/2000/svg' width='{size}' height='{size}' viewBox='0 0 {size} {size}'>")
    add("<defs>\n<style><![CDATA[text{font-family:Inter,Arial,sans-serif;font-size:12px;dominant-baseline:middle}]]></style>\n</defs>")

    # Outer/inner rings
    add(f"<circle cx='{cx}' cy='{cy}' r='{outer_r}' fill='none' stroke='black' stroke-width='2' />")
    add(f"<circle cx='{cx}' cy='{cy}' r='{inner_r}' fill='none' stroke='black' stroke-width='1' />")

    # 12 signs (every 30 deg) and degree ticks
    for k in range(12):
        lon = k * 30.0
        ang = _lon_to_angle_svg(lon)
        x1, y1 = _pol2cart(ang, inner_r, cx, cy)
        x2, y2 = _pol2cart(ang, outer_r, cx, cy)
        add(f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}' stroke='black' stroke-width='1' />")
        # Label (♈︎ .. labels omitted for simplicity; show 0°,30°,... instead)
        lx, ly = _pol2cart(ang, outer_r + 16, cx, cy)
        add(f"<text x='{lx:.2f}' y='{ly:.2f}' text-anchor='middle'>{int(lon)}°</text>")

    if opt.show_degree_ticks:
        for deg in range(0, 360, 5):
            ang = _lon_to_angle_svg(deg)
            r1 = outer_r - (8 if deg % 30 == 0 else 4)
            x1, y1 = _pol2cart(ang, r1, cx, cy)
            x2, y2 = _pol2cart(ang, outer_r, cx, cy)
            add(f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}' stroke='black' stroke-width='0.5' opacity='0.6' />")

    # House lines (if provided)
    if opt.show_house_lines and houses and len(houses) >= 12:
        for idx, lon in enumerate(houses[:12]):
            ang = _lon_to_angle_svg(lon)
            x1, y1 = _pol2cart(ang, inner_r, cx, cy)
            x2, y2 = _pol2cart(ang, 0.05 * size, cx, cy)
            add(f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}' stroke='gray' stroke-width='1' opacity='0.6' />")
            lx, ly = _pol2cart(ang, inner_r - 18, cx, cy)
            label = ROMAN_NUMERALS[idx % 12]
            add(f"<text x='{lx:.2f}' y='{ly:.2f}' text-anchor='middle' fill='#333'>{label}</text>")

    if angles and "asc" in angles and "mc" in angles:
        asc = float(angles["asc"]) % 360.0
        mc = float(angles["mc"]) % 360.0
        desc = (asc + 180.0) % 360.0
        ic = (mc + 180.0) % 360.0
        for ang, label in ((asc, "ASC"), (mc, "MC")):
            svg_ang = _lon_to_angle_svg(ang)
            x1, y1 = _pol2cart(svg_ang, 0.05 * size, cx, cy)
            x2, y2 = _pol2cart(svg_ang, outer_r, cx, cy)
            add(f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}' stroke='black' stroke-width='2' opacity='0.8' />")
            tx, ty = _pol2cart(svg_ang, outer_r + 24, cx, cy)
            add(f"<text x='{tx:.2f}' y='{ty:.2f}' text-anchor='middle' font-weight='bold'>{label}</text>")
        for ang, label in ((desc, "DES"), (ic, "IC")):
            svg_ang = _lon_to_angle_svg(ang)
            x1, y1 = _pol2cart(svg_ang, 0.05 * size, cx, cy)
            x2, y2 = _pol2cart(svg_ang, outer_r, cx, cy)
            add(f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}' stroke='black' stroke-width='1' opacity='0.5' stroke-dasharray='4 4' />")
            tx, ty = _pol2cart(svg_ang, outer_r + 24, cx, cy)
            add(f"<text x='{tx:.2f}' y='{ty:.2f}' text-anchor='middle' fill='#555'>{label}</text>")

    # Aspect lines (optional)
    if opt.show_aspects:
        if aspects_hits is None:
            policy = opt.policy or {
                "per_object": {},
                "per_aspect": {
                    "conjunction": 8.0,
                    "opposition": 7.0,
                    "square": 6.0,
                    "trine": 6.0,
                    "sextile": 4.0,
                },
                "adaptive_rules": {},
            }
            aspects_hits = build_aspect_hits(positions, opt.aspects, policy)
        for h in aspects_hits or []:
            a_ang = _lon_to_angle_svg(positions[h["a"]])
            b_ang = _lon_to_angle_svg(positions[h["b"]])
            ax, ay = _pol2cart(a_ang, (inner_r + outer_r) / 2, cx, cy)
            bx, by = _pol2cart(b_ang, (inner_r + outer_r) / 2, cx, cy)
            add(f"<line x1='{ax:.2f}' y1='{ay:.2f}' x2='{bx:.2f}' y2='{by:.2f}' stroke='black' stroke-width='1' opacity='0.5' />")

    # Planet markers (text labels on the outer ring)
    for name, lon in positions.items():
        ang = _lon_to_angle_svg(float(lon))
        tx, ty = _pol2cart(ang, outer_r + 6, cx, cy)
        add(f"<text x='{tx:.2f}' y='{ty:.2f}' text-anchor='middle'>{name}</text>")

    names_lower = {name.lower(): name for name in positions.keys()}
    if "sun" in names_lower and "moon" in names_lower:
        sun_lon = positions[names_lower["sun"]]
        moon_lon = positions[names_lower["moon"]]
        sm_mid = _midpoint_angle(float(sun_lon), float(moon_lon))
        ang = _lon_to_angle_svg(sm_mid)
        tx, ty = _pol2cart(ang, outer_r - 20, cx, cy)
        add(f"<text x='{tx:.2f}' y='{ty:.2f}' text-anchor='middle' fill='#aa5500'>☀︎/☾ midpoint</text>")

    add("</svg>")
    return "".join(svg)
