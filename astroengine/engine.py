"""High level transit scanning helpers used by the CLI and unit tests."""

from __future__ import annotations

import datetime as dt

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, List, Mapping

import yaml

from .astro.declination import DEFAULT_ANTISCIA_AXIS
from .core.engine import get_active_aspect_angles
from .detectors import CoarseHit, detect_antiscia_contacts, detect_decl_contacts
from .detectors.common import body_lon, delta_deg, iso_to_jd, jd_to_iso, norm360
from .detectors_aspects import AspectHit, detect_aspects
from .exporters import LegacyTransitEvent
from .infrastructure.paths import profiles_dir
from .providers import get_provider
from .profiles import load_base_profile
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


_ANGLE_BODIES = {"asc", "mc", "ic", "dsc"}


def _normalize_body(name: str | None) -> str:
    return str(name or "").lower()


def _has_moon(*names: str) -> bool:
    return any(_normalize_body(name) == "moon" for name in names)


def _has_angle(*names: str) -> bool:
    return any(_normalize_body(name) in _ANGLE_BODIES for name in names)


def _orb_from_policy(
    policy: Any,
    *,
    moving: str,
    target: str,
    default: float,
    include_moon: bool = True,
    include_angles: bool = False,
    angle_key: str = "angular",
) -> float:
    if isinstance(policy, Mapping):
        value: Any = policy.get("default", default)
        if include_moon and _has_moon(moving, target):
            value = policy.get("moon", value)
        if include_angles and _has_angle(moving, target):
            value = policy.get(angle_key, value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)
    if policy is None:
        return float(default)
    try:
        return float(policy)
    except (TypeError, ValueError):
        return float(default)


def _resolve_declination_orb(
    profile: Mapping[str, Any],
    *,
    kind: str,
    moving: str,
    target: str,
    override: float | None,
) -> float:
    if override is not None:
        return float(override)
    policies = profile.get("orb_policies")
    policy: Any = None
    if isinstance(policies, Mapping):
        policy = policies.get("declination_aspect_orb_deg")
        if isinstance(policy, Mapping):
            kind_policy = policy.get(kind)
            if kind_policy is not None:
                policy = kind_policy
    return _orb_from_policy(
        policy,
        moving=moving,
        target=target,
        default=0.5,
    )


def _resolve_mirror_orb(
    profile: Mapping[str, Any],
    *,
    kind: str,
    moving: str,
    target: str,
    override: float | None,
) -> float:
    if override is not None:
        return float(override)
    policies = profile.get("orb_policies")
    policy: Any = None
    if isinstance(policies, Mapping):
        policy = policies.get("antiscia_orb_deg")
        if isinstance(policy, Mapping):
            kind_policy = policy.get(kind)
            if kind_policy is not None:
                policy = kind_policy
    return _orb_from_policy(
        policy,
        moving=moving,
        target=target,
        default=2.0,
        include_angles=True,
    )


def _load_profile_by_id(profile_id: str) -> Mapping[str, Any]:
    base = load_base_profile()
    profiles_path = profiles_dir()
    for suffix in (".yaml", ".yml", ".json"):
        candidate = profiles_path / f"{profile_id}{suffix}"
        if not candidate.exists():
            continue
        try:
            data = yaml.safe_load(candidate.read_text(encoding="utf-8"))
        except Exception:  # pragma: no cover - file parse errors bubble to callers later
            break
        if isinstance(data, Mapping):
            return data
        break
    return base


def _resolve_profile(
    profile: Mapping[str, Any] | None,
    profile_id: str | None,
) -> Mapping[str, Any]:
    if profile is not None:
        return profile
    if profile_id:
        if profile_id == "base":
            return load_base_profile()
        return _load_profile_by_id(profile_id)
    return load_base_profile()


