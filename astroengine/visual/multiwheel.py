"""Rendering helpers for multi-wheel synastry compositions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from io import BytesIO
import math
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from astroengine.config.settings import MultiWheelCfg, Settings, SynastryCfg
from core.aspects_plus.harmonics import BASE_ASPECTS
from core.aspects_plus.matcher import angular_sep_deg
from core.aspects_plus.orb_policy import orb_limit


# ---------------------------------------------------------------------------
# Dataclasses describing composition inputs and computed geometry


@dataclass(slots=True)
class MultiWheelLayer:
    """Input payload for a single wheel layer."""

    label: str
    bodies: Mapping[str, float]
    houses: Sequence[float] | None = None
    declinations: Mapping[str, float] | None = None


@dataclass(slots=True)
class MultiWheelComposition:
    """High level description of a multi-wheel chart."""

    layers: Sequence[MultiWheelLayer]
    title: str | None = None
    subtitle: str | None = None


@dataclass(slots=True)
class MultiWheelOptions:
    """Runtime toggles for rendering multi-wheel layouts."""

    size: int = 820
    margin: int = 32
    wheel_count: int = 2
    show_aspects: bool = True
    aspect_set: Iterable[str] = (
        "conjunction",
        "opposition",
        "trine",
        "square",
        "sextile",
    )
    orb_policy: Mapping[str, Mapping[str, float]] | None = None
    show_house_overlay: bool = True
    show_declination_synastry: bool = False
    declination_orb: float = 1.0
    background: str = "#0f1115"
    palette: Sequence[str] = ("#f5f5f5", "#ffe082", "#80cbc4")


@dataclass(slots=True)
class BodyPoint:
    """Computed position for a body on a wheel."""

    name: str
    longitude: float
    angle: float
    x: float
    y: float


@dataclass(slots=True)
class HouseMarker:
    """Descriptor for a house cusp line and label."""

    angle: float
    inner_radius: float
    outer_radius: float
    label: str
    label_pos: Tuple[float, float]


@dataclass(slots=True)
class LayerGeometry:
    """Computed geometry for a single ring."""

    layer: MultiWheelLayer
    color: str
    radius_inner: float
    radius_outer: float
    body_points: Sequence[BodyPoint]
    house_markers: Sequence[HouseMarker]
    label_pos: Tuple[float, float]


@dataclass(slots=True)
class AspectLink:
    """Aspect connection drawn between two layers."""

    body_a: str
    body_b: str
    layer_a: int
    layer_b: int
    aspect: str
    orb: float
    point_a: Tuple[float, float]
    point_b: Tuple[float, float]


@dataclass(slots=True)
class DeclinationPair:
    """Declination pairing metadata."""

    body_a: str
    body_b: str
    layer_a: int
    layer_b: int
    difference: float


@dataclass(slots=True)
class MultiWheelRenderResult:
    """Container bundling layout and overlays."""

    layout: Sequence[LayerGeometry]
    aspects: Sequence[AspectLink]
    declination_pairs: Sequence[DeclinationPair]
    canvas_size: Tuple[int, int]


# ---------------------------------------------------------------------------
# Geometry helpers


_ROMAN = (
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
)


_ASPECT_COLORS = {
    "conjunction": "#ffab91",
    "opposition": "#90caf9",
    "square": "#ef9a9a",
    "trine": "#a5d6a7",
    "sextile": "#ce93d8",
}


def _norm360(value: float) -> float:
    v = value % 360.0
    return v + 360.0 if v < 0 else v


def _lon_to_angle_svg(lon: float) -> float:
    return _norm360(0.0 - lon)


def _pol2cart(angle_deg: float, r: float, cx: float, cy: float) -> Tuple[float, float]:
    a = math.radians(angle_deg)
    return cx + r * math.cos(a), cy - r * math.sin(a)


def _roman(idx: int) -> str:
    return _ROMAN[idx % 12]


def _resolve_options(
    options: MultiWheelOptions | None,
    settings: Settings | None,
    layer_count: int,
) -> MultiWheelOptions:
    base = options or MultiWheelOptions()
    cfg: MultiWheelCfg | None = None
    syn: SynastryCfg | None = None
    if settings is not None:
        cfg = getattr(settings, "multiwheel", None)
        syn = getattr(settings, "synastry", None)
        if cfg and not cfg.enabled:
            raise RuntimeError("Multi-wheel rendering disabled via settings.multiwheel")
    wheel_count = min(layer_count, max(1, base.wheel_count))
    if cfg is not None:
        wheel_count = min(wheel_count, max(1, cfg.max_wheels))
        show_house_overlay = base.show_house_overlay and cfg.house_overlay
    else:
        show_house_overlay = base.show_house_overlay
    show_decl = base.show_declination_synastry
    decl_orb = base.declination_orb
    if syn is not None:
        show_decl = show_decl and syn.declination
        decl_orb = syn.declination_orb if syn.declination_orb is not None else decl_orb
        if syn.house_overlay is not None:
            show_house_overlay = show_house_overlay and syn.house_overlay
    palette = base.palette
    if cfg and cfg.palette:
        palette = tuple(cfg.palette)
    policy = base.orb_policy
    if cfg and cfg.orb_policy:
        policy = cfg.orb_policy
    resolved = replace(
        base,
        wheel_count=wheel_count,
        show_house_overlay=show_house_overlay,
        show_declination_synastry=show_decl,
        declination_orb=float(decl_orb),
        palette=palette,
        orb_policy=policy,
    )
    return resolved


def _build_ring_radii(options: MultiWheelOptions) -> List[Tuple[float, float]]:
    count = max(1, options.wheel_count)
    outer = (options.size / 2) - options.margin
    core = max(options.size * 0.12, 40.0)
    usable = max(outer - core, 40.0)
    width = usable / count
    gap = width * 0.22
    radii: List[Tuple[float, float]] = []
    for idx in range(count):
        r_outer = outer - idx * width
        r_inner = max(core, r_outer - (width - gap))
        radii.append((r_inner, r_outer))
    return radii


def _build_body_points(
    layer: MultiWheelLayer,
    radius_inner: float,
    radius_outer: float,
    cx: float,
    cy: float,
) -> List[BodyPoint]:
    points: List[BodyPoint] = []
    mid_r = (radius_inner + radius_outer) / 2
    for name, lon in layer.bodies.items():
        angle = _lon_to_angle_svg(float(lon))
        x, y = _pol2cart(angle, mid_r, cx, cy)
        points.append(BodyPoint(name=name, longitude=float(lon), angle=angle, x=x, y=y))
    return points


def _build_house_markers(
    houses: Sequence[float] | None,
    radius_inner: float,
    radius_outer: float,
    cx: float,
    cy: float,
) -> List[HouseMarker]:
    markers: List[HouseMarker] = []
    if not houses or len(houses) < 12:
        return markers
    for idx, lon in enumerate(houses[:12]):
        angle = _lon_to_angle_svg(float(lon))
        x1, y1 = _pol2cart(angle, radius_inner, cx, cy)
        x2, y2 = _pol2cart(angle, radius_outer, cx, cy)
        lx, ly = _pol2cart(angle, radius_inner - 18, cx, cy)
        markers.append(
            HouseMarker(
                angle=angle,
                inner_radius=radius_inner,
                outer_radius=radius_outer,
                label=_roman(idx),
                label_pos=(lx, ly),
            )
        )
    return markers


def _build_declination_pairs(
    layers: Sequence[LayerGeometry],
    options: MultiWheelOptions,
) -> List[DeclinationPair]:
    pairs: List[DeclinationPair] = []
    if not options.show_declination_synastry:
        return pairs
    orb = float(options.declination_orb)
    for i, geo_a in enumerate(layers):
        decl_a = geo_a.layer.declinations or {}
        if not decl_a:
            continue
        for j in range(i + 1, len(layers)):
            decl_b = layers[j].layer.declinations or {}
            if not decl_b:
                continue
            for name_a, dec_a in decl_a.items():
                if name_a not in decl_b:
                    continue
                dec_b = float(decl_b[name_a])
                delta = abs(float(dec_a) - dec_b)
                if delta <= orb + 1e-6:
                    pairs.append(
                        DeclinationPair(
                            body_a=name_a,
                            body_b=name_a,
                            layer_a=i,
                            layer_b=j,
                            difference=delta,
                        )
                    )
    pairs.sort(key=lambda item: (item.difference, item.body_a.lower()))
    return pairs


def _aspect_policy(policy: Mapping[str, Mapping[str, float]] | None) -> Mapping[str, Mapping[str, float]]:
    if policy:
        return policy
    return {
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


def _build_aspect_links(
    geometries: Sequence[LayerGeometry],
    options: MultiWheelOptions,
    cx: float,
    cy: float,
) -> List[AspectLink]:
    links: List[AspectLink] = []
    if not options.show_aspects or len(geometries) < 2:
        return links
    policy = _aspect_policy(options.orb_policy)
    aspects = [asp.lower() for asp in options.aspect_set if asp.lower() in BASE_ASPECTS]
    if not aspects:
        return links
    for i, geo_a in enumerate(geometries):
        points_a = {bp.name: bp for bp in geo_a.body_points}
        if not points_a:
            continue
        for j in range(i + 1, len(geometries)):
            geo_b = geometries[j]
            points_b = {bp.name: bp for bp in geo_b.body_points}
            if not points_b:
                continue
            for name_a, point_a in points_a.items():
                lon_a = point_a.longitude
                for name_b, point_b in points_b.items():
                    lon_b = point_b.longitude
                    delta = angular_sep_deg(lon_a, lon_b)
                    best: MutableMapping[str, float] | None = None
                    for asp in aspects:
                        ang = BASE_ASPECTS[asp]
                        orb = abs(delta - float(ang))
                        limit = orb_limit(name_a, name_b, asp, policy)
                        if orb <= limit + 1e-9:
                            candidate: MutableMapping[str, float] = {
                                "aspect": asp,
                                "orb": float(orb),
                                "limit": float(limit),
                            }
                            if best is None or candidate["orb"] < best["orb"]:
                                best = candidate
                    if best is None:
                        continue
                    ax, ay = point_a.x, point_a.y
                    bx, by = point_b.x, point_b.y
                    links.append(
                        AspectLink(
                            body_a=name_a,
                            body_b=name_b,
                            layer_a=i,
                            layer_b=j,
                            aspect=str(best["aspect"]),
                            orb=float(best["orb"]),
                            point_a=(ax, ay),
                            point_b=(bx, by),
                        )
                    )
    links.sort(key=lambda l: (l.aspect, l.orb, l.body_a, l.body_b))
    return links


def build_multiwheel_layout(
    composition: MultiWheelComposition,
    options: MultiWheelOptions | None = None,
    settings: Settings | None = None,
) -> MultiWheelRenderResult:
    """Compute geometry for the provided composition."""

    resolved = _resolve_options(options, settings, len(composition.layers))
    cx = cy = resolved.size / 2
    radii = _build_ring_radii(resolved)
    geometries: List[LayerGeometry] = []
    palette_cycle = list(resolved.palette) or ["#ffffff"]
    for idx in range(min(len(radii), len(composition.layers))):
        layer = composition.layers[idx]
        radius_inner, radius_outer = radii[idx]
        color = palette_cycle[idx % len(palette_cycle)]
        body_points = _build_body_points(layer, radius_inner, radius_outer, cx, cy)
        house_markers = (
            _build_house_markers(layer.houses, radius_inner, radius_outer, cx, cy)
            if resolved.show_house_overlay
            else []
        )
        label_pos = (cx, cy + radius_inner - 20)
        geometries.append(
            LayerGeometry(
                layer=layer,
                color=color,
                radius_inner=radius_inner,
                radius_outer=radius_outer,
                body_points=tuple(body_points),
                house_markers=tuple(house_markers),
                label_pos=label_pos,
            )
        )
    aspects = _build_aspect_links(geometries, resolved, cx, cy)
    decl_pairs = _build_declination_pairs(geometries, resolved)
    canvas_height = int(resolved.size + resolved.margin * 2 + (90 if decl_pairs else 0))
    canvas_width = int(resolved.size + resolved.margin * 2)
    return MultiWheelRenderResult(
        layout=tuple(geometries),
        aspects=tuple(aspects),
        declination_pairs=tuple(decl_pairs),
        canvas_size=(canvas_width, canvas_height),
    )


# ---------------------------------------------------------------------------
# SVG rendering


def render_multiwheel_svg(
    composition: MultiWheelComposition,
    options: MultiWheelOptions | None = None,
    settings: Settings | None = None,
) -> str:
    """Render the composition as an SVG string."""

    result = build_multiwheel_layout(composition, options, settings)
    resolved = _resolve_options(options, settings, len(composition.layers))
    width, height = result.canvas_size
    svg: List[str] = []
    svg.append(
        (
            "<svg xmlns='http://www.w3.org/2000/svg' "
            f"width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"
        )
    )
    svg.append(
        "<defs>\n<style><![CDATA[text{font-family:Inter,Arial,sans-serif;}]]>"
        "</style>\n</defs>"
    )
    svg.append(
        f"<rect x='0' y='0' width='{width}' height='{height}' fill='{resolved.background}'/>"
    )
    center = resolved.size / 2
    offset = resolved.margin
    svg.append(
        f"<g transform='translate({offset},{offset})'>"
    )
    if composition.title:
        svg.append(
            f"<text x='{center}' y='28' fill='#eceff1' text-anchor='middle' font-size='20' font-weight='600'>{composition.title}</text>"
        )
    if composition.subtitle:
        svg.append(
            f"<text x='{center}' y='52' fill='#b0bec5' text-anchor='middle' font-size='14'>{composition.subtitle}</text>"
        )
    # Draw rings
    for idx, geo in enumerate(result.layout):
        outer = geo.radius_outer
        inner = geo.radius_inner
        svg.append(
            f"<circle cx='{center}' cy='{center}' r='{outer:.2f}' fill='none' stroke='{geo.color}' stroke-width='2' opacity='0.85'/>"
        )
        svg.append(
            f"<circle cx='{center}' cy='{center}' r='{inner:.2f}' fill='none' stroke='{geo.color}' stroke-width='1' opacity='0.35'/>"
        )
        # Body markers
        for point in geo.body_points:
            svg.append(
                f"<circle cx='{point.x:.2f}' cy='{point.y:.2f}' r='4' fill='{geo.color}' stroke='#1e272e' stroke-width='1'/>"
            )
            tx, ty = _pol2cart(point.angle, geo.radius_outer + 20, center, center)
            svg.append(
                f"<text x='{tx:.2f}' y='{ty:.2f}' text-anchor='middle' fill='{geo.color}' font-size='12'>{point.name}</text>"
            )
        if geo.house_markers:
            for marker in geo.house_markers:
                x1, y1 = _pol2cart(marker.angle, marker.inner_radius, center, center)
                x2, y2 = _pol2cart(marker.angle, marker.outer_radius, center, center)
                svg.append(
                    f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}' stroke='{geo.color}' stroke-width='0.8' opacity='0.4'/>"
                )
                lx, ly = marker.label_pos
                svg.append(
                    f"<text x='{lx:.2f}' y='{ly:.2f}' text-anchor='middle' fill='{geo.color}' font-size='11' opacity='0.7'>{marker.label}</text>"
                )
        label_x, label_y = geo.label_pos
        svg.append(
            f"<text x='{label_x:.2f}' y='{label_y:.2f}' text-anchor='middle' fill='{geo.color}' font-size='13' font-weight='600'>{geo.layer.label}</text>"
        )
    # Aspect lines
    if result.aspects:
        for link in result.aspects:
            color = _ASPECT_COLORS.get(link.aspect, "#9e9e9e")
            x1, y1 = link.point_a
            x2, y2 = link.point_b
            svg.append(
                f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}' stroke='{color}' stroke-width='1.2' opacity='0.6'/>"
            )
    svg.append("</g>")
    if result.declination_pairs:
        block_y = resolved.size + resolved.margin - 10
        svg.append(
            f"<g transform='translate({resolved.margin},{block_y})'>"
        )
        svg.append(
            "<rect x='0' y='0' width='{width}' height='90' fill='rgba(38,50,56,0.65)' rx='8'/>".format(
                width=resolved.size
            )
        )
        svg.append(
            "<text x='{x}' y='26' fill='#eceff1' font-size='14' font-weight='600'>Declination matches (≤ {orb:.1f}°)</text>".format(
                x=resolved.size / 2,
                orb=resolved.declination_orb,
            )
        )
        line_y = 46
        for pair in result.declination_pairs:
            svg.append(
                "<text x='{x}' y='{y}' fill='#cfd8dc' font-size='12'>{label}</text>".format(
                    x=resolved.size / 2,
                    y=line_y,
                    label=f"{pair.body_a}: Δ{pair.difference:.2f}° (layers {pair.layer_a + 1}/{pair.layer_b + 1})",
                )
            )
            line_y += 18
        svg.append("</g>")
    svg.append("</svg>")
    return "".join(svg)


# ---------------------------------------------------------------------------
# PNG rendering


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size=size)
    except OSError:  # pragma: no cover - font availability varies
        return ImageFont.load_default()


def _measure(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> Tuple[float, float]:
    if not text:
        return 0.0, 0.0
    bbox = draw.textbbox((0, 0), text, font=font)
    return float(bbox[2] - bbox[0]), float(bbox[3] - bbox[1])


def render_multiwheel_png(
    composition: MultiWheelComposition,
    options: MultiWheelOptions | None = None,
    settings: Settings | None = None,
) -> bytes:
    """Render the composition into a PNG buffer."""

    result = build_multiwheel_layout(composition, options, settings)
    resolved = _resolve_options(options, settings, len(composition.layers))
    width, height = result.canvas_size
    img = Image.new("RGBA", (width, height), resolved.background)
    draw = ImageDraw.Draw(img)
    cx = cy = resolved.size / 2 + resolved.margin

    # Titles
    title_font = _font(20)
    subtitle_font = _font(14)
    if composition.title:
        tw, th = _measure(draw, composition.title, title_font)
        draw.text((cx - tw / 2, resolved.margin / 2), composition.title, fill="#eceff1", font=title_font)
    if composition.subtitle:
        sw, sh = _measure(draw, composition.subtitle, subtitle_font)
        draw.text((cx - sw / 2, resolved.margin / 2 + 24), composition.subtitle, fill="#b0bec5", font=subtitle_font)

    # Rings and markers
    for geo in result.layout:
        outer = geo.radius_outer
        inner = geo.radius_inner
        bbox_outer = (
            cx - outer,
            cy - outer,
            cx + outer,
            cy + outer,
        )
        bbox_inner = (
            cx - inner,
            cy - inner,
            cx + inner,
            cy + inner,
        )
        draw.ellipse(bbox_outer, outline=geo.color, width=2)
        draw.ellipse(bbox_inner, outline=geo.color, width=1)
        label_font = _font(13)
        label_x = geo.label_pos[0] + resolved.margin
        label_y = geo.label_pos[1] + resolved.margin
        lw, lh = _measure(draw, geo.layer.label, label_font)
        draw.text((label_x - lw / 2, label_y - lh / 2), geo.layer.label, fill=geo.color, font=label_font)
        for marker in geo.house_markers:
            x1, y1 = _pol2cart(marker.angle, marker.inner_radius, cx, cy)
            x2, y2 = _pol2cart(marker.angle, marker.outer_radius, cx, cy)
            draw.line((x1, y1, x2, y2), fill=geo.color, width=1)
            label_font_small = _font(11)
            lw2, lh2 = _measure(draw, marker.label, label_font_small)
            draw.text(
                (
                    marker.label_pos[0] + resolved.margin - lw2 / 2,
                    marker.label_pos[1] + resolved.margin - lh2 / 2,
                ),
                marker.label,
                fill=geo.color,
                font=label_font_small,
            )
        body_font = _font(12)
        for point in geo.body_points:
            bx, by = point.x + resolved.margin, point.y + resolved.margin
            draw.ellipse((bx - 3, by - 3, bx + 3, by + 3), fill=geo.color, outline="#1e272e")
            tx, ty = _pol2cart(point.angle, geo.radius_outer + 20, cx, cy)
            tw, th = _measure(draw, point.name, body_font)
            draw.text((tx - tw / 2, ty - th / 2), point.name, fill=geo.color, font=body_font)

    if result.aspects:
        for link in result.aspects:
            color = _ASPECT_COLORS.get(link.aspect, "#9e9e9e")
            x1, y1 = link.point_a
            x2, y2 = link.point_b
            draw.line(
                (
                    x1 + resolved.margin,
                    y1 + resolved.margin,
                    x2 + resolved.margin,
                    y2 + resolved.margin,
                ),
                fill=color,
                width=2,
            )

    if result.declination_pairs:
        block_top = resolved.size + resolved.margin - 10
        draw.rectangle(
            (resolved.margin, block_top, resolved.margin + resolved.size, block_top + 90),
            fill=(38, 50, 56, 180),
            outline=None,
        )
        header_font = _font(14)
        header = f"Declination matches (≤ {resolved.declination_orb:.1f}°)"
        hw, hh = _measure(draw, header, header_font)
        draw.text((cx - hw / 2, block_top + 10), header, fill="#eceff1", font=header_font)
        line_y = block_top + 32
        entry_font = _font(12)
        for pair in result.declination_pairs:
            label = f"{pair.body_a}: Δ{pair.difference:.2f}° (layers {pair.layer_a + 1}/{pair.layer_b + 1})"
            lw, lh = _measure(draw, label, entry_font)
            draw.text((cx - lw / 2, line_y), label, fill="#cfd8dc", font=entry_font)
            line_y += lh + 4

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Export helper


def export_multiwheel(
    composition: MultiWheelComposition,
    options: MultiWheelOptions | None = None,
    settings: Settings | None = None,
    fmt: str = "svg",
) -> bytes:
    """Export the composition as SVG or PNG bytes."""

    fmt_lower = fmt.lower()
    if fmt_lower == "svg":
        return render_multiwheel_svg(composition, options, settings).encode("utf-8")
    if fmt_lower == "png":
        return render_multiwheel_png(composition, options, settings)
    raise ValueError("Unsupported format: expected 'svg' or 'png'")


__all__ = [
    "MultiWheelLayer",
    "MultiWheelComposition",
    "MultiWheelOptions",
    "MultiWheelRenderResult",
    "build_multiwheel_layout",
    "render_multiwheel_svg",
    "render_multiwheel_png",
    "export_multiwheel",
]
