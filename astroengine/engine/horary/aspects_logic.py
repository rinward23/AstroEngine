"""Applying/separating aspect logic and derived horary patterns."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from ...chart.natal import NatalChart
from ...utils.angles import delta_angle, norm360, classify_applying_separating
from .models import AspectContact, CollectionOfLight, Prohibition, TranslationOfLight
from .profiles import HoraryProfile

__all__ = [
    "ASPECT_ANGLES",
    "aspect_between",
    "find_translation",
    "find_collection",
    "find_prohibition",
]

ASPECT_ANGLES: dict[int, str] = {
    0: "conjunction",
    60: "sextile",
    90: "square",
    120: "trine",
    180: "opposition",
}


def _orb_allowance(aspect: str, body_a: str, body_b: str, profile: HoraryProfile) -> float:
    policy = profile.orb_policy()
    base = policy.by_aspect.get(aspect, 6.0)
    mult_a = policy.by_body_mult.get(body_a, 1.0)
    mult_b = policy.by_body_mult.get(body_b, 1.0)
    return base * max(mult_a, mult_b)


def _relative_speed(chart: NatalChart, moving: str, target: str) -> float:
    pos = chart.positions
    return pos[moving].speed_longitude - pos[target].speed_longitude


def _perfection_time(
    chart: NatalChart,
    moving: str,
    target_lon: float,
    *,
    relative_speed: float,
    applying: bool,
) -> datetime | None:
    if not applying or relative_speed == 0.0:
        return None
    delta = delta_angle(norm360(chart.positions[moving].longitude), norm360(target_lon))
    days = delta / relative_speed
    if days <= 0:
        return None
    return chart.moment + timedelta(days=days)


def aspect_between(
    chart: NatalChart,
    body_a: str,
    body_b: str,
    profile: HoraryProfile,
) -> AspectContact | None:
    """Return the dominant aspect contact between ``body_a`` and ``body_b``."""

    positions = chart.positions
    if body_a not in positions or body_b not in positions:
        return None

    pos_a = positions[body_a]
    pos_b = positions[body_b]
    best: AspectContact | None = None

    for angle, label in ASPECT_ANGLES.items():
        phase = (pos_b.longitude - pos_a.longitude + 360.0) % 360.0
        offset = (phase - angle + 180.0) % 360.0 - 180.0
        orb = abs(offset)
        allowance = _orb_allowance(label, body_a, body_b, profile)
        if orb > allowance:
            continue

        speed_a = abs(pos_a.speed_longitude)
        speed_b = abs(pos_b.speed_longitude)
        if speed_a >= speed_b:
            moving = body_a
            target_lon = (pos_b.longitude - angle) % 360.0
        else:
            moving = body_b
            target_lon = (pos_a.longitude - angle) % 360.0

        moving_pos = positions[moving]
        state = classify_applying_separating(
            norm360(moving_pos.longitude),
            moving_pos.speed_longitude,
            norm360(target_lon),
        )
        applying_flag = state == "applying"
        relative = _relative_speed(chart, moving, body_b if moving == body_a else body_a)
        perfection = _perfection_time(
            chart,
            moving,
            target_lon,
            relative_speed=relative,
            applying=applying_flag,
        )

        contact = AspectContact(
            body_a=body_a,
            body_b=body_b,
            aspect=label,
            orb=orb,
            exact_delta=offset,
            applying=applying_flag,
            moving_body=moving,
            target_longitude=target_lon,
            perfection_time=perfection,
        )
        if best is None or orb < best.orb:
            best = contact

    return best


def _bodies_sorted_by_speed(chart: NatalChart, bodies: Iterable[str], reverse: bool) -> list[str]:
    return sorted(
        bodies,
        key=lambda name: abs(chart.positions.get(name).speed_longitude) if name in chart.positions else 0.0,
        reverse=reverse,
    )


def _perfection_in_window(contact: AspectContact | None, limit: datetime) -> bool:
    if contact is None or not contact.applying:
        return False
    if contact.perfection_time is None:
        return True
    return contact.perfection_time <= limit


def find_translation(
    chart: NatalChart,
    body_a: str,
    body_b: str,
    profile: HoraryProfile,
    *,
    window_days: float = 30.0,
) -> TranslationOfLight | None:
    """Return translation of light between ``body_a`` and ``body_b`` when present."""

    candidates = [
        name
        for name in chart.positions
        if name not in {body_a, body_b}
    ]
    faster = _bodies_sorted_by_speed(chart, candidates, reverse=True)
    limit = chart.moment + timedelta(days=window_days)

    for translator in faster:
        if abs(chart.positions[translator].speed_longitude) <= max(
            abs(chart.positions[body_a].speed_longitude),
            abs(chart.positions[body_b].speed_longitude),
        ):
            continue
        contact_a = aspect_between(chart, translator, body_a, profile)
        contact_b = aspect_between(chart, translator, body_b, profile)
        if contact_a and contact_b and not contact_a.applying and _perfection_in_window(contact_b, limit):
            return TranslationOfLight(
                translator=translator,
                from_body=body_a,
                to_body=body_b,
                sequence=(contact_a, contact_b),
            )
    return None


def find_collection(
    chart: NatalChart,
    body_a: str,
    body_b: str,
    profile: HoraryProfile,
    *,
    window_days: float = 30.0,
) -> CollectionOfLight | None:
    """Return collection of light when a slower body gathers both lights."""

    candidates = [
        name
        for name in chart.positions
        if name not in {body_a, body_b}
    ]
    slower = _bodies_sorted_by_speed(chart, candidates, reverse=False)
    limit = chart.moment + timedelta(days=window_days)

    for collector in slower:
        if abs(chart.positions[collector].speed_longitude) >= min(
            abs(chart.positions[body_a].speed_longitude),
            abs(chart.positions[body_b].speed_longitude),
        ):
            continue
        contact_a = aspect_between(chart, collector, body_a, profile)
        contact_b = aspect_between(chart, collector, body_b, profile)
        if (
            contact_a
            and contact_b
            and _perfection_in_window(contact_a, limit)
            and _perfection_in_window(contact_b, limit)
        ):
            return CollectionOfLight(
                collector=collector,
                bodies=(body_a, body_b),
                sequence=(contact_a, contact_b),
            )
    return None


def find_prohibition(
    chart: NatalChart,
    body_a: str,
    body_b: str,
    profile: HoraryProfile,
    *,
    window_days: float = 30.0,
) -> Prohibition | None:
    """Return prohibition when another body perfects before the significators do."""

    primary = aspect_between(chart, body_a, body_b, profile)
    if primary is None or not primary.applying or primary.perfection_time is None:
        return None

    limit = min(primary.perfection_time, chart.moment + timedelta(days=window_days))

    for name in chart.positions:
        if name in {body_a, body_b}:
            continue
        for primary_body in (body_a, body_b):
            contact = aspect_between(chart, primary_body, name, profile)
            if (
                contact
                and contact.applying
                and contact.perfection_time is not None
                and contact.perfection_time < limit
            ):
                return Prohibition(
                    preventing_body=name,
                    affected_pair=(body_a, body_b),
                    contact=contact,
                )
    return None

