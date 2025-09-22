"""Utilities for computing solar ingress charts and mundane aspecting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from ..chart.natal import (
    ChartLocation,
    DEFAULT_BODIES,
    NatalChart,
)
from ..detectors.common import iso_to_jd
from ..detectors.ingresses import ZODIAC_SIGNS, find_sign_ingresses
from ..ephemeris import BodyPosition, HousePositions, SwissEphemerisAdapter
from ..events import IngressEvent
from ..scoring import DEFAULT_ASPECTS, OrbCalculator

__all__ = [
    "MundaneAspect",
    "SolarIngressChart",
    "compute_solar_ingress_chart",
    "compute_solar_quartet",
]


@dataclass(frozen=True)
class MundaneAspect:
    """Aspect hit produced within ingress charts or against natal positions."""

    source: str
    body_a: str
    body_b: str
    angle: int
    orb: float
    separation: float


@dataclass(frozen=True)
class SolarIngressChart:
    """Computed chart snapshot for a solar ingress."""

    sign: str
    year: int
    event: IngressEvent
    location: ChartLocation | None
    positions: Mapping[str, BodyPosition]
    houses: HousePositions | None
    aspects: Sequence[MundaneAspect]
    natal_aspects: Sequence[MundaneAspect]


def _resolve_sign(sign: str) -> str:
    canon = sign.strip().lower()
    for name in ZODIAC_SIGNS:
        if name.lower() == canon:
            return name
    raise ValueError(f"Unknown zodiac sign: {sign}")


def _circular_delta(a: float, b: float) -> float:
    diff = (b - a) % 360.0
    return diff if diff <= 180.0 else 360.0 - diff


def _compute_chart_aspects(
    positions: Mapping[str, BodyPosition],
    angles: Sequence[int],
    calculator: OrbCalculator,
    profile: str,
) -> list[MundaneAspect]:
    hits: list[MundaneAspect] = []
    names = list(positions.keys())
    for idx, name_a in enumerate(names):
        pos_a = positions[name_a].longitude
        for name_b in names[idx + 1 :]:
            pos_b = positions[name_b].longitude
            separation = _circular_delta(pos_a, pos_b)
            for angle in angles:
                orb = abs(separation - angle)
                threshold = calculator.orb_for(name_a, name_b, angle, profile=profile)
                if orb <= threshold:
                    hits.append(
                        MundaneAspect(
                            source="ingress",
                            body_a=name_a,
                            body_b=name_b,
                            angle=int(angle),
                            orb=orb,
                            separation=separation,
                        )
                    )
                    break
    return hits


def _compute_cross_aspects(
    positions_a: Mapping[str, BodyPosition],
    positions_b: Mapping[str, BodyPosition],
    angles: Sequence[int],
    calculator: OrbCalculator,
    profile: str,
) -> list[MundaneAspect]:
    hits: list[MundaneAspect] = []
    for name_a, pos_a in positions_a.items():
        for name_b, pos_b in positions_b.items():
            separation = _circular_delta(pos_a.longitude, pos_b.longitude)
            for angle in angles:
                orb = abs(separation - angle)
                threshold = calculator.orb_for(name_a, name_b, angle, profile=profile)
                if orb <= threshold:
                    hits.append(
                        MundaneAspect(
                            source="ingress-natal",
                            body_a=name_a,
                            body_b=name_b,
                            angle=int(angle),
                            orb=orb,
                            separation=separation,
                        )
                    )
                    break
    return hits


def _find_solar_event(year: int, sign: str) -> IngressEvent:
    start_jd = iso_to_jd(f"{year}-01-01T00:00:00Z")
    end_jd = iso_to_jd(f"{year + 1}-01-01T00:00:00Z")
    events = find_sign_ingresses(start_jd, end_jd, bodies=("sun",), step_hours=6.0)
    target = sign.lower()
    for event in events:
        if event.to_sign.lower() == target:
            return event
    raise ValueError(f"No solar ingress into {sign} found for {year}")


def compute_solar_ingress_chart(
    year: int,
    sign: str,
    *,
    location: ChartLocation | None = None,
    bodies: Mapping[str, int] | None = None,
    aspect_angles: Sequence[int] | None = None,
    orb_profile: str = "standard",
    adapter: SwissEphemerisAdapter | None = None,
    orb_calculator: OrbCalculator | None = None,
    natal_chart: NatalChart | None = None,
) -> SolarIngressChart:
    """Compute a solar ingress chart for ``year`` and zodiac ``sign``."""

    resolved_sign = _resolve_sign(sign)
    event = _find_solar_event(year, resolved_sign)
    adapter = adapter or SwissEphemerisAdapter()
    orb_calculator = orb_calculator or OrbCalculator()
    bodies = bodies or DEFAULT_BODIES
    angles = aspect_angles or DEFAULT_ASPECTS

    positions = adapter.body_positions(event.jd, bodies)
    houses: HousePositions | None = None
    if location is not None:
        houses = adapter.houses(event.jd, location.latitude, location.longitude)

    chart_aspects = _compute_chart_aspects(positions, list(angles), orb_calculator, orb_profile)

    natal_aspects: list[MundaneAspect] = []
    if natal_chart is not None:
        natal_aspects = _compute_cross_aspects(
            positions,
            natal_chart.positions,
            list(angles),
            orb_calculator,
            orb_profile,
        )

    return SolarIngressChart(
        sign=resolved_sign,
        year=year,
        event=event,
        location=location,
        positions=positions,
        houses=houses,
        aspects=tuple(chart_aspects),
        natal_aspects=tuple(natal_aspects),
    )


def compute_solar_quartet(
    year: int,
    *,
    location: ChartLocation | None = None,
    bodies: Mapping[str, int] | None = None,
    aspect_angles: Sequence[int] | None = None,
    orb_profile: str = "standard",
    adapter: SwissEphemerisAdapter | None = None,
    orb_calculator: OrbCalculator | None = None,
    natal_chart: NatalChart | None = None,
) -> list[SolarIngressChart]:
    """Return the solstice/equinox quartet for ``year``."""

    adapter = adapter or SwissEphemerisAdapter()
    orb_calculator = orb_calculator or OrbCalculator()
    charts: list[SolarIngressChart] = []
    for sign in ("Aries", "Cancer", "Libra", "Capricorn"):
        charts.append(
            compute_solar_ingress_chart(
                year,
                sign,
                location=location,
                bodies=bodies,
                aspect_angles=aspect_angles,
                orb_profile=orb_profile,
                adapter=adapter,
                orb_calculator=orb_calculator,
                natal_chart=natal_chart,
            )
        )
    return charts
