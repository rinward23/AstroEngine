
from __future__ import annotations
import datetime as dt
from typing import Iterable, List

from .providers import get_provider
from .detectors import detect_decl_contacts, detect_antiscia_contacts, CoarseHit
from .detectors_aspects import detect_aspects, AspectHit
from .exporters import TransitEvent
from .scoring import compute_score, ScoreInputs



def _iso_ticks(start_iso: str, end_iso: str, step_minutes: int = 60) -> Iterable[str]:
    t0 = dt.datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    t1 = dt.datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
    step = dt.timedelta(minutes=step_minutes)
    while t0 <= t1:
        yield t0.replace(tzinfo=dt.timezone.utc).isoformat().replace("+00:00", "Z")
        t0 += step



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

) -> List[TransitEvent]:
    prov = get_provider(provider_name)
    ticks = list(_iso_ticks(start_iso, end_iso, step_minutes=step_minutes))
    events: List[TransitEvent] = []

    # Declination & mirrors
    for hit in detect_decl_contacts(prov, ticks, moving, target, decl_parallel_orb, decl_contra_orb):
        allow = decl_parallel_orb if hit.kind == "decl_parallel" else decl_contra_orb

    # Longitudinal aspects
    from .detectors_aspects import _load_policy as _asp_load
    asp_pol = _asp_load(aspects_policy_path)



def resolve_provider(name: str | None) -> object:
    """Compatibility shim for legacy callers."""
    return get_provider(name or "swiss")
