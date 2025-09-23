"""Compute mundane ingress charts for cardinal points."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Mapping, Sequence

from ..chart.config import ChartConfig
from ..chart.natal import (
    ChartLocation,
    NatalChart,
    DEFAULT_BODIES,
    compute_natal_chart,
)
from ..detectors.ingress import find_ingresses
from ..events import IngressEvent
from ..ephemeris import SwissEphemerisAdapter
from ..scoring import DEFAULT_ASPECTS

__all__ = ["IngressChart", "compute_cardinal_ingress_charts"]

_CARDINAL_WINDOWS = {
    "aries": ((3, 10), (4, 1)),
    "cancer": ((6, 10), (7, 1)),
    "libra": ((9, 10), (10, 1)),
    "capricorn": ((12, 10), (12, 31)),
}


@dataclass(frozen=True)
class IngressChart:
    """Container pairing an ingress event with its mundane chart."""

    sign: str
    event: IngressEvent
    chart: NatalChart


def _window_for(year: int, sign: str) -> tuple[datetime, datetime]:
    try:
        (start_month, start_day), (end_month, end_day) = _CARDINAL_WINDOWS[sign]
    except KeyError as exc:
        raise ValueError(f"Unsupported ingress sign '{sign}'") from exc
    start = datetime(year, start_month, start_day, tzinfo=UTC)
    end_year = year if sign != "capricorn" else year
    end = datetime(end_year, end_month, end_day, tzinfo=UTC)
    return start, end


def compute_cardinal_ingress_charts(
    year: int,
    location: ChartLocation,
    *,
    chart_config: ChartConfig | None = None,
    bodies: Mapping[str, int] | None = None,
    aspect_angles: Sequence[int] | None = None,
    orb_profile: str = "standard",
    adapter: SwissEphemerisAdapter | None = None,
) -> dict[str, IngressChart]:
    """Return mundane charts for the Sun's cardinal ingresses in ``year``."""

    chart_config = chart_config or ChartConfig()
    adapter = adapter or SwissEphemerisAdapter(chart_config=chart_config)
    body_map = bodies or DEFAULT_BODIES
    angles = aspect_angles or DEFAULT_ASPECTS
    results: dict[str, IngressChart] = {}

    for sign_key in ("aries", "cancer", "libra", "capricorn"):
        start_dt, end_dt = _window_for(year, sign_key)
        start_jd = adapter.julian_day(start_dt)
        end_jd = adapter.julian_day(end_dt)
        ingresses = find_ingresses(start_jd, end_jd, ["Sun"])
        match: IngressEvent | None = None
        for event in ingresses:
            if event.sign.lower() == sign_key:
                match = event
                break
        if match is None:
            raise ValueError(f"No solar ingress for {sign_key} between {start_dt.isoformat()} and {end_dt.isoformat()}")
        moment = datetime.fromisoformat(match.ts.replace("Z", "+00:00")).astimezone(UTC)
        natal = compute_natal_chart(
            moment,
            location,
            bodies=body_map,
            aspect_angles=angles,
            orb_profile=orb_profile,
            config=chart_config,
            adapter=adapter,
        )
        results[sign_key] = IngressChart(sign=match.sign, event=match, chart=natal)
    return results
