"""High level transit scanning helpers used by the CLI and unit tests."""

from __future__ import annotations

import datetime as dt

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from typing import Any, Iterable, List, Mapping, MutableMapping




import yaml


from .astro.declination import DEFAULT_ANTISCIA_AXIS
from .chart.config import ChartConfig

from .core.engine import get_active_aspect_angles
from .detectors import CoarseHit, detect_antiscia_contacts, detect_decl_contacts
from .detectors.common import body_lon, delta_deg, iso_to_jd, jd_to_iso, norm360

try:  # pragma: no cover - optional for environments without pyswisseph
    import swisseph as swe  # type: ignore
except Exception:  # pragma: no cover
    swe = None  # type: ignore
from .detectors_aspects import AspectHit, detect_aspects
from .ephemeris import EphemerisConfig
from .exporters import LegacyTransitEvent

from .infrastructure.paths import profiles_dir
from .plugins import DetectorContext, get_plugin_manager

from .providers import get_provider
from .profiles import load_base_profile, load_resonance_weights
from .scoring import ScoreInputs, compute_score
from .canonical import BodyPosition
from .chart.natal import NatalChart
from .chart.progressions import ProgressedChart, compute_secondary_progressed_chart
from .chart.directions import DirectedChart, compute_solar_arc_chart
from .chart.composite import CompositeChart

try:  # pragma: no cover - optional systems ship without full timelord stack
    from .timelords.active import TimelordCalculator
except Exception:  # pragma: no cover - SyntaxError/import failures treated as optional

    class TimelordCalculator:  # type: ignore[no-redef]
        """Fallback that signals the timelord stack is unavailable."""

        def __init__(self, *_args, **_kwargs) -> None:  # pragma: no cover - error path
            raise RuntimeError("timelord subsystem unavailable")


from .ephemeris import SwissEphemerisAdapter


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

