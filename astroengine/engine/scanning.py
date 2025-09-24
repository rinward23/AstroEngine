"""Transit scanning orchestrators."""

from __future__ import annotations

import datetime as dt

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from itertools import tee
from typing import Any, List, Mapping

from ..chart.config import ChartConfig
from ..core.engine import get_active_aspect_angles
from ..detectors import CoarseHit, detect_antiscia_contacts, detect_decl_contacts
from ..detectors import common as detectors_common
from ..detectors.common import body_lon, delta_deg, iso_to_jd, jd_to_iso, norm360
from ..detectors_aspects import AspectHit, detect_aspects
from ..ephemeris import EphemerisConfig, SwissEphemerisAdapter
from ..exporters import LegacyTransitEvent
from ..plugins import DetectorContext, get_plugin_manager
from ..providers import get_provider
from ..scoring import ScoreInputs, compute_score

from .context import (
    ScanFeaturePlan,
    ScanFeatureToggles,
    ScanProfileContext,
    build_scan_profile_context,
)
from .frames import FrameAwareProvider, TargetFrameResolver
from .profiles import resolve_profile

try:  # pragma: no cover - optional systems ship without full timelord stack
    from ..timelords.active import TimelordCalculator
except Exception:  # pragma: no cover - SyntaxError/import failures treated as optional

    class TimelordCalculator:  # type: ignore[no-redef]
        """Fallback that signals the timelord stack is unavailable."""

        def __init__(self, *_args, **_kwargs) -> None:  # pragma: no cover - error path
            raise RuntimeError("timelord subsystem unavailable")


try:  # pragma: no cover - optional for environments without pyswisseph
    import swisseph as swe  # type: ignore
except Exception:  # pragma: no cover
    swe = None  # type: ignore

__all__ = [
    "events_to_dicts",
    "scan_contacts",
    "get_active_aspect_angles",
    "resolve_provider",
    "fast_scan",
    "ScanConfig",
    "ScanFeaturePlan",
    "ScanFeatureToggles",
    "ScanProfileContext",
    "TargetFrameResolver",
    "build_scan_profile_context",
]


# >>> AUTO-GEN BEGIN: engine-feature-flags v1.0
# Feature flags (default OFF to preserve current behavior)
FEATURE_LUNATIONS = False
FEATURE_ECLIPSES = False
FEATURE_STATIONS = False
FEATURE_PROGRESSIONS = False
FEATURE_DIRECTIONS = False
FEATURE_RETURNS = False
FEATURE_PROFECTIONS = False
FEATURE_TIMELORDS = False
# >>> AUTO-GEN END: engine-feature-flags v1.0

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


class _TickCachingProvider:
    """Memoize ``positions_ecliptic`` calls for a single scan session."""

    __slots__ = ("_provider", "_cache")

    def __init__(self, provider: object) -> None:
        self._provider = provider
        self._cache: dict[tuple[str, tuple[str, ...]], Mapping[str, Mapping[str, float]]] = {}

    def positions_ecliptic(
        self, iso_utc: str, bodies: Iterable[str] | None
    ) -> Mapping[str, Mapping[str, float]]:
        if bodies is None:
            raise TypeError("positions_ecliptic requires an iterable of body names")

        bodies_tuple = tuple(bodies)
        if not bodies_tuple:
            return {}

        canonical = tuple(sorted({name.lower() for name in bodies_tuple}))
        key = (iso_utc, canonical)

        normalized = self._cache.get(key)
        if normalized is None:
            result = self._provider.positions_ecliptic(iso_utc, bodies_tuple)
            normalized = {name.lower(): data for name, data in result.items()}
            self._cache[key] = normalized

        return {
            name: normalized[name_lower]
            for name in bodies_tuple
            if (name_lower := name.lower()) in normalized
        }

    def __getattr__(self, name: str):  # pragma: no cover - delegation passthrough
        return getattr(self._provider, name)


if swe is not None:  # pragma: no cover - availability tested via swiss-marked tests
    for attr, name in (
        ("CERES", "ceres"),
        ("PALLAS", "pallas"),
        ("JUNO", "juno"),
        ("VESTA", "vesta"),
        ("CHIRON", "chiron"),
    ):
        code = getattr(swe, attr, None)
        if code is not None:
            _BODY_CODE_TO_NAME[int(code)] = name


