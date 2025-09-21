"""High level transit scanning helpers used by the CLI and unit tests."""

from __future__ import annotations

import datetime as dt
from typing import Iterable, List

from .core.engine import get_active_aspect_angles
from .detectors import CoarseHit, detect_antiscia_contacts, detect_decl_contacts
from .detectors_aspects import AspectHit, detect_aspects
from .exporters import TransitEvent
from .providers import get_provider
from .scoring import ScoreInputs, compute_score

__all__ = ["events_to_dicts", "scan_contacts", "get_active_aspect_angles", "resolve_provider"]


def events_to_dicts(events: Iterable[TransitEvent]) -> List[dict]:
    """Convert :class:`TransitEvent` objects into JSON-friendly dictionaries."""

    return [event.to_dict() for event in events]


def _iso_ticks(start_iso: str, end_iso: str, *, step_minutes: int) -> Iterable[str]:
    """Yield ISO-8601 timestamps separated by ``step_minutes`` minutes."""

    start_dt = dt.datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    end_dt = dt.datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
    step = dt.timedelta(minutes=step_minutes)
    current = start_dt
    while current <= end_dt:
        yield current.replace(tzinfo=dt.timezone.utc).isoformat().replace("+00:00", "Z")
        current += step


def _score_from_hit(
    kind: str,
    orb_abs: float,
    orb_allow: float,
    moving: str,
    target: str,
    phase: str,
) -> float:
    """Use the scoring policy to assign a score for a detected contact."""

    score_inputs = ScoreInputs(
        kind=kind,
        orb_abs_deg=float(orb_abs),
        orb_allow_deg=float(orb_allow),
        moving=moving,
        target=target,
        applying_or_separating=phase,
    )
    return compute_score(score_inputs).score


def _event_from_decl(hit: CoarseHit, *, orb_allow: float) -> TransitEvent:
    score = _score_from_hit(
        hit.kind,
        abs(hit.delta),
        orb_allow,
        hit.moving,
        hit.target,
        hit.applying_or_separating,
    )
    return TransitEvent(
        kind=hit.kind,
        timestamp=hit.when_iso,
        moving=hit.moving,
        target=hit.target,
        orb_abs=abs(hit.delta),
        orb_allow=float(orb_allow),
        applying_or_separating=hit.applying_or_separating,
        score=score,
        lon_moving=hit.lon_moving,
        lon_target=hit.lon_target,
        metadata={
            "dec_moving": hit.dec_moving,
            "dec_target": hit.dec_target,
        },
    )


def _event_from_aspect(hit: AspectHit) -> TransitEvent:
    score = _score_from_hit(
        hit.kind,
        hit.orb_abs,
        hit.orb_allow,
        hit.moving,
        hit.target,
        hit.applying_or_separating,
    )
    return TransitEvent(
        kind=hit.kind,
        timestamp=hit.when_iso,
        moving=hit.moving,
        target=hit.target,
        orb_abs=float(hit.orb_abs),
        orb_allow=float(hit.orb_allow),
        applying_or_separating=hit.applying_or_separating,
        score=score,
        lon_moving=hit.lon_moving,
        lon_target=hit.lon_target,
        metadata={"angle_deg": hit.angle_deg},
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
    """Scan for declination, antiscia, and aspect contacts between two bodies."""

    provider = get_provider(provider_name)
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
        events.append(_event_from_decl(hit, orb_allow=allow))

    for hit in detect_antiscia_contacts(
        provider,
        ticks,
        moving,
        target,
        antiscia_orb,
        contra_antiscia_orb,
    ):
        allow = antiscia_orb if hit.kind == "antiscia" else contra_antiscia_orb
        events.append(_event_from_decl(hit, orb_allow=allow))

    for aspect_hit in detect_aspects(
        provider,
        ticks,
        moving,
        target,
        policy_path=aspects_policy_path,
    ):
        events.append(_event_from_aspect(aspect_hit))

    events.sort(key=lambda event: (event.timestamp, -event.score))
    return events


def resolve_provider(name: str | None) -> object:
    """Compatibility shim used by external callers."""

    return get_provider(name or "swiss")
