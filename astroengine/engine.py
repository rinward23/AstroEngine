# >>> AUTO-GEN BEGIN: AE Engine Hooks v1.0
from __future__ import annotations
import datetime as dt
from typing import Iterable, List

from .providers import get_provider
from .detectors import detect_decl_contacts, detect_antiscia_contacts, CoarseHit
from .exporters import TransitEvent
from .scoring import compute_score, ScoreInputs


def _iso_ticks(start_iso: str, end_iso: str, step_minutes: int = 60) -> Iterable[str]:
    t0 = dt.datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    t1 = dt.datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
    step = dt.timedelta(minutes=step_minutes)
    while t0 <= t1:
        yield t0.replace(tzinfo=dt.timezone.utc).isoformat().replace("+00:00", "Z")
        t0 += step


def _score_from_hit(hit: CoarseHit, orb_allow: float, kind_key: str) -> float:
    res = compute_score(ScoreInputs(
        kind=kind_key,
        orb_abs_deg=abs(hit.delta),
        orb_allow_deg=orb_allow,
        moving=hit.moving,
        target=hit.target,
        applying_or_separating=hit.applying_or_separating,
    ))
    return res.score


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
) -> List[TransitEvent]:
    prov = get_provider(provider_name)
    ticks = list(_iso_ticks(start_iso, end_iso, step_minutes=step_minutes))
    events: List[TransitEvent] = []

    for hit in detect_decl_contacts(prov, ticks, moving, target, decl_parallel_orb, decl_contra_orb):
        allow = decl_parallel_orb if hit.kind == "decl_parallel" else decl_contra_orb
        score = _score_from_hit(hit, allow, hit.kind)
        events.append(TransitEvent(
            kind=hit.kind,
            when_iso=hit.when_iso,
            moving=hit.moving,
            target=hit.target,
            orb_abs=abs(hit.delta),
            applying_or_separating=hit.applying_or_separating,
            score=score,
        ))

    for hit in detect_antiscia_contacts(prov, ticks, moving, target, antiscia_orb, contra_antiscia_orb):
        allow = antiscia_orb if hit.kind == "antiscia" else contra_antiscia_orb
        score = _score_from_hit(hit, allow, hit.kind)
        events.append(TransitEvent(
            kind=hit.kind,
            when_iso=hit.when_iso,
            moving=hit.moving,
            target=hit.target,
            orb_abs=abs(hit.delta),
            applying_or_separating=hit.applying_or_separating,
            score=score,
        ))

    events.sort(key=lambda e: (e.when_iso, -e.score))
    return events
# >>> AUTO-GEN END: AE Engine Hooks v1.0

from .core.engine import (
    apply_profile_if_any,
    get_active_aspect_angles,
    get_feature_flag,
    maybe_attach_domain_fields,
)

__all__ = [
    "apply_profile_if_any",
    "get_active_aspect_angles",
    "get_feature_flag",
    "maybe_attach_domain_fields",
    "resolve_provider",
    "scan_contacts",
]


def resolve_provider(name: str | None) -> object:
    return get_provider(name or "swiss")
