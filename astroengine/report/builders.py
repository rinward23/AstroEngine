"""Helper utilities for building chart report payloads."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Protocol, Sequence

from ..canonical import canonical_round, normalize_longitude
from .pdf import AspectEntry, ChartReportContext, WheelEntry

__all__ = [
    "ChartLike",
    "build_chart_report_context",
    "build_wheel_entries",
    "build_aspect_entries",
    "build_narrative",
    "build_subtitle",
]


class ChartLike(Protocol):
    """Protocol describing the attributes required from a chart model."""

    id: int
    dt_utc: datetime | None
    lat: float | None
    lon: float | None
    location_name: str | None
    kind: str | None
    profile_key: str | None


_SIGN_NAMES = (
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

_ASPECT_NAMES = {0: "Conjunction", 60: "Sextile", 90: "Square", 120: "Trine", 180: "Opposition"}


def _normalise_longitude(value: float) -> float:
    return normalize_longitude(value)


def _sign_name(longitude: float) -> str:
    index = int(_normalise_longitude(longitude) // 30)
    return _SIGN_NAMES[index]


def _sign_degree(longitude: float) -> float:
    return canonical_round(_normalise_longitude(longitude) % 30.0)


def _house_for(longitude: float, cusps: Sequence[float]) -> int | None:
    if not cusps:
        return None
    normalized = [_normalise_longitude(value) for value in cusps]
    lon = _normalise_longitude(longitude)
    for idx, start in enumerate(normalized):
        end = normalized[(idx + 1) % 12]
        if start <= end:
            if start <= lon < end:
                return idx + 1
        else:
            if lon >= start or lon < end:
                return idx + 1
    return None


def build_wheel_entries(natal) -> list[WheelEntry]:
    """Convert natal positions into wheel entries sorted by longitude."""

    cusps = list(getattr(natal.houses, "cusps", []) or [])
    entries: list[WheelEntry] = []
    for body, position in natal.positions.items():
        longitude = canonical_round(_normalise_longitude(position.longitude))
        entries.append(
            WheelEntry(
                body=body,
                sign=_sign_name(longitude),
                degree=_sign_degree(longitude),
                longitude=longitude,
                house=_house_for(longitude, cusps),
            )
        )
    entries.sort(key=lambda item: item.longitude)
    return entries


def build_aspect_entries(natal) -> list[AspectEntry]:
    """Produce aspect entries ordered by increasing orb."""

    entries: list[AspectEntry] = []
    for hit in sorted(natal.aspects, key=lambda item: item.orb):
        aspect_name = _ASPECT_NAMES.get(int(hit.angle), f"{int(hit.angle)}°")
        entries.append(
            AspectEntry(
                body_a=hit.body_a,
                body_b=hit.body_b,
                aspect=aspect_name,
                orb=float(hit.orb),
                separation=float(hit.separation),
            )
        )
    return entries


def build_narrative(
    timestamp: datetime | None,
    location_name: str | None,
    natal,
) -> str:
    """Generate a short narrative summary describing the natal chart."""

    components: list[str] = []
    ts_text = timestamp.isoformat() if timestamp else "unspecified time"
    location = location_name or "unspecified location"
    components.append(f"Chart generated for {ts_text} at {location}.")
    for key in ("Sun", "Moon"):
        body = natal.positions.get(key)
        if body is not None:
            components.append(
                f"{key} in {_sign_name(body.longitude)} at {_sign_degree(body.longitude):.2f}°"
            )
    asc = getattr(natal.houses, "ascendant", None)
    if asc is not None:
        components.append(
            f"Ascendant {_sign_name(asc)} {_sign_degree(asc):.2f}°"
        )
    return " ".join(components)


def build_subtitle(chart_id: int, chart_kind: str | None, profile_key: str | None) -> str:
    """Generate the subtitle displayed beneath the report title."""

    subtitle_parts: list[str] = [f"Chart #{chart_id}"]
    if chart_kind:
        subtitle_parts.append(str(chart_kind))
    if profile_key:
        subtitle_parts.append(profile_key)
    return " · ".join(subtitle_parts)


def build_chart_report_context(
    chart_id: int,
    natal,
    *,
    chart_kind: str | None,
    profile_key: str | None,
    chart_timestamp: datetime | None,
    location_name: str | None,
    disclaimers: Iterable[str] | None = None,
    generated_at: datetime | None = None,
    title: str = "AstroEngine Chart Report",
    aspect_limit: int | None = 24,
) -> ChartReportContext:
    """Assemble a :class:`ChartReportContext` from natal data."""

    generated = generated_at or datetime.now(timezone.utc)
    wheel_entries = build_wheel_entries(natal)
    aspect_entries = build_aspect_entries(natal)
    if aspect_limit is not None:
        aspect_entries = aspect_entries[:aspect_limit]
    narrative = build_narrative(chart_timestamp, location_name, natal)
    subtitle = build_subtitle(chart_id, chart_kind, profile_key)
    disclaimer_lines = [line for line in (disclaimers or []) if line.strip()]
    return ChartReportContext(
        title=title,
        subtitle=subtitle,
        generated_at=generated,
        wheel=wheel_entries,
        aspects=aspect_entries,
        narrative=narrative,
        disclaimers=disclaimer_lines,
    )

