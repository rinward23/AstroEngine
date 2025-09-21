"""High level transit scanning helpers used by the CLI."""

from __future__ import annotations

import datetime as _dt
from typing import Iterable, List

from .core.engine import (
    apply_profile_if_any,
    get_active_aspect_angles,
    get_feature_flag,
    maybe_attach_domain_fields,
)
from .detectors import CoarseHit, detect_antiscia_contacts, detect_decl_contacts
from .detectors_aspects import AspectHit, detect_aspects
from .exporters import TransitEvent
from .providers import EphemerisProvider, get_provider
from .scoring import ScoreInputs, compute_score

__all__ = [
    "scan_contacts",
    "resolve_provider",
    "events_to_dicts",
    "apply_profile_if_any",
    "get_active_aspect_angles",
    "get_feature_flag",
    "maybe_attach_domain_fields",
]


def _iso_ticks(start_iso: str, end_iso: str, step_minutes: int = 60) -> Iterable[str]:
    start = _dt.datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    end = _dt.datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
    step = _dt.timedelta(minutes=int(step_minutes))
    while start <= end:
        yield start.astimezone(_dt.timezone.utc).isoformat().replace("+00:00", "Z")
        start += step


def _score_contact(kind: str, hit: CoarseHit, orb_allow: float) -> float:
    inputs = ScoreInputs(
        kind=kind,
        orb_abs_deg=abs(float(hit.delta)),
        orb_allow_deg=float(orb_allow),
        moving=hit.moving,
        target=hit.target,
        applying_or_separating=hit.applying_or_separating,
    )
    return compute_score(inputs).score


def _event_from_coarse(hit: CoarseHit, orb_allow: float) -> TransitEvent:
    score = _score_contact(hit.kind, hit, orb_allow)
    return TransitEvent(
        kind=hit.kind,
        timestamp=hit.when_iso,
        moving=hit.moving,
        target=hit.target,
        orb_abs=abs(float(hit.delta)),
        orb_allow=float(orb_allow),
        applying_or_separating=hit.applying_or_separating,
        score=float(score),
        lon_moving=float(hit.lon_moving),
        lon_target=float(hit.lon_target),
        metadata={"dec_moving": float(hit.dec_moving), "dec_target": float(hit.dec_target)},
    )


def _event_from_aspect(hit: AspectHit) -> TransitEvent:
    inputs = ScoreInputs(
        kind=hit.kind,
        orb_abs_deg=float(hit.orb_abs),
        orb_allow_deg=float(hit.orb_allow),
        moving=hit.moving,
        target=hit.target,
        applying_or_separating=hit.applying_or_separating,
    )
    score = compute_score(inputs).score
    return TransitEvent(
        kind=hit.kind,
        timestamp=hit.when_iso,
        moving=hit.moving,
        target=hit.target,
        orb_abs=float(hit.orb_abs),
        orb_allow=float(hit.orb_allow),
        applying_or_separating=hit.applying_or_separating,
        score=float(score),
        lon_moving=float(hit.lon_moving),
        lon_target=float(hit.lon_target),
        metadata={"angle_deg": float(hit.angle_deg)},
    )


def scan_contacts(
    start_iso: str,
    end_iso: str,
    moving: str,
    target: str,
    provider_name: str = "swiss",
    *,
    decl_parallel_orb: float = 0.5,
    decl_contra_orb: float = 0.5,
    antiscia_orb: float = 2.0,
    contra_antiscia_orb: float = 2.0,
    step_minutes: int = 60,
    aspects_policy_path: str | None = None,
) -> List[TransitEvent]:
    try:
        provider: EphemerisProvider = get_provider(provider_name)
    except KeyError:
        return []

    ticks = list(_iso_ticks(start_iso, end_iso, step_minutes=step_minutes))
    events: List[TransitEvent] = []

    for hit in detect_decl_contacts(
        provider,
        ticks,
        moving,
        target,
        decl_parallel_orb,
        decl_contra_orb,
    ):
        allow = decl_parallel_orb if hit.kind == "decl_parallel" else decl_contra_orb
        events.append(_event_from_coarse(hit, allow))

    for hit in detect_antiscia_contacts(
        provider,
        ticks,
        moving,
        target,
        antiscia_orb,
        contra_antiscia_orb,
    ):
        allow = antiscia_orb if hit.kind == "antiscia" else contra_antiscia_orb
        events.append(_event_from_coarse(hit, allow))

    for hit in detect_aspects(
        provider,
        ticks,
        moving,
        target,
        policy_path=aspects_policy_path,
    ):
        events.append(_event_from_aspect(hit))

    events.sort(key=lambda e: (e.timestamp, e.kind))
    return events


def resolve_provider(name: str | None) -> EphemerisProvider:
    return get_provider(name or "swiss")


def events_to_dicts(events: Iterable[TransitEvent]) -> List[dict]:
    return [e.to_dict() for e in events]