@dataclass(slots=True)
class ScanConfig:
    body: int
    natal_lon_deg: float
    aspect_angle_deg: float
    orb_deg: float
    tick_minutes: int = 60


@dataclass(frozen=True, slots=True)
class _ScoringContext:
    """Shared scoring dependencies resolved from the active profile."""

    resonance_weights: Mapping[str, float] | None
    tradition: str | None
    chart_sect: str | None
    uncertainty_bias: Mapping[str, str] | None


def events_to_dicts(events: Iterable[LegacyTransitEvent]) -> List[dict]:
    """Convert :class:`LegacyTransitEvent` objects into JSON-friendly dictionaries."""

    return [event.to_dict() for event in events]


def _parse_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _attach_timelords(
    event: LegacyTransitEvent,
    calculator: TimelordCalculator | None,
) -> None:
    if not FEATURE_TIMELORDS or calculator is None:
        return
    stack = calculator.active_stack(_parse_iso_datetime(event.timestamp))
    event.metadata.setdefault("timelord_rulers", stack.rulers())
    event.metadata.setdefault("timelords", stack.to_dict())


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
    *,
    corridor_width: float | None = None,
    corridor_profile: str | None = None,
    resonance_weights: Mapping[str, float] | None = None,
    tradition: str | None = None,
    chart_sect: str | None = None,
    angle_deg: float | None = None,
    uncertainty_bias: Mapping[str, str] | None = None,
) -> float:
    """Use the scoring policy to assign a score for a detected contact."""

    score_inputs = ScoreInputs(
        kind=kind,
        orb_abs_deg=float(orb_abs),
        orb_allow_deg=float(orb_allow),
        moving=moving,
        target=target,
        applying_or_separating=phase,
        corridor_width_deg=corridor_width,
        corridor_profile=corridor_profile or "gaussian",
        resonance_weights=resonance_weights,
        tradition_profile=tradition,
        chart_sect=chart_sect,
        angle_deg=angle_deg,
        uncertainty_bias=uncertainty_bias,
    )
    return compute_score(score_inputs).score


def _event_from_decl(
    hit: CoarseHit,
    *,
    orb_allow: float,
    scoring: _ScoringContext,
) -> LegacyTransitEvent:
    effective_orb = float(hit.orb_allow) if hit.orb_allow is not None else float(orb_allow)
    score = _score_from_hit(
        hit.kind,
        abs(hit.delta),
        effective_orb,
        hit.moving,
        hit.target,
        hit.applying_or_separating,
        corridor_width=hit.corridor_width_deg,
        corridor_profile=hit.corridor_profile,
        resonance_weights=scoring.resonance_weights,
        tradition=scoring.tradition,
        chart_sect=scoring.chart_sect,
        angle_deg=None,
        uncertainty_bias=scoring.uncertainty_bias,
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
    if hit.corridor_width_deg is not None:
        metadata["corridor_width_deg"] = float(hit.corridor_width_deg)
    if hit.corridor_profile:
        metadata["corridor_profile"] = hit.corridor_profile
    return LegacyTransitEvent(
        kind=hit.kind,
        timestamp=hit.when_iso,
        moving=hit.moving,
        target=hit.target,
        orb_abs=float(abs(hit.delta)),
        orb_allow=float(effective_orb),
        applying_or_separating=hit.applying_or_separating,
        score=score,
        lon_moving=hit.lon_moving,
        lon_target=hit.lon_target,
        metadata=metadata,
    )


def _event_from_aspect(
    hit: AspectHit,
    *,
    scoring: _ScoringContext,
) -> LegacyTransitEvent:
    score = _score_from_hit(
        hit.kind,
        hit.orb_abs,
        hit.orb_allow,
        hit.moving,
        hit.target,
        hit.applying_or_separating,
        corridor_width=hit.corridor_width_deg,
        corridor_profile=hit.corridor_profile,
        resonance_weights=scoring.resonance_weights,
        tradition=scoring.tradition,
        chart_sect=scoring.chart_sect,
        angle_deg=hit.angle_deg,
        uncertainty_bias=scoring.uncertainty_bias,
    )
    metadata = {
        "angle_deg": float(hit.angle_deg),
        "delta_lambda_deg": float(hit.delta_lambda_deg),
        "offset_deg": float(hit.offset_deg),
        "partile": bool(hit.is_partile),
        "family": hit.family,
    }
    if hit.corridor_width_deg is not None:
        metadata["corridor_width_deg"] = float(hit.corridor_width_deg)
    if hit.corridor_profile:
        metadata["corridor_profile"] = hit.corridor_profile
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
        metadata=metadata,
    )


