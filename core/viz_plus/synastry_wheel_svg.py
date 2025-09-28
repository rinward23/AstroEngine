"""SVG renderer for dual-ring synastry wheels (Spec B-009)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Iterable, Sequence

import math

# External mapping reused for aspect degree resolution
from core.aspects_plus.harmonics import BASE_ASPECTS

# ---------------------------------------------------------------------------
# Constants & helpers

ASPECT_FAMILY: dict[int, str] = {
    0: "neutral",
    30: "neutral",
    45: "challenging",
    60: "harmonious",
    72: "harmonious",
    90: "challenging",
    120: "harmonious",
    135: "challenging",
    144: "harmonious",
    150: "challenging",
    180: "challenging",
}

MAJOR_ASPECTS = {0, 60, 90, 120, 180}
MINOR_ASPECTS = {30, 45, 72, 135, 144, 150}

ASPECT_SYMBOL = {
    0: "☌",
    30: "◦30",
    45: "◦45",
    60: "✶",
    72: "◦72",
    90: "□",
    120: "△",
    135: "◦135",
    144: "◦144",
    150: "◦150",
    180: "☍",
}

THEME_COLORS = {
    "light": {
        "harmonious": "#1d6fb8",
        "challenging": "#c62828",
        "neutral": "#5f6368",
    },
    "dark": {
        "harmonious": "#7ad3ff",
        "challenging": "#ff8a8a",
        "neutral": "#cfcfcf",
    },
}


def _to_xy(cx: float, cy: float, radius: float, lon: float) -> tuple[float, float]:
    theta = math.radians(lon)
    return cx + radius * math.cos(theta), cy - radius * math.sin(theta)


def _norm_lon(lon: float) -> float:
    value = lon % 360.0
    return value + 360.0 if value < 0 else value


def _midpoint_lon(a: float, b: float) -> float:
    delta = ((b - a + 180.0) % 360.0) - 180.0
    return _norm_lon(a + 0.5 * delta)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _family_for(aspect: int) -> str:
    return ASPECT_FAMILY.get(aspect, "neutral")


def _color_for(aspect: int, theme: str) -> str:
    palette = THEME_COLORS.get(theme, THEME_COLORS["light"])
    family = _family_for(aspect)
    return palette.get(family, palette["neutral"])


def _stroke_dash(aspect: int) -> str | None:
    return "4 3" if aspect in MINOR_ASPECTS else None


def _family_filter_set(families: Iterable[str] | None) -> set[str]:
    if not families:
        return {"harmonious", "challenging", "neutral"}
    return {fam for fam in families if fam in {"harmonious", "challenging", "neutral"}}


def _collision_shim(positions: Sequence[tuple[str, float]], min_sep: float = 3.0) -> dict[str, float]:
    """Return adjusted longitudes for labels to avoid tight overlaps."""

    if not positions:
        return {}
    sorted_items = sorted(((name, _norm_lon(lon)) for name, lon in positions), key=lambda item: item[1])
    adjusted: dict[str, float] = {}
    last_lon: float | None = None
    for idx, (name, lon) in enumerate(sorted_items):
        candidate = lon
        if last_lon is not None:
            delta = candidate - last_lon
            if delta < min_sep:
                candidate = last_lon + min_sep
        adjusted[name] = candidate
        last_lon = candidate

    # Wrap-around correction for first element if necessary
    first_name, first_lon = sorted_items[0]
    if len(sorted_items) > 1:
        last_name, last_adj = sorted_items[-1][0], adjusted[sorted_items[-1][0]]
        span = (last_adj - adjusted[first_name])
        if span > 360.0:
            shift = span - 360.0
            adjusted[first_name] += shift

    return {name: lon % 360.0 for name, lon in adjusted.items()}


# ---------------------------------------------------------------------------
# Options


@dataclass(slots=True)
class SynastryWheelOptions:
    size: int = 640
    w_min: float = 0.6
    w_max: float = 3.0
    opacity_min: float = 0.35
    opacity_max: float = 0.95
    show_labels: bool = True
    show_degree_ticks: bool = True
    show_majors: bool = True
    show_minors: bool = True
    families: Iterable[str] | None = None
    top_k: int | None = None
    label_top_k: int | None = 10
    show_aspect_labels: bool = True
    theme: str = "light"
    midpoint_pairs: Sequence[tuple[str, str]] = ()


# ---------------------------------------------------------------------------
# Rendering


def _resolve_aspect(value: object) -> int | None:
    if isinstance(value, (int, float)):
        return int(round(float(value)))
    if isinstance(value, str):
        degree = BASE_ASPECTS.get(value.lower())
        if degree is None:
            return None
        return int(round(float(degree)))
    return None


def _coerce_hit(entry: object) -> tuple[str, str, int, float, float] | None:
    body_a: str | None = None
    body_b: str | None = None
    aspect_value: object | None = None
    severity_value: object | None = None
    offset_value: object | None = None

    if isinstance(entry, Mapping):
        body_a = entry.get("bodyA") or entry.get("a") or entry.get("from")
        body_b = entry.get("bodyB") or entry.get("b") or entry.get("to")
        aspect_value = entry.get("aspect")
        severity_value = entry.get("severity")
        offset_value = entry.get("offset")
        if offset_value is None:
            delta = entry.get("delta")
            angle = entry.get("angle")
            if delta is not None and angle is not None:
                offset_value = float(delta) - float(angle)
    else:
        try:
            body_a, body_b, aspect_value, severity_value, offset_value = entry  # type: ignore[misc]
        except (TypeError, ValueError):
            return None

    if body_a is None or body_b is None or aspect_value is None or severity_value is None:
        return None

    aspect_deg = _resolve_aspect(aspect_value)
    if aspect_deg is None:
        return None

    offset = float(offset_value) if offset_value is not None else 0.0
    return str(body_a), str(body_b), aspect_deg, float(severity_value), offset


def render_synastry_wheel_svg(
    wheel_a: Sequence[tuple[str, float]] | Mapping[str, float],
    wheel_b: Sequence[tuple[str, float]] | Mapping[str, float],
    hits: Sequence[object],
    options: SynastryWheelOptions | None = None,
) -> str:
    """Render a dual-ring synastry wheel as an SVG string."""

    opt = options or SynastryWheelOptions()
    size = opt.size
    cx = cy = size / 2.0
    zodiac_radius = size * 0.46
    radius_a = zodiac_radius * 0.62
    radius_b = zodiac_radius * 0.86

    if isinstance(wheel_a, Mapping):
        seq_a = list(wheel_a.items())
    else:
        seq_a = list(wheel_a)
    if isinstance(wheel_b, Mapping):
        seq_b = list(wheel_b.items())
    else:
        seq_b = list(wheel_b)

    lon_a = {name: float(lon) for name, lon in seq_a}
    lon_b = {name: float(lon) for name, lon in seq_b}

    label_lon_a = _collision_shim(seq_a)
    label_lon_b = _collision_shim(seq_b)

    fam_filter = _family_filter_set(opt.families)

    filtered_hits: list[tuple[str, str, int, float, float]] = []
    for hit in hits:
        coerced = _coerce_hit(hit)
        if coerced is None:
            continue
        body_a, body_b, aspect, severity, offset = coerced
        if aspect not in ASPECT_FAMILY:
            continue
        family = _family_for(aspect)
        if family not in fam_filter:
            continue
        is_minor = aspect in MINOR_ASPECTS
        if is_minor and not opt.show_minors:
            continue
        if (not is_minor) and not opt.show_majors:
            continue
        filtered_hits.append((body_a, body_b, aspect, _clamp01(float(severity)), float(offset)))

    filtered_hits.sort(key=lambda item: item[3], reverse=True)
    if opt.top_k is not None:
        filtered_hits = filtered_hits[: opt.top_k]

    # Layer ordering: draw lower severity first, minors before majors
    layered = sorted(
        filtered_hits,
        key=lambda item: (
            0 if item[2] in MINOR_ASPECTS else 1,
            item[3],
            item[0],
            item[1],
            item[2],
        ),
    )

    svg_parts: list[str] = []

    def emit(fragment: str) -> None:
        svg_parts.append(fragment)

    emit(
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{size}' height='{size}' viewBox='0 0 {size} {size}'>"
    )
    emit(
        "<defs><style><![CDATA[text{font-family:Inter,Arial,sans-serif;dominant-baseline:middle;font-size:12px}]]>"
        "</style></defs>"
    )

    # Zodiac ring
    emit(
        f"<circle cx='{cx:.2f}' cy='{cy:.2f}' r='{zodiac_radius:.2f}' fill='none' stroke='var(--wheel-zodiac-stroke,#616161)' stroke-width='1.2'/>"
    )

    # Major sign lines & labels every 30°
    for sector in range(12):
        lon = sector * 30.0
        x1, y1 = _to_xy(cx, cy, radius_a * 0.92, lon)
        x2, y2 = _to_xy(cx, cy, zodiac_radius, lon)
        emit(
            f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}' stroke='var(--wheel-zodiac-stroke,#757575)' stroke-width='1'/>"
        )
        label_x, label_y = _to_xy(cx, cy, zodiac_radius + 18.0, lon)
        emit(
            f"<text x='{label_x:.2f}' y='{label_y:.2f}' text-anchor='middle' fill='var(--wheel-label,#424242)'>"
            f"{int(lon)}°</text>"
        )

    # Minor ticks
    if opt.show_degree_ticks:
        for deg in range(0, 360, 5):
            x1, y1 = _to_xy(cx, cy, zodiac_radius - (10 if deg % 30 == 0 else 5), deg)
            x2, y2 = _to_xy(cx, cy, zodiac_radius, deg)
            emit(
                f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}' stroke='var(--wheel-tick,#9e9e9e)' stroke-width='0.6' opacity='0.7'/>"
            )

    # Aspect lines
    for body_a, body_b, aspect, severity, offset in layered:
        lon1 = lon_a.get(body_a)
        lon2 = lon_b.get(body_b)
        if lon1 is None or lon2 is None:
            continue
        x1, y1 = _to_xy(cx, cy, radius_a, lon1)
        x2, y2 = _to_xy(cx, cy, radius_b, lon2)
        stroke = _color_for(aspect, opt.theme)
        stroke_width = opt.w_min + severity * (opt.w_max - opt.w_min)
        opacity = opt.opacity_min + severity * (opt.opacity_max - opt.opacity_min)
        dash = _stroke_dash(aspect)
        title = (
            f"{body_a} – {body_b} • {aspect}°" f" • offset {offset:+.2f}° • severity {severity:.2f}"
        )
        emit("<g>")
        emit(f"<title>{title}</title>")
        dash_attr = f" stroke-dasharray='{dash}'" if dash else ""
        emit(
            f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}' stroke='{stroke}' stroke-width='{stroke_width:.2f}' stroke-opacity='{opacity:.2f}'{dash_attr}/>")
        emit("</g>")

    # Aspect labels near chord midpoints (top severity selection)
    if opt.show_aspect_labels and filtered_hits:
        label_budget = opt.label_top_k if opt.label_top_k is not None else len(filtered_hits)
        label_hits = filtered_hits[:label_budget]
        used_positions: list[tuple[float, float]] = []
        for body_a, body_b, aspect, severity, _ in label_hits:
            lon1 = lon_a.get(body_a)
            lon2 = lon_b.get(body_b)
            if lon1 is None or lon2 is None:
                continue
            x1, y1 = _to_xy(cx, cy, radius_a, lon1)
            x2, y2 = _to_xy(cx, cy, radius_b, lon2)
            mid_x = (x1 + x2) / 2.0
            mid_y = (y1 + y2) / 2.0
            # simple collision shim: nudge label if too close to previous ones
            for existing_x, existing_y in used_positions:
                if (existing_x - mid_x) ** 2 + (existing_y - mid_y) ** 2 < 20**2:
                    mid_y -= 18
                    break
            used_positions.append((mid_x, mid_y))
            emit(
                f"<text x='{mid_x:.2f}' y='{mid_y:.2f}' text-anchor='middle' fill='{_color_for(aspect, opt.theme)}' font-size='11'>"
                f"{ASPECT_SYMBOL.get(aspect, aspect)}</text>"
            )

    # Ring glyphs for chart A & B
    if opt.show_labels:
        for name, lon in lon_a.items():
            disp_lon = label_lon_a.get(name, lon)
            x, y = _to_xy(cx, cy, radius_a, disp_lon)
            emit(
                f"<text x='{x:.2f}' y='{y:.2f}' text-anchor='middle' fill='var(--wheel-bodyA,#1b5e20)' font-size='13'>{name}</text>"
            )
        for name, lon in lon_b.items():
            disp_lon = label_lon_b.get(name, lon)
            x, y = _to_xy(cx, cy, radius_b, disp_lon)
            emit(
                f"<text x='{x:.2f}' y='{y:.2f}' text-anchor='middle' fill='var(--wheel-bodyB,#0d47a1)' font-size='13'>{name}</text>"
            )

    # Midpoint axes
    for body_a, body_b in opt.midpoint_pairs:
        lon1 = lon_a.get(body_a)
        lon2 = lon_b.get(body_b)
        if lon1 is None or lon2 is None:
            continue
        mid = _midpoint_lon(lon1, lon2)
        outer_x, outer_y = _to_xy(cx, cy, zodiac_radius + 8.0, mid)
        inner_x, inner_y = _to_xy(cx, cy, radius_a - 8.0, mid)
        emit(
            f"<line x1='{outer_x:.2f}' y1='{outer_y:.2f}' x2='{inner_x:.2f}' y2='{inner_y:.2f}' stroke='var(--wheel-midpoint,#9e9e9e)' stroke-width='1' stroke-dasharray='2 3'/>"
        )
        emit(
            f"<text x='{outer_x:.2f}' y='{outer_y - 10:.2f}' text-anchor='middle' font-size='10' fill='var(--wheel-midpoint,#9e9e9e)'>{body_a}+{body_b}</text>"
        )

    # Legend (family colors)
    legend_y = size - 40
    legend_x = 30
    emit("<g>")
    emit(
        f"<rect x='{legend_x - 20}' y='{legend_y - 18}' width='200' height='32' rx='6' fill='var(--wheel-legend-bg,rgba(250,250,250,0.85))' stroke='var(--wheel-legend-border,#bdbdbd)' stroke-width='0.6'/>"
    )
    step = 65
    for idx, family in enumerate(("harmonious", "challenging", "neutral")):
        color = _color_for(60 if family == "harmonious" else 90 if family == "challenging" else 0, opt.theme)
        x = legend_x + idx * step
        emit(
            f"<circle cx='{x:.2f}' cy='{legend_y:.2f}' r='6' fill='{color}' stroke='none'/>"
        )
        emit(
            f"<text x='{x + 16:.2f}' y='{legend_y:.2f}' fill='var(--wheel-label,#424242)' text-anchor='start' font-size='11'>{family.title()}</text>"
        )
    emit("</g>")

    emit("</svg>")
    return "".join(svg_parts)


__all__ = ["SynastryWheelOptions", "render_synastry_wheel_svg"]

