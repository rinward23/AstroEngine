"""Render time-altitude and polar azimuth diagrams for topocentric tracks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from io import BytesIO
import math
from typing import Iterable, Sequence

from ...ephemeris.adapter import EphemerisAdapter, ObserverLocation
from ...core.dependencies import require_dependency
from .events import rise_set_times, transit_time
from .topocentric import MetConditions, horizontal_from_equatorial, topocentric_equatorial

try:  # pragma: no cover - optional Swiss Ephemeris dependency
    import swisseph as swe
except ModuleNotFoundError:  # pragma: no cover
    swe = None

_SUN_ID = getattr(swe, "SUN", 0)


@lru_cache(maxsize=1)
def _pillow_modules():
    """Return Pillow modules required for PNG rendering."""

    image = require_dependency(
        "PIL.Image",
        package="Pillow",
        extras=("reports", "ui"),
        purpose="render observational diagrams as PNG",
    )
    image_draw = require_dependency(
        "PIL.ImageDraw",
        package="Pillow",
        extras=("reports", "ui"),
        purpose="render observational diagrams as PNG",
    )
    image_font = require_dependency(
        "PIL.ImageFont",
        package="Pillow",
        extras=("reports", "ui"),
        purpose="render observational diagrams as PNG",
    )
    return image, image_draw, image_font


@dataclass(frozen=True)
class AltAzDiagram:
    """Rendered Alt/Az diagram in SVG and (optionally) PNG form."""

    svg: str
    png: bytes | None
    metadata: dict[str, object]


@dataclass(frozen=True)
class AltAzSample:
    moment: datetime
    altitude_deg: float
    azimuth_deg: float
    sun_altitude_deg: float


def render_altaz_diagram(
    adapter: EphemerisAdapter,
    body: int,
    start: datetime,
    end: datetime,
    observer: ObserverLocation,
    *,
    refraction: bool = True,
    met: MetConditions | None = None,
    horizon_dip_deg: float = 0.0,
    step_seconds: int = 300,
    include_png: bool = True,
) -> AltAzDiagram:
    """Render an Alt/Az diagram for ``body`` between ``start`` and ``end``."""

    if start >= end:
        raise ValueError("start must precede end")
    met = met or MetConditions()
    samples = list(
        _sample_track(
            adapter,
            body,
            start,
            end,
            observer,
            refraction=refraction,
            met=met,
            horizon_dip_deg=horizon_dip_deg,
            step_seconds=max(60, step_seconds),
        )
    )
    rise, set_ = _collect_rise_set(adapter, body, start, end, observer)
    transit = _collect_transit(adapter, body, start, end, observer)
    svg = _render_svg(samples, rise, set_, transit, start, end)
    png_bytes = _render_png(samples, rise, set_, transit, start, end) if include_png else None
    metadata = {
        "count": len(samples),
        "rise": rise.isoformat() if rise else None,
        "set": set_.isoformat() if set_ else None,
        "transit": transit.isoformat() if transit else None,
    }
    return AltAzDiagram(svg=svg, png=png_bytes, metadata=metadata)


def _sample_track(
    adapter: EphemerisAdapter,
    body: int,
    start: datetime,
    end: datetime,
    observer: ObserverLocation,
    *,
    refraction: bool,
    met: MetConditions,
    horizon_dip_deg: float,
    step_seconds: int,
) -> Iterable[AltAzSample]:
    step = timedelta(seconds=step_seconds)
    moment = start.astimezone(UTC) if start.tzinfo else start.replace(tzinfo=UTC)
    finish = end.astimezone(UTC) if end.tzinfo else end.replace(tzinfo=UTC)
    while moment <= finish:
        equ = topocentric_equatorial(adapter, body, moment, observer)
        horiz = horizontal_from_equatorial(
            equ.right_ascension_deg,
            equ.declination_deg,
            moment,
            observer,
            refraction=refraction,
            met=met,
            horizon_dip_deg=horizon_dip_deg,
        )
        sun_equ = topocentric_equatorial(adapter, _SUN_ID, moment, observer)
        sun_horiz = horizontal_from_equatorial(
            sun_equ.right_ascension_deg,
            sun_equ.declination_deg,
            moment,
            observer,
            refraction=refraction,
            met=met,
            horizon_dip_deg=horizon_dip_deg,
        )
        yield AltAzSample(moment, horiz.altitude_deg, horiz.azimuth_deg, sun_horiz.altitude_deg)
        moment += step


def _collect_rise_set(
    adapter: EphemerisAdapter,
    body: int,
    start: datetime,
    end: datetime,
    observer: ObserverLocation,
) -> tuple[datetime | None, datetime | None]:
    days = _days_spanning(start, end)
    rise: datetime | None = None
    set_: datetime | None = None
    for day in days:
        r, s = rise_set_times(adapter, body, day, observer)
        if r is not None and start <= r <= end:
            rise = r
        if s is not None and start <= s <= end:
            set_ = s
    return rise, set_


def _collect_transit(
    adapter: EphemerisAdapter,
    body: int,
    start: datetime,
    end: datetime,
    observer: ObserverLocation,
) -> datetime | None:
    days = _days_spanning(start, end)
    for day in days:
        transit = transit_time(adapter, body, day, observer)
        if transit is None:
            continue
        if start <= transit <= end:
            return transit
    return None


def _days_spanning(start: datetime, end: datetime) -> list[datetime]:
    base = (start.astimezone(UTC) if start.tzinfo else start.replace(tzinfo=UTC)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end_utc = end.astimezone(UTC) if end.tzinfo else end.replace(tzinfo=UTC)
    days = [base - timedelta(days=1), base, base + timedelta(days=1)]
    if (base + timedelta(days=2)) <= end_utc + timedelta(days=1):
        days.append(base + timedelta(days=2))
    return days


def _render_svg(
    samples: Sequence[AltAzSample],
    rise: datetime | None,
    set_: datetime | None,
    transit: datetime | None,
    start: datetime,
    end: datetime,
) -> str:
    width = 900
    height = 580
    margin_left = 70
    margin_top = 50
    plot_width = width - margin_left - 40
    plot_height = 260
    polar_center_x = margin_left + plot_width / 2
    polar_center_y = margin_top + plot_height + 220
    polar_radius = 160

    if not samples:
        return "<svg xmlns='http://www.w3.org/2000/svg' width='900' height='580'></svg>"

    altitudes = [s.altitude_deg for s in samples]
    sun_altitudes = [s.sun_altitude_deg for s in samples]
    min_alt = min(min(altitudes), -10.0)
    max_alt = max(max(altitudes), 90.0)
    alt_range = max_alt - min_alt or 1.0

    def x_pos(moment: datetime) -> float:
        span = (end - start).total_seconds()
        if span == 0:
            return margin_left
        return margin_left + ((moment - start).total_seconds() / span) * plot_width

    def y_pos(alt: float) -> float:
        return margin_top + plot_height - ((alt - min_alt) / alt_range) * plot_height

    path_points = " ".join(
        f"{x_pos(s.moment):.2f},{y_pos(s.altitude_deg):.2f}" for s in samples
    )

    twilight = _twilight_polygons(samples, x_pos, margin_top, plot_height)

    rise_line = (
        f"<line x1='{x_pos(rise):.2f}' y1='{margin_top}' x2='{x_pos(rise):.2f}' y2='{margin_top + plot_height}' "
        f"stroke='#4caf50' stroke-dasharray='6 4'/>"
        if rise
        else ""
    )
    set_line = (
        f"<line x1='{x_pos(set_):.2f}' y1='{margin_top}' x2='{x_pos(set_):.2f}' y2='{margin_top + plot_height}' "
        f"stroke='#f44336' stroke-dasharray='6 4'/>"
        if set_
        else ""
    )
    transit_line = (
        f"<line x1='{x_pos(transit):.2f}' y1='{margin_top}' x2='{x_pos(transit):.2f}' y2='{margin_top + plot_height}' "
        f"stroke='#03a9f4' stroke-dasharray='4 4'/>"
        if transit
        else ""
    )

    polar_path = " ".join(
        f"{polar_center_x + _polar_radius(s.altitude_deg, polar_radius) * math.sin(math.radians(s.azimuth_deg)):.2f},"
        f"{polar_center_y - _polar_radius(s.altitude_deg, polar_radius) * math.cos(math.radians(s.azimuth_deg)):.2f}"
        for s in samples
    )

    svg = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<style>text{font-family:Helvetica,Arial,sans-serif;font-size:14px;}</style>",
        f"<rect x='0' y='0' width='{width}' height='{height}' fill='#0b1021'/>",
        *twilight,
        f"<polyline points='{path_points}' fill='none' stroke='#ffec3d' stroke-width='2' />",
        rise_line,
        set_line,
        transit_line,
        f"<rect x='{margin_left}' y='{margin_top}' width='{plot_width}' height='{plot_height}' fill='none' stroke='#ffffff40' stroke-width='1' />",
        f"<text x='{margin_left}' y='{margin_top - 15}' fill='#fff'>Altitude vs Time</text>",
        _time_labels(start, end, margin_left, plot_width, margin_top + plot_height + 25),
        _altitude_labels(min_alt, max_alt, margin_left - 10, margin_top, plot_height),
        _polar_axes(polar_center_x, polar_center_y, polar_radius),
        f"<polyline points='{polar_path}' fill='none' stroke='#ffec3d' stroke-width='2' />",
        _event_marker_svg(rise, "Rise", x_pos, margin_top, plot_height, '#4caf50'),
        _event_marker_svg(set_, "Set", x_pos, margin_top, plot_height, '#f44336'),
        _event_marker_svg(transit, "Transit", x_pos, margin_top, plot_height, '#03a9f4'),
        "</svg>",
    ]
    return "".join(svg)


def _render_png(
    samples: Sequence[AltAzSample],
    rise: datetime | None,
    set_: datetime | None,
    transit: datetime | None,
    start: datetime,
    end: datetime,
) -> bytes:
    image_module, image_draw_module, image_font_module = _pillow_modules()

    width = 900
    height = 580
    margin_left = 70
    margin_top = 50
    plot_width = width - margin_left - 40
    plot_height = 260

    img = image_module.new("RGBA", (width, height), "#0b1021")
    draw = image_draw_module.Draw(img)
    font = image_font_module.load_default()

    if not samples:
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    altitudes = [s.altitude_deg for s in samples]
    min_alt = min(min(altitudes), -10.0)
    max_alt = max(max(altitudes), 90.0)
    alt_range = max_alt - min_alt or 1.0

    def x_pos(moment: datetime) -> float:
        span = (end - start).total_seconds()
        if span == 0:
            return margin_left
        return margin_left + ((moment - start).total_seconds() / span) * plot_width

    def y_pos(alt: float) -> float:
        return margin_top + plot_height - ((alt - min_alt) / alt_range) * plot_height

    _draw_twilight(draw, samples, x_pos, margin_top, plot_height)

    path = []
    for s in samples:
        path.append((x_pos(s.moment), y_pos(s.altitude_deg)))
    draw.line(path, fill="#ffec3d", width=2)

    _draw_event_line(draw, x_pos, margin_top, plot_height, rise, "#4caf50")
    _draw_event_line(draw, x_pos, margin_top, plot_height, set_, "#f44336")
    _draw_event_line(draw, x_pos, margin_top, plot_height, transit, "#03a9f4")

    draw.rectangle(
        [margin_left, margin_top, margin_left + plot_width, margin_top + plot_height],
        outline="#ffffff40",
        width=1,
    )
    draw.text((margin_left, margin_top - 20), "Altitude vs Time", fill="#ffffff", font=font)
    _draw_time_labels(draw, start, end, margin_left, plot_width, margin_top + plot_height + 10, font)
    _draw_altitude_labels(draw, min_alt, max_alt, margin_left - 40, margin_top, plot_height, font)

    _draw_polar(
        draw,
        samples,
        margin_left + plot_width / 2,
        margin_top + plot_height + 220,
        160,
        image_font_module,
    )

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def _twilight_polygons(samples: Sequence[AltAzSample], x_pos, margin_top: float, plot_height: float) -> list[str]:
    bands = [(-90.0, -18.0, "#001d3d80"), (-18.0, -12.0, "#123f7380"), (-12.0, -6.0, "#24527b80")]
    segments: list[str] = []
    for low, high, color in bands:
        spans = _sun_band(samples, low, high)
        for start, end in spans:
            x0 = x_pos(start)
            x1 = x_pos(end)
            segments.append(
                f"<rect x='{x0:.2f}' y='{margin_top}' width='{max(x1 - x0, 1):.2f}' height='{plot_height}' fill='{color}'/>"
            )
    return segments


def _sun_band(samples: Sequence[AltAzSample], low: float, high: float) -> list[tuple[datetime, datetime]]:
    spans: list[tuple[datetime, datetime]] = []
    active_start: datetime | None = None
    for sample in samples:
        alt = sample.sun_altitude_deg
        if low <= alt < high:
            if active_start is None:
                active_start = sample.moment
        else:
            if active_start is not None:
                spans.append((active_start, sample.moment))
                active_start = None
    if active_start is not None:
        spans.append((active_start, samples[-1].moment))
    return spans


def _polar_radius(alt: float, radius: float) -> float:
    return max(0.0, min(1.0, alt / 90.0)) * radius


def _polar_axes(cx: float, cy: float, radius: float) -> str:
    rings = []
    for alt in (90, 60, 30, 0):
        r = _polar_radius(alt, radius)
        rings.append(
            f"<circle cx='{cx:.2f}' cy='{cy:.2f}' r='{r:.2f}' stroke='#ffffff30' stroke-width='1' fill='none'/>"
        )
        rings.append(
            f"<text x='{cx + r + 5:.2f}' y='{cy - 5:.2f}' fill='#ffffff80'>{alt}°</text>"
        )
    axes = []
    for az in range(0, 360, 45):
        theta = math.radians(az)
        x = cx + radius * math.sin(theta)
        y = cy - radius * math.cos(theta)
        axes.append(
            f"<line x1='{cx:.2f}' y1='{cy:.2f}' x2='{x:.2f}' y2='{y:.2f}' stroke='#ffffff20' stroke-width='1'/>"
        )
    labels = [
        f"<text x='{cx:.2f}' y='{cy - radius - 10:.2f}' fill='#fff'>N</text>",
        f"<text x='{cx + radius + 5:.2f}' y='{cy:.2f}' fill='#fff'>E</text>",
        f"<text x='{cx:.2f}' y='{cy + radius + 18:.2f}' fill='#fff'>S</text>",
        f"<text x='{cx - radius - 20:.2f}' y='{cy:.2f}' fill='#fff'>W</text>",
    ]
    return "".join(rings + axes + labels)


def _event_marker_svg(moment: datetime | None, label: str, x_pos, margin_top, plot_height, color: str) -> str:
    if moment is None:
        return ""
    x = x_pos(moment)
    y = margin_top - 10
    return (
        f"<text x='{x:.2f}' y='{y:.2f}' fill='{color}' text-anchor='middle'>{label}</text>"
    )


def _time_labels(start: datetime, end: datetime, x0: float, width: float, y: float) -> str:
    span = (end - start).total_seconds()
    ticks = 6
    labels = []
    for idx in range(ticks + 1):
        frac = idx / ticks
        moment = start + timedelta(seconds=span * frac)
        x = x0 + width * frac
        labels.append(
            f"<text x='{x:.2f}' y='{y:.2f}' fill='#ffffff80' text-anchor='middle'>{moment.strftime('%H:%M')}</text>"
        )
    return "".join(labels)


def _altitude_labels(min_alt: float, max_alt: float, x: float, y0: float, height: float) -> str:
    labels = []
    for alt in range(int(math.floor(min_alt / 10) * 10), int(math.ceil(max_alt / 10) * 10) + 1, 10):
        pos = y0 + height - ((alt - min_alt) / (max_alt - min_alt or 1.0)) * height
        labels.append(
            f"<text x='{x:.2f}' y='{pos:.2f}' fill='#ffffff80' text-anchor='end'>{alt}°</text>"
        )
    return "".join(labels)


def _draw_twilight(draw: ImageDraw.ImageDraw, samples: Sequence[AltAzSample], x_pos, margin_top: float, plot_height: float) -> None:
    bands = [(-90.0, -18.0, (0, 29, 61, 128)), (-18.0, -12.0, (18, 63, 115, 128)), (-12.0, -6.0, (36, 82, 123, 128))]
    for low, high, color in bands:
        spans = _sun_band(samples, low, high)
        for start, end in spans:
            draw.rectangle(
                [x_pos(start), margin_top, x_pos(end), margin_top + plot_height],
                fill=color,
            )


def _draw_event_line(draw: ImageDraw.ImageDraw, x_pos, margin_top: float, plot_height: float, moment: datetime | None, color: str) -> None:
    if moment is None:
        return
    x = x_pos(moment)
    draw.line([x, margin_top, x, margin_top + plot_height], fill=color, width=2, joint="curve")


def _draw_time_labels(draw: ImageDraw.ImageDraw, start: datetime, end: datetime, x0: float, width: float, y: float, font: ImageFont.ImageFont) -> None:
    span = (end - start).total_seconds()
    ticks = 6
    for idx in range(ticks + 1):
        frac = idx / ticks
        moment = start + timedelta(seconds=span * frac)
        x = x0 + width * frac
        draw.text((x - 15, y), moment.strftime("%H:%M"), fill="#ffffff80", font=font)


def _draw_altitude_labels(draw: ImageDraw.ImageDraw, min_alt: float, max_alt: float, x: float, y0: float, height: float, font: ImageFont.ImageFont) -> None:
    for alt in range(int(math.floor(min_alt / 10) * 10), int(math.ceil(max_alt / 10) * 10) + 1, 10):
        pos = y0 + height - ((alt - min_alt) / (max_alt - min_alt or 1.0)) * height
        draw.text((x, pos - 7), f"{alt}°", fill="#ffffff80", font=font)


def _draw_polar(
    draw: ImageDraw.ImageDraw,
    samples: Sequence[AltAzSample],
    cx: float,
    cy: float,
    radius: float,
    font_module,
) -> None:
    for alt in (90, 60, 30, 0):
        r = _polar_radius(alt, radius)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline="#ffffff30")
    for az in range(0, 360, 45):
        theta = math.radians(az)
        x = cx + radius * math.sin(theta)
        y = cy - radius * math.cos(theta)
        draw.line([cx, cy, x, y], fill="#ffffff20")
    label_font = font_module.load_default()
    draw.text((cx - 5, cy - radius - 20), "N", fill="#ffffff", font=label_font)
    draw.text((cx + radius + 5, cy - 5), "E", fill="#ffffff", font=label_font)
    draw.text((cx - 5, cy + radius + 5), "S", fill="#ffffff", font=label_font)
    draw.text((cx - radius - 20, cy - 5), "W", fill="#ffffff", font=label_font)
    path = []
    for s in samples:
        r = _polar_radius(s.altitude_deg, radius)
        theta = math.radians(s.azimuth_deg)
        x = cx + r * math.sin(theta)
        y = cy - r * math.cos(theta)
        path.append((x, y))
    if len(path) >= 2:
        draw.line(path, fill="#ffec3d", width=2)


__all__ = ["AltAzDiagram", "AltAzSample", "render_altaz_diagram"]