__all__ = [
    "events_to_dicts",
    "scan_contacts",
    "get_active_aspect_angles",
    "resolve_provider",
    "fast_scan",
    "ScanConfig",
    "TargetFrameResolver",
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


class TargetFrameResolver:
    """Resolve target body positions for alternate reference frames."""

    def __init__(
        self,
        frame: str,
        *,
        natal_chart: NatalChart | None = None,
        composite_chart: CompositeChart | None = None,
        static_positions: Mapping[str, float] | None = None,
    ) -> None:
        self.frame = frame.lower()
        self._progressed_cache: MutableMapping[str, ProgressedChart] = {}
        self._directed_cache: MutableMapping[str, DirectedChart] = {}
        self._static_positions: MutableMapping[str, float] = {}
        self._natal_chart: NatalChart | None = None
        self._composite_chart: CompositeChart | None = None
        self._name_lookup: dict[str, str] = {}
        self.static_positions = static_positions
        self.natal_chart = natal_chart
        self.composite_chart = composite_chart

    @property
    def natal_chart(self) -> NatalChart | None:
        return self._natal_chart

    @natal_chart.setter
    def natal_chart(self, chart: NatalChart | None) -> None:
        self._natal_chart = chart
        self._progressed_cache.clear()
        self._directed_cache.clear()
        self._name_lookup = self._build_name_lookup()

    @property
    def composite_chart(self) -> CompositeChart | None:
        return self._composite_chart

    @composite_chart.setter
    def composite_chart(self, chart: CompositeChart | None) -> None:
        self._composite_chart = chart
        self._name_lookup = self._build_name_lookup()

    @staticmethod
    def _normalize_iso(ts: str) -> tuple[str, datetime]:
        """Return a normalized ISO string and UTC datetime for ``ts``."""

        dt_obj = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        dt_utc = dt_obj.astimezone(timezone.utc) if dt_obj.tzinfo else dt_obj.replace(tzinfo=timezone.utc)
        dt_utc = dt_utc.replace(microsecond=0)
        normalized = dt_utc.isoformat().replace("+00:00", "Z")
        return normalized, dt_utc

    def overrides_target(self) -> bool:
        if self.frame == "natal":
            return bool(self._static_positions) or self.natal_chart is not None
        if self.frame in {"progressed", "directed", "composite"}:
            return True
        return False

    @property
    def static_positions(self) -> Mapping[str, float]:
        return dict(self._static_positions)

    @static_positions.setter
    def static_positions(self, positions: Mapping[str, float] | None) -> None:
        source = positions or {}
        self._static_positions = {
            str(key).lower(): float(value) % 360.0 for key, value in source.items()
        }
        self._name_lookup = self._build_name_lookup()

    def set_static_position(self, name: str, longitude: float) -> None:
        """Register or update a static position and refresh cached lookups."""

        self._static_positions[str(name).lower()] = float(longitude) % 360.0
        self._name_lookup = self._build_name_lookup()

    def remove_static_position(self, name: str) -> None:
        """Remove a static position override when present."""

        normalized = str(name).lower()
        if normalized in self._static_positions:
            del self._static_positions[normalized]
            self._name_lookup = self._build_name_lookup()

    def clear_temporal_caches(self) -> None:
        """Drop progressed/directed caches, forcing recomputation on next access."""

        self._progressed_cache.clear()
        self._directed_cache.clear()

    def _build_name_lookup(self) -> dict[str, str]:
        """Return mapping from lowercase body names to canonical identifiers."""

        lookup: dict[str, str] = {}

        def _record(names: Iterable[str]) -> None:
            for raw_name in names:
                normalized = str(raw_name).lower()
                lookup.setdefault(normalized, str(raw_name))

        _record(self._static_positions.keys())
        if self.natal_chart is not None:
            _record(self.natal_chart.positions.keys())
        if self.composite_chart is not None:
            _record(self.composite_chart.positions.keys())
        return lookup

    def _resolve_body_name(self, body: str) -> str:
        body_lower = body.lower()
        name = self._name_lookup.get(body_lower)
        if name is not None:
            return name
        self._name_lookup = self._build_name_lookup()
        return self._name_lookup.get(body_lower, body)

    def _natal_body(self, body: str) -> BodyPosition | None:
        if self.natal_chart is None:
            return None
        name = self._resolve_body_name(body)
        return self.natal_chart.positions.get(name)

    def _progressed_for(self, iso_ts: str) -> ProgressedChart:
        key, moment = self._normalize_iso(iso_ts)
        cached = self._progressed_cache.get(key)
        if cached is not None:
            return cached
        if self.natal_chart is None:
            raise ValueError("Progressed frame requires a natal chart")
        progressed = compute_secondary_progressed_chart(self.natal_chart, moment)
        self._progressed_cache[key] = progressed
        return progressed

    def _directed_for(self, iso_ts: str) -> DirectedChart:
        key, moment = self._normalize_iso(iso_ts)
        cached = self._directed_cache.get(key)
        if cached is not None:
            return cached
        if self.natal_chart is None:
            raise ValueError("Directed frame requires a natal chart")
        directed = compute_solar_arc_chart(self.natal_chart, moment)
        self._directed_cache[key] = directed
        return directed

    def _static_position(self, body: str) -> Mapping[str, float] | None:
        body_lower = body.lower()
        if body_lower not in self._static_positions:
            return None
        lon = self._static_positions[body_lower]
        return {"lon": lon, "lat": 0.0, "decl": 0.0, "speed_lon": 0.0}

    def position_dict(self, iso_ts: str, body: str) -> Mapping[str, float]:
        frame = self.frame
        if frame == "natal":
            static = self._static_position(body)
            if static is not None:
                return static
            natal = self._natal_body(body)
            if natal is None:
                raise KeyError(f"Body '{body}' not present in natal chart")
            return {
                "lon": natal.longitude % 360.0,
                "lat": natal.latitude,
                "decl": natal.declination,
                "speed_lon": natal.speed_longitude,
            }

        if frame == "progressed":
            progressed = self._progressed_for(iso_ts).chart
            name = self._resolve_body_name(body)
            pos = progressed.positions.get(name)
            if pos is None:
                raise KeyError(f"Body '{body}' not present in progressed chart")
            return {
                "lon": pos.longitude % 360.0,
                "lat": pos.latitude,
                "decl": pos.declination,
                "speed_lon": pos.speed_longitude,
            }

        if frame == "directed":
            directed = self._directed_for(iso_ts)
            name = self._resolve_body_name(body)
            lon = directed.positions.get(name)
            if lon is None:
                raise KeyError(f"Body '{body}' not present in directed chart")
            natal = self._natal_body(body)
            lat = natal.latitude if natal is not None else 0.0
            decl = natal.declination if natal is not None else 0.0
            return {"lon": lon % 360.0, "lat": lat, "decl": decl, "speed_lon": 0.0}

        if frame == "composite":
            if self.composite_chart is None:
                raise ValueError("Composite frame requires a composite chart")
            name = self._resolve_body_name(body)
            pos = self.composite_chart.positions.get(name)
            if pos is None:
                raise KeyError(f"Body '{body}' not present in composite chart")
            return {
                "lon": pos.midpoint_longitude % 360.0,
                "lat": pos.latitude,
                "decl": pos.declination,
                "speed_lon": pos.speed_longitude,
            }

        raise ValueError(f"Unsupported target frame '{self.frame}'")


class FrameAwareProvider:
    """Provider wrapper that injects alternate frame target positions."""

    def __init__(self, provider, target: str, resolver: TargetFrameResolver) -> None:
        self._provider = provider
        self._target = target.lower()
        self._resolver = resolver

    def positions_ecliptic(self, iso_utc: str, bodies: Iterable[str]):
        base = dict(self._provider.positions_ecliptic(iso_utc, bodies))
        if not self._resolver.overrides_target():
            return base

        target_lower = self._target
        replaced = False
        for name in list(base.keys()):
            if name.lower() == target_lower:
                base[name] = dict(self._resolver.position_dict(iso_utc, name))
                replaced = True
        if not replaced:
            for requested in bodies:
                if str(requested).lower() == target_lower:
                    base[str(requested)] = dict(
                        self._resolver.position_dict(iso_utc, str(requested))
                    )
                    break
        return base

    def position(self, body: str, ts_utc: str) -> BodyPosition:
        if self._resolver.overrides_target() and body.lower() == self._target:
            data = self._resolver.position_dict(ts_utc, body)
            return BodyPosition(
                lon=float(data["lon"]),
                lat=float(data.get("lat", 0.0)),
                dec=float(data.get("decl", 0.0)),
                speed_lon=float(data.get("speed_lon", 0.0)),
            )
        return self._provider.position(body, ts_utc)

    def __getattr__(self, item):  # pragma: no cover - passthrough
        return getattr(self._provider, item)


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
    resonance_weights: Mapping[str, float] | None,
    tradition: str | None,
    chart_sect: str | None,
    uncertainty_bias: Mapping[str, str] | None,
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
        resonance_weights=resonance_weights,
        tradition=tradition,
        chart_sect=chart_sect,
        angle_deg=None,
        uncertainty_bias=uncertainty_bias,
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
        orb_abs=abs(hit.delta),
        orb_allow=effective_orb,
        applying_or_separating=hit.applying_or_separating,
        score=score,
        lon_moving=hit.lon_moving,
        lon_target=hit.lon_target,
        metadata=metadata,
    )