def _declination_events(
    provider: object,
    ticks: Iterable[str],
    *,
    moving: str,
    target: str,
    parallel_orb: float,
    contra_orb: float,
    toggles: ScanFeatureToggles,
    scoring: _ScoringContext,
) -> Iterable[LegacyTransitEvent]:
    if not (toggles.do_declination and (toggles.do_parallels or toggles.do_contras)):
        return

    for hit in detect_decl_contacts(
        provider,
        ticks,
        moving,
        target,
        parallel_orb,
        contra_orb,
    ):
        kind = str(hit.kind)
        if kind == "decl_parallel":
            if not toggles.do_parallels:
                continue
            allow = parallel_orb
        elif kind == "decl_contra":
            if not toggles.do_contras:
                continue
            allow = contra_orb
        else:
            if not toggles.do_declination:
                continue
            allow = parallel_orb if "parallel" in kind else contra_orb

        yield _event_from_decl(
            hit,
            orb_allow=allow,
            scoring=scoring,
        )


def _mirror_events(
    provider: object,
    ticks: Iterable[str],
    *,
    moving: str,
    target: str,
    antiscia_orb: float,
    contra_antiscia_orb: float,
    axis: str,
    toggles: ScanFeatureToggles,
    scoring: _ScoringContext,
) -> Iterable[LegacyTransitEvent]:
    if not toggles.do_mirrors:
        return

    for hit in detect_antiscia_contacts(
        provider,
        ticks,
        moving,
        target,
        antiscia_orb,
        contra_antiscia_orb,
        axis=axis,
    ):
        kind = str(hit.kind)
        allow = antiscia_orb if kind == "antiscia" else contra_antiscia_orb
        yield _event_from_decl(
            hit,
            orb_allow=allow,
            scoring=scoring,
        )


def _aspect_events(
    provider: object,
    ticks: Iterable[str],
    *,
    moving: str,
    target: str,
    policy_path: str | None,
    toggles: ScanFeatureToggles,
    scoring: _ScoringContext,
) -> Iterable[LegacyTransitEvent]:
    if not toggles.do_aspects:
        return

    for aspect_hit in detect_aspects(
        provider,
        ticks,
        moving,
        target,
        policy_path=policy_path,
    ):
        yield _event_from_aspect(
            aspect_hit,
            scoring=scoring,
        )


