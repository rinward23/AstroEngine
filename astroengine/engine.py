# >>> AUTO-GEN BEGIN: AE Engine Hooks v1.2
from __future__ import annotations
import datetime as dt
from typing import Iterable, List

from .providers import get_provider
from .detectors import detect_decl_contacts, detect_antiscia_contacts, CoarseHit
from .detectors_aspects import detect_aspects, AspectHit
from .exporters import TransitEvent
from .scoring import compute_score, ScoreInputs
from .valence import combine_valence


def _iso_ticks(start_iso: str, end_iso: str, step_minutes: int = 60) -> Iterable[str]:
    t0 = dt.datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    t1 = dt.datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
    step = dt.timedelta(minutes=step_minutes)
    while t0 <= t1:
        yield t0.replace(tzinfo=dt.timezone.utc).isoformat().replace("+00:00", "Z")
        t0 += step


def _score_from(hit_kind: str, orb_abs: float, orb_allow: float, moving: str, target: str, phase: str) -> float:
    return compute_score(ScoreInputs(
        kind=hit_kind, orb_abs_deg=orb_abs, orb_allow_deg=orb_allow,
        moving=moving, target=target, applying_or_separating=phase,
    )).score


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
    valence_policy_path: str | None = None,
) -> List[TransitEvent]:
    prov = get_provider(provider_name)
    ticks = list(_iso_ticks(start_iso, end_iso, step_minutes=step_minutes))
    events: List[TransitEvent] = []

    # Declination & mirrors
    for hit in detect_decl_contacts(prov, ticks, moving, target, decl_parallel_orb, decl_contra_orb):
        allow = decl_parallel_orb if hit.kind == "decl_parallel" else decl_contra_orb
        base = _score_from(hit.kind, abs(hit.delta), allow, hit.moving, hit.target, hit.applying_or_separating)
        val, factor = combine_valence(moving=hit.moving, target=hit.target, contact_kind=hit.kind, aspect_name=None, policy_path=valence_policy_path)
        signed = base * factor * (1 if val == "positive" else (-1 if val == "negative" else 1))
        events.append(TransitEvent(hit.kind, hit.when_iso, hit.moving, hit.target, abs(hit.delta), hit.applying_or_separating, base, val, factor, signed))

    for hit in detect_antiscia_contacts(prov, ticks, moving, target, antiscia_orb, contra_antiscia_orb):
        allow = antiscia_orb if hit.kind == "antiscia" else contra_antiscia_orb
        base = _score_from(hit.kind, abs(hit.delta), allow, hit.moving, hit.target, hit.applying_or_separating)
        val, factor = combine_valence(moving=hit.moving, target=hit.target, contact_kind=hit.kind, aspect_name=None, policy_path=valence_policy_path)
        signed = base * factor * (1 if val == "positive" else (-1 if val == "negative" else 1))
        events.append(TransitEvent(hit.kind, hit.when_iso, hit.moving, hit.target, abs(hit.delta), hit.applying_or_separating, base, val, factor, signed))

    # Longitudinal aspects
    from .detectors_aspects import _load_policy as _asp_load
    asp_pol = _asp_load(aspects_policy_path)
    for ah in detect_aspects(prov, ticks, moving, target, policy_path=aspects_policy_path):
        aname = ah.kind.split("_", 1)[1]
        orbs_map = asp_pol["orbs_deg"][aname]
        from .core.bodies import body_class
        allow = min(orbs_map.get(body_class(moving), 2.0), orbs_map.get(body_class(target), 2.0))
        base = _score_from(ah.kind, ah.orb_abs, allow, ah.moving, ah.target, ah.applying_or_separating)
        val, factor = combine_valence(moving=ah.moving, target=ah.target, contact_kind=ah.kind, aspect_name=aname, policy_path=valence_policy_path)
        signed = base * factor * (1 if val == "positive" else (-1 if val == "negative" else 1))
        events.append(TransitEvent(ah.kind, ah.when_iso, ah.moving, ah.target, ah.orb_abs, ah.applying_or_separating, base, val, factor, signed))

    events.sort(key=lambda e: (e.when_iso, -e.signed_score))
    return events
# >>> AUTO-GEN END: AE Engine Hooks v1.2


def resolve_provider(name: str | None) -> object:
    """Compatibility shim for legacy callers."""
    return get_provider(name or "swiss")