def _resolve_antiscia_axis(
    profile: Mapping[str, Any], axis_override: str | None
) -> str:
    if axis_override:
        return axis_override
    feature_flags = profile.get("feature_flags")
    axis: Any = None
    if isinstance(feature_flags, Mapping):
        antiscia_flags = feature_flags.get("antiscia")
        if isinstance(antiscia_flags, Mapping):
            axis = antiscia_flags.get("axis")
    if axis is None:
        legacy = profile.get("antiscia")
        if isinstance(legacy, Mapping):
            axis = legacy.get("axis")
    if isinstance(axis, str) and axis.strip():
        return axis
    return DEFAULT_ANTISCIA_AXIS

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
    metadata: dict[str, float | str] = {
        "dec_moving": hit.dec_moving,
        "dec_target": hit.dec_target,
        "decl_moving": hit.dec_moving,
        "decl_target": hit.dec_target,
        "decl_delta": hit.delta,
    }
    if hit.mirror_lon is not None:
        metadata["mirror_lon"] = hit.mirror_lon
    if hit.axis:
        metadata["mirror_axis"] = hit.axis
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
        metadata=metadata,
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
    decl_parallel_orb: float | None = None,
    decl_contra_orb: float | None = None,
    antiscia_orb: float | None = None,
    contra_antiscia_orb: float | None = None,
    step_minutes: int = 60,
    aspects_policy_path: str | None = None,
    profile: Mapping[str, Any] | None = None,
    profile_id: str | None = None,
    include_declination: bool = True,
    include_mirrors: bool = True,
    include_aspects: bool = True,
    antiscia_axis: str | None = None,
) -> List[LegacyTransitEvent]:
    """Scan for declination, antiscia, and aspect contacts between two bodies."""

    profile_data = _resolve_profile(profile, profile_id)

    decl_parallel_allow = _resolve_declination_orb(
        profile_data,
        kind="parallel",
        moving=moving,
        target=target,
        override=decl_parallel_orb,
    )
    decl_contra_allow = _resolve_declination_orb(
        profile_data,
        kind="contraparallel",
        moving=moving,
        target=target,
        override=decl_contra_orb,
    )
    antiscia_allow = _resolve_mirror_orb(
        profile_data,
        kind="antiscia",
        moving=moving,
        target=target,
        override=antiscia_orb,
    )
    contra_antiscia_allow = _resolve_mirror_orb(
        profile_data,
        kind="contra_antiscia",
        moving=moving,
        target=target,
        override=contra_antiscia_orb,
    )
    axis = _resolve_antiscia_axis(profile_data, antiscia_axis)

    feature_flags = profile_data.get("feature_flags")
    decl_flags: Mapping[str, Any] = {}
    antiscia_flags: Mapping[str, Any] = {}
    if isinstance(feature_flags, Mapping):
        candidate = feature_flags.get("declination_aspects")
        if isinstance(candidate, Mapping):
            decl_flags = candidate
        candidate = feature_flags.get("antiscia")
        if isinstance(candidate, Mapping):
            antiscia_flags = candidate

    decl_enabled = bool(decl_flags.get("enabled", True))
    parallel_enabled = bool(decl_flags.get("parallels", True))
    contra_enabled = bool(decl_flags.get("contraparallels", True))
    antiscia_enabled = bool(antiscia_flags.get("enabled", True))

    do_declination = include_declination and decl_enabled
    do_parallels = parallel_enabled
    do_contras = contra_enabled
    do_mirrors = include_mirrors and antiscia_enabled
    do_aspects = include_aspects

    provider = get_provider(provider_name)
    ticks = list(_iso_ticks(start_iso, end_iso, step_minutes=step_minutes))

    events: List[LegacyTransitEvent] = []

    if do_declination:
        for hit in detect_decl_contacts(
            provider,
            ticks,
            moving,
            target,
            decl_parallel_allow,
            decl_contra_allow,
        ):
            if hit.kind == "decl_parallel" and not do_parallels:
                continue
            if hit.kind == "decl_contra" and not do_contras:
                continue
            allow = (
                decl_parallel_allow
                if hit.kind == "decl_parallel"
                else decl_contra_allow
            )
            events.append(_event_from_decl(hit, orb_allow=allow))

    if do_mirrors:
        for hit in detect_antiscia_contacts(
            provider,
            ticks,
            moving,
            target,
            antiscia_allow,
            contra_antiscia_allow,
            axis=axis,
        ):
            allow = (
                antiscia_allow
                if hit.kind == "antiscia"
                else contra_antiscia_allow
            )
            events.append(_event_from_decl(hit, orb_allow=allow))

    if do_aspects:
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