def scan_contacts(
    start_iso: str,
    end_iso: str,
    moving: str,
    target: str,
    provider_name: str = "swiss",
    *,
    ephemeris_config: EphemerisConfig | None = None,
    decl_parallel_orb: float | None = None,
    decl_contra_orb: float | None = None,
    antiscia_orb: float | None = None,
    contra_antiscia_orb: float | None = None,
    step_minutes: int = 60,
    aspects_policy_path: str | None = None,
    provider: object | None = None,
    target_frame: str = "transit",
    target_resolver: TargetFrameResolver | None = None,
    timelord_calculator: TimelordCalculator | None = None,
    chart_config: ChartConfig | None = None,
    profile: Mapping[str, Any] | None = None,
    profile_id: str | None = None,
    include_declination: bool = True,
    include_mirrors: bool = True,
    include_aspects: bool = True,
    antiscia_axis: str | None = None,
    tradition_profile: str | None = None,
    chart_sect: str | None = None,
) -> List[LegacyTransitEvent]:
    """Scan for declination, antiscia, and aspect contacts between two bodies."""

    base_provider = provider or get_provider(provider_name)
    if ephemeris_config is not None:
        configure = getattr(base_provider, "configure", None)
        if callable(configure):
            configure(
                topocentric=ephemeris_config.topocentric,
                observer=ephemeris_config.observer,
                sidereal=ephemeris_config.sidereal,
                time_scale=ephemeris_config.time_scale,
            )

    frame = (target_frame or "transit").lower()
    resolver = target_resolver
    if resolver is not None and frame != "transit" and resolver.frame != frame:
        resolver = TargetFrameResolver(
            frame,
            natal_chart=target_resolver.natal_chart,
            composite_chart=target_resolver.composite_chart,
            static_positions=target_resolver.static_positions,
        )

    scan_provider: object = base_provider
    if resolver is not None and resolver.overrides_target():
        scan_provider = FrameAwareProvider(base_provider, target, resolver)

    if chart_config is not None:
        SwissEphemerisAdapter.configure_defaults(chart_config=chart_config)

    profile_data = resolve_profile(profile, profile_id)
    profile_ctx = build_scan_profile_context(
        profile_data,
        moving=moving,
        target=target,
        decl_parallel_orb=decl_parallel_orb,
        decl_contra_orb=decl_contra_orb,
        antiscia_orb=antiscia_orb,
        contra_antiscia_orb=contra_antiscia_orb,
        antiscia_axis=antiscia_axis,
        tradition_profile=tradition_profile,
        chart_sect=chart_sect,
    )

    feature_plan = profile_ctx.plan_features(
        include_declination=include_declination,
        include_mirrors=include_mirrors,
        include_aspects=include_aspects,
    )
    toggles = feature_plan.toggles

    decl_parallel_allow = profile_ctx.decl_parallel_orb
    decl_contra_allow = profile_ctx.decl_contra_orb
    antiscia_allow = profile_ctx.antiscia_orb
    contra_antiscia_allow = profile_ctx.contra_antiscia_orb
    axis = profile_ctx.antiscia_axis

    scoring_ctx = _ScoringContext(
        resonance_weights=profile_ctx.resonance_weights,
        tradition=profile_ctx.tradition,
        chart_sect=profile_ctx.chart_sect,
        uncertainty_bias=profile_ctx.uncertainty_bias,
    )

    feature_metadata = feature_plan.plugin_metadata()

    tick_source = _iso_ticks(start_iso, end_iso, step_minutes=step_minutes)
    decl_ticks, mirror_ticks, aspect_ticks, plugin_ticks = tee(tick_source, 4)

    cached_provider = _TickCachingProvider(scan_provider)

    events: List[LegacyTransitEvent] = []

    def _append_event(event: LegacyTransitEvent) -> None:
        _attach_timelords(event, timelord_calculator)
        events.append(event)

    for event in _declination_events(
        cached_provider,
        decl_ticks,
        moving=moving,
        target=target,
        parallel_orb=decl_parallel_allow,
        contra_orb=decl_contra_allow,
        toggles=toggles,
        scoring=scoring_ctx,
    ):
        _append_event(event)

    for event in _mirror_events(
        cached_provider,
        mirror_ticks,
        moving=moving,
        target=target,
        antiscia_orb=antiscia_allow,
        contra_antiscia_orb=contra_antiscia_allow,
        axis=axis,
        toggles=toggles,
        scoring=scoring_ctx,
    ):
        _append_event(event)

    for event in _aspect_events(
        cached_provider,
        aspect_ticks,
        moving=moving,
        target=target,
        policy_path=aspects_policy_path,
        toggles=toggles,
        scoring=scoring_ctx,
    ):
        _append_event(event)

    plugin_context = DetectorContext(
        provider=cached_provider,
        provider_name=provider_name,
        start_iso=start_iso,
        end_iso=end_iso,
        ticks=tuple(plugin_ticks),
        moving=moving,
        target=target,
        options={
            "decl_parallel_orb": decl_parallel_allow,
            "decl_contra_orb": decl_contra_allow,
            "antiscia_orb": antiscia_allow,
            "contra_antiscia_orb": contra_antiscia_allow,
            "step_minutes": step_minutes,
            "aspects_policy_path": aspects_policy_path,
            "antiscia_axis": axis,
            **feature_metadata,
            "declination_flags": dict(profile_ctx.declination_flags),
            "antiscia_flags": dict(profile_ctx.antiscia_flags),
        },
        existing_events=tuple(events),
    )
    plugin_events = get_plugin_manager().run_detectors(plugin_context)
    if plugin_events:
        for plugin_event in plugin_events:
            _append_event(plugin_event)

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

    restore_cache_flag = detectors_common.USE_CACHE
    cache_available = getattr(detectors_common, "get_lon_daily", None) is not None
    dense_sampling = config.tick_minutes < 720
    toggled_cache = False
    if cache_available and dense_sampling and not restore_cache_flag:
        detectors_common.enable_cache(True)
        toggled_cache = True

    hits: List[dict] = []
    try:
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
    finally:
        if toggled_cache:
            detectors_common.enable_cache(restore_cache_flag)
    return hits

