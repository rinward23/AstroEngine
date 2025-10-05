"""Horary toolkit orchestrating chart casting and judgement."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any, Mapping

from ...chart.config import ChartConfig
from ...chart.natal import ChartLocation, compute_natal_chart, DEFAULT_BODIES
from ...ephemeris.swisseph_adapter import get_swisseph
from .aspects_logic import aspect_between, find_collection, find_prohibition, find_translation
from .hour_ruler import GeoLocation, planetary_hour
from .judgement import score_testimonies
from .models import (
    AspectContact,
    CollectionOfLight,
    JudgementResult,
    PlanetaryHourResult,
    Prohibition,
    RadicalityCheck,
    Significator,
    SignificatorSet,
    TranslationOfLight,
)
from .profiles import HoraryProfile, get_profile
from .radicality import run_checks
from .significators import choose_significators

__all__ = ["evaluate_case", "GeoLocation", "get_profile"]


def _horary_bodies() -> Mapping[str, int]:
    bodies = dict(DEFAULT_BODIES)
    try:
        swe = get_swisseph()
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime dependency guard
        raise RuntimeError(
            "Horary profiles require pyswisseph. Install astroengine[ephem] to enable them."
        ) from exc
    bodies.setdefault("True Node", int(getattr(swe, "TRUE_NODE")))
    bodies.setdefault("Mean Node", int(getattr(swe, "MEAN_NODE")))
    return bodies


def _chart_location(loc: GeoLocation) -> ChartLocation:
    return ChartLocation(latitude=loc.latitude, longitude=loc.longitude)


def _serialize_planetary_hour(result: PlanetaryHourResult) -> dict[str, Any]:
    return {
        "ruler": result.ruler,
        "index": result.index,
        "start": result.start.isoformat(),
        "end": result.end.isoformat(),
        "sunrise": result.sunrise.isoformat(),
        "sunset": result.sunset.isoformat(),
        "next_sunrise": result.next_sunrise.isoformat(),
        "day_ruler": result.day_ruler,
        "sequence": list(result.sequence),
    }


def _serialize_significator(sig: Significator) -> dict[str, Any]:
    return {
        "body": sig.body,
        "role": sig.role,
        "longitude": sig.longitude,
        "latitude": sig.latitude,
        "speed": sig.speed,
        "house": sig.house,
        "dignities": asdict(sig.dignities),
        "receptions": {k: list(v) for k, v in sig.receptions.items()},
    }


def _serialize_contact(contact: AspectContact | None) -> dict[str, Any] | None:
    if contact is None:
        return None
    return {
        "body_a": contact.body_a,
        "body_b": contact.body_b,
        "aspect": contact.aspect,
        "orb": contact.orb,
        "exact_delta": contact.exact_delta,
        "applying": contact.applying,
        "moving_body": contact.moving_body,
        "target_longitude": contact.target_longitude,
        "perfection_time": contact.perfection_time.isoformat() if contact.perfection_time else None,
    }


def _serialize_sequence(obj: TranslationOfLight | CollectionOfLight | None) -> dict[str, Any] | None:
    if obj is None:
        return None
    payload: dict[str, Any] = {}
    if isinstance(obj, TranslationOfLight):
        payload.update(
            {
                "type": "translation",
                "translator": obj.translator,
                "from": obj.from_body,
                "to": obj.to_body,
            }
        )
    else:
        payload.update(
            {
                "type": "collection",
                "collector": obj.collector,
                "bodies": list(obj.bodies),
            }
        )
    payload["sequence"] = [
        _serialize_contact(contact) for contact in obj.sequence
    ]
    return payload


def _serialize_prohibition(prohibition: Prohibition | None) -> dict[str, Any] | None:
    if prohibition is None:
        return None
    return {
        "preventing_body": prohibition.preventing_body,
        "affected_pair": list(prohibition.affected_pair),
        "contact": _serialize_contact(prohibition.contact),
    }


def _serialize_checks(checks: list[RadicalityCheck]) -> list[dict[str, Any]]:
    return [
        {
            "code": check.code,
            "flag": check.flag,
            "reason": check.reason,
            "data": dict(check.data),
            "caution_weight": check.caution_weight,
        }
        for check in checks
    ]


def _serialize_judgement(result: JudgementResult) -> dict[str, Any]:
    return {
        "score": result.score,
        "classification": result.classification,
        "contributions": [
            {
                "code": entry.code,
                "label": entry.label,
                "weight": entry.weight,
                "value": entry.value,
                "score": entry.score,
                "rationale": entry.rationale,
            }
            for entry in result.contributions
        ],
    }


def evaluate_case(
    question: str,
    asked_at: datetime,
    location: GeoLocation,
    *,
    house_system: str = "placidus",
    quesited_house: int,
    profile: HoraryProfile | str = "Lilly",
) -> dict[str, Any]:
    """Compute the full horary assessment for a question."""

    profile_obj = get_profile(profile) if isinstance(profile, str) else profile
    if asked_at.tzinfo is None:
        asked_at = asked_at.replace(tzinfo=UTC)
    else:
        asked_at = asked_at.astimezone(UTC)

    config = ChartConfig(house_system=house_system)
    chart = compute_natal_chart(
        moment=asked_at,
        location=_chart_location(location),
        bodies=_horary_bodies(),
        config=config,
    )

    hour = planetary_hour(asked_at, location)
    is_day_chart = hour.sunrise <= asked_at <= hour.sunset

    significators = choose_significators(
        chart,
        quesited_house=quesited_house,
        profile=profile_obj,
        is_day_chart=is_day_chart,
    )

    checks = run_checks(chart, profile_obj, significators, hour)

    main_contact = aspect_between(
        chart, significators.querent.body, significators.quesited.body, profile_obj
    )
    translation = find_translation(
        chart, significators.querent.body, significators.quesited.body, profile_obj
    )
    collection = find_collection(
        chart, significators.querent.body, significators.quesited.body, profile_obj
    )
    prohibition = find_prohibition(
        chart, significators.querent.body, significators.quesited.body, profile_obj
    )

    judgement = score_testimonies(chart, significators, checks, profile_obj)

    positions_payload = {
        name: {
            "longitude": pos.longitude % 360.0,
            "latitude": pos.latitude,
            "speed_longitude": pos.speed_longitude,
        }
        for name, pos in chart.positions.items()
    }

    houses_payload = {
        "system": chart.houses.system,
        "ascendant": chart.houses.ascendant,
        "midheaven": chart.houses.midheaven,
        "cusps": list(chart.houses.cusps[:12]),
    }

    return {
        "question": question,
        "asked_at": asked_at.isoformat(),
        "profile": profile_obj.name,
        "location": {
            "latitude": location.latitude,
            "longitude": location.longitude,
        },
        "house_system": house_system,
        "planetary_hour": _serialize_planetary_hour(hour),
        "chart": {
            "positions": positions_payload,
            "houses": houses_payload,
        },
        "significators": {
            "querent": _serialize_significator(significators.querent),
            "quesited": _serialize_significator(significators.quesited),
            "moon": _serialize_significator(significators.moon),
            "co_significators": [
                _serialize_significator(sig) for sig in significators.co_significators
            ],
            "is_day_chart": significators.is_day_chart,
        },
        "aspect": _serialize_contact(main_contact),
        "translation": _serialize_sequence(translation),
        "collection": _serialize_sequence(collection),
        "prohibition": _serialize_prohibition(prohibition),
        "radicality": _serialize_checks(checks),
        "judgement": _serialize_judgement(judgement),
    }