def _event_from_aspect(
    hit: AspectHit,
    *,
    resonance_weights: Mapping[str, float] | None,
    tradition: str | None,
    chart_sect: str | None,
    uncertainty_bias: Mapping[str, str] | None,
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
        resonance_weights=resonance_weights,
        tradition=tradition,
        chart_sect=chart_sect,
        angle_deg=hit.angle_deg,
        uncertainty_bias=uncertainty_bias,
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

    profile_data = _resolve_profile(profile, profile_id)
    resonance_weights_map = load_resonance_weights(profile_data).as_mapping()
    uncertainty_bias_map: Mapping[str, str] | None = None
    resonance_section = (
        profile_data.get("resonance") if isinstance(profile_data, Mapping) else None
    )
    if isinstance(resonance_section, Mapping):
        bias_section = resonance_section.get("uncertainty_bias")
        if isinstance(bias_section, Mapping):

            uncertainty_bias_map = {
                str(key): str(value) for key, value in bias_section.items()
            }

    tradition = tradition_profile
    tradition_section = (
        profile_data.get("tradition") if isinstance(profile_data, Mapping) else None
    )

    if not tradition and isinstance(tradition_section, Mapping):
        default_trad = tradition_section.get("default")
        if isinstance(default_trad, str):
            tradition = default_trad


    chart_sect_value = chart_sect
    natal_section = (
        profile_data.get("natal") if isinstance(profile_data, Mapping) else None
    )
    if not chart_sect_value and isinstance(natal_section, Mapping):
        candidate_sect = natal_section.get("chart_sect")
        if isinstance(candidate_sect, str):
            chart_sect_value = candidate_sect


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


    feature_flags = (
        profile_data.get("feature_flags") if isinstance(profile_data, Mapping) else None
    )

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
    do_parallels = do_declination and parallel_enabled
    do_contras = do_declination and contra_enabled
    do_mirrors = include_mirrors and antiscia_enabled
    do_aspects = include_aspects


    ticks = list(_iso_ticks(start_iso, end_iso, step_minutes=step_minutes))

    events: List[LegacyTransitEvent] = []


    def _append_event(event: LegacyTransitEvent) -> None:
        _attach_timelords(event, timelord_calculator)
        events.append(event)

    if do_declination:
        for hit in detect_decl_contacts(
            scan_provider,
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
                decl_parallel_allow if hit.kind == "decl_parallel" else decl_contra_allow
            )
            _append_event(
                _event_from_decl(
                    hit,
                    orb_allow=allow,
                    resonance_weights=resonance_weights_map,
                    tradition=tradition,
                    chart_sect=chart_sect_value,
                    uncertainty_bias=uncertainty_bias_map,
                )
            )

    if do_mirrors:
        for hit in detect_antiscia_contacts(
            scan_provider,
            ticks,
            moving,
            target,
            antiscia_allow,
            contra_antiscia_allow,
            axis=axis,
        ):
            allow = (
                antiscia_allow if hit.kind == "antiscia" else contra_antiscia_allow
            )
            _append_event(
                _event_from_decl(
                    hit,
                    orb_allow=allow,
                    resonance_weights=resonance_weights_map,
                    tradition=tradition,
                    chart_sect=chart_sect_value,
                    uncertainty_bias=uncertainty_bias_map,
                )
            )

    if do_aspects:
        for aspect_hit in detect_aspects(
            scan_provider,
            ticks,
            moving,
            target,
            policy_path=aspects_policy_path,
        ):
            _append_event(
                _event_from_aspect(
                    aspect_hit,
                    resonance_weights=resonance_weights_map,
                    tradition=tradition,
                    chart_sect=chart_sect_value,
                    uncertainty_bias=uncertainty_bias_map,
                )
            )

    plugin_context = DetectorContext(
        provider=scan_provider,
        provider_name=provider_name,
        start_iso=start_iso,
        end_iso=end_iso,
        ticks=tuple(ticks),
        moving=moving,
        target=target,
        options={
            "decl_parallel_orb": decl_parallel_allow,
            "decl_contra_orb": decl_contra_allow,
            "antiscia_orb": antiscia_allow,
            "contra_antiscia_orb": contra_antiscia_allow,
            "step_minutes": step_minutes,
            "aspects_policy_path": aspects_policy_path,
            "include_declination": include_declination,
            "include_mirrors": include_mirrors,
            "include_aspects": include_aspects,
            "antiscia_axis": axis,
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
