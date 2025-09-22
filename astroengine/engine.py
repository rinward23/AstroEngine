"""High level transit scanning helpers used by the CLI and unit tests."""

from __future__ import annotations

import datetime as dt

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, List

from .core.engine import get_active_aspect_angles
from .detectors import CoarseHit, detect_antiscia_contacts, detect_decl_contacts
from .detectors.common import body_lon, delta_deg, iso_to_jd, jd_to_iso, norm360
from .detectors_aspects import AspectHit, detect_aspects
from .ephemeris import EphemerisConfig
from .exporters import LegacyTransitEvent
from .providers import get_provider
from .scoring import ScoreInputs, compute_score

# >>> AUTO-GEN BEGIN: engine-feature-flags v1.0
# Feature flags (default OFF to preserve current behavior)
FEATURE_LUNATIONS = False
FEATURE_ECLIPSES = False
FEATURE_STATIONS = False
FEATURE_PROGRESSIONS = False
FEATURE_DIRECTIONS = False
FEATURE_RETURNS = False
FEATURE_PROFECTIONS = False
# >>> AUTO-GEN END: engine-feature-flags v1.0

__all__ = [
    "events_to_dicts",
    "scan_contacts",
    "get_active_aspect_angles",
    "resolve_provider",
    "fast_scan",
    "ScanConfig",
]

_BODY_CODE_TO_NAME = {
    0: "sun",
    1: "moon",
    2: "mercury",
    3: "venus",
    4: "mars",
    5: "jupiter",
    6: "saturn",
    7: "uranus",
    8: "neptune",
    9: "pluto",
}


@dataclass(slots=True)
class ScanConfig:
    body: int
    natal_lon_deg: float
    aspect_angle_deg: float
    orb_deg: float
    tick_minutes: int = 60


def events_to_dicts(events: Iterable[LegacyTransitEvent]) -> List[dict]:
    """Convert :class:`LegacyTransitEvent` objects into JSON-friendly dictionaries."""

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


def _event_from_decl(hit: CoarseHit, *, orb_allow: float) -> LegacyTransitEvent:
    score = _score_from_hit(
        hit.kind,
        abs(hit.delta),
        orb_allow,
        hit.moving,
        hit.target,
        hit.applying_or_separating,
    )
    return LegacyTransitEvent(
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


def _event_from_aspect(hit: AspectHit) -> LegacyTransitEvent:
    score = _score_from_hit(
        hit.kind,
        hit.orb_abs,
        hit.orb_allow,
        hit.moving,
        hit.target,
        hit.applying_or_separating,
    )
    return LegacyTransitEvent(
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
    ephemeris_config: EphemerisConfig | None = None,
    decl_parallel_orb: float = 0.5,
    decl_contra_orb: float = 0.5,
    antiscia_orb: float = 2.0,
    contra_antiscia_orb: float = 2.0,
    step_minutes: int = 60,
    aspects_policy_path: str | None = None,
) -> List[LegacyTransitEvent]:
    """Scan for declination, antiscia, and aspect contacts between two bodies."""

    provider = get_provider(provider_name)
    if ephemeris_config is not None:
        configure = getattr(provider, "configure", None)
        if callable(configure):
            configure(
                topocentric=ephemeris_config.topocentric,
                observer=ephemeris_config.observer,
                sidereal=ephemeris_config.sidereal,
                time_scale=ephemeris_config.time_scale,
            )
    ticks = list(_iso_ticks(start_iso, end_iso, step_minutes=step_minutes))

    events: List[LegacyTransitEvent] = []

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


def _datetime_to_jd(moment: datetime) -> float:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    else:
        moment = moment.astimezone(timezone.utc)
    iso = moment.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return iso_to_jd(iso)


def fast_scan(start: datetime, end: datetime, config: ScanConfig) -> List[dict]:
    """Lightweight aspect scanner using Swiss Ephemeris positions."""

    body_name = _BODY_CODE_TO_NAME.get(config.body)
    if body_name is None:
        raise ValueError(f"Unsupported body code: {config.body}")

    start_jd = _datetime_to_jd(start)
    end_jd = _datetime_to_jd(end)
    if end_jd <= start_jd:
        return []

    step_days = config.tick_minutes / (24.0 * 60.0)
    target_lon = norm360(config.natal_lon_deg + config.aspect_angle_deg)

    hits: List[dict] = []
    current = start_jd
    while current <= end_jd:
        lon = body_lon(current, body_name)
        delta = delta_deg(lon, target_lon)
        if abs(delta) <= config.orb_deg:
            hits.append(
                {
                    "timestamp": jd_to_iso(current),
                    "body": body_name,
                    "longitude": lon,
                    "delta": delta,
                }
            )
        current += step_days
    return hits
