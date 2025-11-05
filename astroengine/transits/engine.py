"""Unified transit scanning services."""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Iterable, Iterator, Literal, Mapping, MutableMapping, Sequence

from ..chart.natal import BODY_EXPANSIONS, DEFAULT_BODIES, build_body_map
from ..core.angles import classify_relative_motion, signed_delta
from ..core.angles import normalize_degrees as _normalize_degrees
from ..core.bodies import canonical_name
from ..core.qcache import DEFAULT_QSEC, qbin, qcache
from ..core.time import to_tt
from ..detectors_aspects import AspectHit
from ..ephemeris import EphemerisAdapter, EphemerisConfig, EphemerisSample
from ..ephemeris.refinement import SECONDS_PER_DAY, RefineResult, refine_event
from ..ephemeris.swisseph_adapter import SwissEphemerisAdapter, VariantConfig

try:  # pragma: no cover - optional canonical schema
    from ..canonical import TransitEvent, events_from_any
except Exception:  # pragma: no cover - fallback for minimal installs
    TransitEvent = object  # type: ignore[misc, assignment]

    def events_from_any(x):  # type: ignore[no-redef]
        return list(x)


__all__ = [
    "TransitScanEvent",
    "TransitScanService",
    "TransitEngineConfig",
    "to_canonical_events",
    "FEATURE_LUNATIONS",
    "FEATURE_ECLIPSES",
    "FEATURE_STATIONS",
    "FEATURE_PROGRESSIONS",
    "FEATURE_DIRECTIONS",
    "FEATURE_RETURNS",
    "FEATURE_PROFECTIONS",
    "FEATURE_TIMELORDS",
    "TickCachingProvider",
    "scan_transits",
    "_aspect_definitions",
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


def to_canonical_events(events: Iterable[object]) -> Iterable[TransitEvent]:
    """Normalise events to the canonical :class:`TransitEvent` payload."""

    return events_from_any(events)


@dataclass(slots=True)
class TransitScanEvent:
    """Result yielded by :class:`TransitScanService` longitude scans."""

    timestamp: _dt.datetime
    body: int
    aspect_angle_deg: float
    reference_longitude: float
    offset_deg: float
    motion: str
    sample: EphemerisSample
    metadata: Mapping[str, object]

    def as_legacy_payload(self) -> Mapping[str, object]:
        """Return a mapping usable when constructing ``LegacyTransitEvent``."""

        return {
            "timestamp": self.timestamp,
            "body": str(self.body),
            "aspect": f"{self.aspect_angle_deg:.0f}",
            "orb": abs(self.offset_deg),
            "motion": self.motion,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class _RefinementSettings:
    """Internal container describing refinement behaviour for a scan."""

    enabled: bool
    max_iterations: int
    min_step_seconds: float


@dataclass(frozen=True)
class TransitEngineConfig:
    """Configuration toggles controlling coarse scan cadence and refinement."""

    coarse_step_hours: float = 6.0
    refinement_mode: Literal["fast", "accurate"] = "accurate"
    accurate_iterations: int = 12
    accurate_min_step_seconds: float = 30.0
    fast_min_step_seconds: float = 900.0
    cache_samples: bool = True

    def resolve_settings(self, override: str | None = None) -> _RefinementSettings:
        """Return refinement settings for the requested mode."""

        mode = (override or self.refinement_mode).lower()
        if mode == "fast":
            return _RefinementSettings(
                enabled=False,
                max_iterations=0,
                min_step_seconds=max(float(self.fast_min_step_seconds), 1.0),
            )
        if mode == "accurate":
            return _RefinementSettings(
                enabled=True,
                max_iterations=max(int(self.accurate_iterations), 1),
                min_step_seconds=max(float(self.accurate_min_step_seconds), 1.0),
            )
        raise ValueError(f"Unsupported refinement mode: {mode}")


def _quantized_refined_sample(
    adapter: EphemerisAdapter,
    body: int,
    moment: _dt.datetime,
    *,
    frame: str,
    accuracy: str,
) -> EphemerisSample:
    """Return a cached ephemeris sample quantized by ``accuracy`` and frame."""

    conversion = to_tt(moment)
    bin_key = qbin(conversion.jd_tt, DEFAULT_QSEC)
    cache_key = ("pos", int(body), bin_key, frame, accuracy, adapter.signature())
    cached = qcache.get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]
    sample = adapter.sample(body, conversion)
    qcache.put(cache_key, sample)
    return sample


@dataclass
class TransitScanService:
    """Lightweight transit scanning orchestrator shared by API layers."""

    adapter: EphemerisAdapter
    config: TransitEngineConfig = field(default_factory=TransitEngineConfig)

    @classmethod
    def with_default_adapter(
        cls,
        config: EphemerisConfig | None = None,
        *,
        engine_config: TransitEngineConfig | None = None,
    ) -> "TransitScanService":
        return cls(
            adapter=EphemerisAdapter(config),
            config=engine_config or TransitEngineConfig(),
        )

    def compute_positions(
        self,
        bodies: Sequence[int],
        moment: _dt.datetime,
    ) -> Mapping[int, float]:
        cache: MutableMapping[tuple[int, _dt.datetime], EphemerisSample]
        cache = {}

        def sample(body: int) -> EphemerisSample:
            if not self.config.cache_samples:
                return self.adapter.sample(body, moment)
            key = (body, moment)
            cached = cache.get(key)
            if cached is not None:
                return cached
            sampled = self.adapter.sample(body, moment)
            cache[key] = sampled
            return sampled

        return {body: sample(body).longitude for body in bodies}

    def iter_longitude_crossings(
        self,
        body: int,
        reference_longitude: float,
        aspect_angle_deg: float,
        start: _dt.datetime,
        end: _dt.datetime,
        *,
        step_hours: float | None = None,
        refinement: str | None = None,
    ) -> Iterator[TransitScanEvent]:
        if start > end:
            raise ValueError("scan_longitude_crossing requires start <= end")

        step_hours = (
            step_hours if step_hours is not None else self.config.coarse_step_hours
        )
        if step_hours <= 0:
            raise ValueError("step_hours must be positive")

        requested_mode = (refinement or self.config.refinement_mode).lower()
        settings = self.config.resolve_settings(refinement)

        tick_cache: MutableMapping[_dt.datetime, EphemerisSample] | None = (
            {} if self.config.cache_samples else None
        )

        def sample(moment: _dt.datetime) -> EphemerisSample:
            if tick_cache is not None:
                cached = tick_cache.get(moment)
                if cached is not None:
                    return cached
            sampled = self.adapter.sample(body, moment)
            if tick_cache is not None:
                tick_cache[moment] = sampled
            return sampled

        def compute_offset(candidate: EphemerisSample) -> float:
            return (
                signed_delta(candidate.longitude - reference_longitude)
                - aspect_angle_deg
            )

        coarse_step = _dt.timedelta(hours=float(step_hours))
        if coarse_step.total_seconds() <= 0.0:
            raise ValueError("step_hours must correspond to a positive duration")

        prev_time = start
        prev_sample = sample(prev_time)
        prev_offset = compute_offset(prev_sample)

        def iter_coarse_windows() -> Iterator[
            tuple[
                _dt.datetime,
                _dt.datetime,
                EphemerisSample,
                EphemerisSample,
                float,
                float,
            ]
        ]:
            nonlocal prev_time, prev_sample, prev_offset
            if start == end:
                return
            current_time = prev_time
            while current_time < end:
                next_time = current_time + coarse_step
                if next_time <= current_time:
                    raise ValueError("step_hours too small to advance timeline")
                if next_time > end:
                    next_time = end

                next_sample = sample(next_time)
                next_offset = compute_offset(next_sample)
                yield (
                    prev_time,
                    next_time,
                    prev_sample,
                    next_sample,
                    prev_offset,
                    next_offset,
                )
                prev_time = next_time
                prev_sample = next_sample
                prev_offset = next_offset
                current_time = next_time

        for (
            start_time,
            end_time,
            start_sample,
            end_sample,
            start_offset,
            end_offset,
        ) in iter_coarse_windows():
            bracketed = (
                start_offset == 0.0
                or end_offset == 0.0
                or (start_offset * end_offset < 0.0)
            )
            if not bracketed:
                continue

            retro_loop = start_sample.speed_longitude * end_sample.speed_longitude < 0.0

            coarse_candidates = (
                (start_time, start_sample, start_offset),
                (end_time, end_sample, end_offset),
            )
            final_time, final_sample, _ = min(
                coarse_candidates,
                key=lambda entry: (abs(entry[2]), entry[0]),
            )

            final_sample_offset = compute_offset(final_sample)

            bracket_span_seconds = (
                abs(end_sample.jd_utc - start_sample.jd_utc) * SECONDS_PER_DAY
            )
            precision_info: Mapping[str, object] = {
                "requested_sec": float(settings.min_step_seconds)
                if settings.enabled
                else float(coarse_step.total_seconds()),
                "achieved_sec": bracket_span_seconds,
                "method": "coarse",
                "iterations": 0,
                "status": (
                    "skipped"
                    if (not settings.enabled or retro_loop or start_time == end_time)
                    else "coarse_only",
                ),
            }

            if settings.enabled and not retro_loop and start_time != end_time:
                jd_start = start_sample.jd_utc
                jd_end = end_sample.jd_utc
                if jd_start <= jd_end:
                    base_jd = jd_start
                    base_time = start_time
                else:
                    base_jd = jd_end
                    base_time = end_time

                bracket = (min(jd_start, jd_end), max(jd_start, jd_end))

                def _delta_fn(jd_ut: float) -> float:
                    seconds = (jd_ut - base_jd) * SECONDS_PER_DAY
                    moment = base_time + _dt.timedelta(seconds=seconds)
                    sample = _quantized_refined_sample(
                        self.adapter,
                        body,
                        moment,
                        frame="geocentric_ecliptic",
                        accuracy=requested_mode,
                    )
                    return compute_offset(sample)

                result: RefineResult = refine_event(
                    bracket,
                    delta_fn=_delta_fn,
                    tol_seconds=settings.min_step_seconds,
                    max_iter=settings.max_iterations,
                )
                refined_seconds = (result.t_exact_jd - base_jd) * SECONDS_PER_DAY
                refined_time = base_time + _dt.timedelta(seconds=refined_seconds)
                refined_sample = _quantized_refined_sample(
                    self.adapter,
                    body,
                    refined_time,
                    frame="geocentric_ecliptic",
                    accuracy=requested_mode,
                )
                if tick_cache is not None:
                    tick_cache[refined_time] = refined_sample
                final_time = refined_time
                final_sample = refined_sample
                final_sample_offset = compute_offset(refined_sample)
                precision_info = {
                    "requested_sec": float(settings.min_step_seconds),
                    "achieved_sec": float(result.achieved_tol_sec),
                    "method": result.method,
                    "iterations": int(result.iterations),
                    "status": result.status,
                }

            final_offset = final_sample_offset

            final_separation = aspect_angle_deg + final_offset
            motion_state = classify_relative_motion(
                final_separation,
                aspect_angle_deg,
                final_sample.speed_longitude,
                0.0,
            )

            metadata = {
                "precision": dict(precision_info),
                "sample": {
                    "body": int(body),
                    "jd_utc": float(final_sample.jd_utc),
                    "jd_tt": float(final_sample.jd_tt),
                    "longitude": float(final_sample.longitude),
                    "speed_longitude": float(final_sample.speed_longitude),
                },
            }

            yield TransitScanEvent(
                timestamp=final_time,
                body=int(body),
                aspect_angle_deg=float(aspect_angle_deg),
                reference_longitude=float(reference_longitude),
                offset_deg=float(final_offset),
                motion=motion_state.state,
                sample=final_sample,
                metadata=metadata,
            )


class TickCachingProvider:
    """Memoize ``positions_ecliptic`` calls for a single scan session."""

    __slots__ = ("_provider", "_cache", "_canonical_cache")

    def __init__(self, provider: object) -> None:
        self._provider = provider
        self._cache: dict[
            tuple[str, tuple[str, ...]], Mapping[str, Mapping[str, float]]
        ] = {}
        self._canonical_cache: dict[frozenset[str], tuple[str, ...]] = {}

    def positions_ecliptic(
        self, iso_utc: str, bodies: Iterable[str] | None
    ) -> Mapping[str, Mapping[str, float]]:
        if bodies is None:
            raise TypeError("positions_ecliptic requires an iterable of body names")

        bodies_tuple = tuple(bodies)
        if not bodies_tuple:
            return {}

        lowered = tuple(name.lower() for name in bodies_tuple)
        canonical_key = frozenset(lowered)
        canonical = self._canonical_cache.get(canonical_key)
        if canonical is None:
            canonical = tuple(sorted(canonical_key))
            self._canonical_cache[canonical_key] = canonical
        key = (iso_utc, canonical)

        normalized = self._cache.get(key)
        if normalized is None:
            result = self._provider.positions_ecliptic(iso_utc, bodies_tuple)
            normalized = {name.lower(): data for name, data in result.items()}
            self._cache[key] = normalized

        return {
            name: normalized[name_lower]
            for name, name_lower in zip(bodies_tuple, lowered, strict=False)
            if name_lower in normalized
        }

    def __getattr__(self, name: str):  # pragma: no cover - delegation passthrough
        return getattr(self._provider, name)


_DEFAULT_TRANSIT_ASPECTS: dict[str, tuple[float, str]] = {
    "conjunction": (0.0, "major"),
    "sextile": (60.0, "major"),
    "square": (90.0, "major"),
    "trine": (120.0, "major"),
    "opposition": (180.0, "major"),
    "semisextile": (30.0, "minor"),
    "semisquare": (45.0, "minor"),
    "sesquisquare": (135.0, "minor"),
    "quincunx": (150.0, "minor"),
    "quintile": (72.0, "minor"),
    "biquintile": (144.0, "minor"),
    "semiquintile": (36.0, "minor"),
    "novile": (40.0, "harmonic"),
    "binovile": (80.0, "harmonic"),
    "septile": (51.4286, "harmonic"),
    "biseptile": (102.8571, "harmonic"),
    "triseptile": (154.2857, "harmonic"),
    "tredecile": (108.0, "harmonic"),
    "undecile": (32.7273, "harmonic"),
}


def _parse_iso8601(ts: str) -> _dt.datetime:
    dt = _dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=_dt.UTC)
    return dt.astimezone(_dt.UTC)


def _normalized_variant(value: str | None) -> str:
    lowered = (value or "mean").lower()
    return "true" if lowered == "true" else "mean"


def _variant_nodes(vc: VariantConfig) -> str:
    if hasattr(vc, "normalized_nodes"):
        return vc.normalized_nodes()
    return _normalized_variant(getattr(vc, "nodes_variant", "mean"))


def _variant_lilith(vc: VariantConfig) -> str:
    if hasattr(vc, "normalized_lilith"):
        return vc.normalized_lilith()
    return _normalized_variant(getattr(vc, "lilith_variant", "mean"))


def _body_name_map(
    names: Iterable[str] | None,
    *,
    adapter: SwissEphemerisAdapter | None = None,
) -> dict[str, int]:
    if not names:
        return {name: int(code) for name, code in DEFAULT_BODIES.items()}

    adapter = adapter or SwissEphemerisAdapter.get_default_adapter()
    variant_config = getattr(adapter, "_variant_config", None)
    if variant_config is None:
        chart_config = getattr(adapter, "chart_config", None)
        nodes_variant = getattr(chart_config, "nodes_variant", "mean")
        lilith_variant = getattr(chart_config, "lilith_variant", "mean")
        variant_config = VariantConfig(
            nodes_variant=nodes_variant,
            lilith_variant=lilith_variant,
        )

    catalog = build_body_map({key: True for key in BODY_EXPANSIONS}, base=DEFAULT_BODIES)
    lookup: dict[str, tuple[str, int]] = {}

    for display_name, code in catalog.items():
        lowered = display_name.lower()
        lookup.setdefault(lowered, (display_name, int(code)))
        canonical = canonical_name(display_name)
        if canonical:
            lookup.setdefault(canonical, (display_name, int(code)))

    mean_node_entry = lookup.get("mean node")
    true_node_entry = lookup.get("true node")
    mean_south_entry = lookup.get("mean south node")
    true_south_entry = lookup.get("true south node")
    node_variant = _variant_nodes(variant_config)
    preferred_node = true_node_entry if node_variant == "true" else mean_node_entry
    preferred_south = true_south_entry if node_variant == "true" else mean_south_entry

    if mean_node_entry:
        lookup["mean_node"] = mean_node_entry
        lookup.setdefault("mean node", mean_node_entry)
    if true_node_entry:
        lookup["true_node"] = true_node_entry
        lookup.setdefault("true node", true_node_entry)
    if preferred_node:
        for alias in ("node", "north_node", "nn"):
            lookup[alias] = preferred_node
    if preferred_south:
        for alias in ("south_node", "sn"):
            lookup[alias] = preferred_south

    mean_lilith_entry = lookup.get("black moon lilith (mean)")
    true_lilith_entry = lookup.get("black moon lilith (true)")
    lilith_variant = _variant_lilith(variant_config)
    preferred_lilith = true_lilith_entry if lilith_variant == "true" else mean_lilith_entry

    if mean_lilith_entry:
        for alias in ("mean_lilith", "mean lilith"):
            lookup[alias] = mean_lilith_entry
    if true_lilith_entry:
        for alias in ("true_lilith", "true lilith", "true black moon lilith"):
            lookup[alias] = true_lilith_entry
    if preferred_lilith:
        for alias in ("lilith", "black_moon_lilith", "black moon lilith"):
            lookup[alias] = preferred_lilith

    resolved: dict[str, int] = {}
    for candidate in names:
        key = canonical_name(str(candidate)) or str(candidate).strip().lower()
        if not key:
            continue
        entry = lookup.get(key)
        if entry is None:
            entry = lookup.get(str(candidate).strip().lower())
        if entry is None:
            continue
        display, code = entry
        resolved[display] = code
    return resolved


def _aspect_definitions(aspects: Iterable[object] | None) -> list[tuple[str, float, str]]:
    """Normalise caller provided aspects into ``(name, angle, family)`` tuples."""

    if not aspects:
        return [
            (name, angle, family)
            for name, (angle, family) in _DEFAULT_TRANSIT_ASPECTS.items()
        ]

    resolved: list[tuple[str, float, str]] = []
    for item in aspects:
        if isinstance(item, str):
            key = item.strip().lower()
            details = _DEFAULT_TRANSIT_ASPECTS.get(key)
            if details is not None:
                resolved.append((key, float(details[0]), details[1]))
        elif isinstance(item, (int, float)):
            angle = float(item)
            resolved.append((f"angle_{angle:g}", angle % 360.0, "custom"))
        elif isinstance(item, dict):
            name = str(item.get("name", "custom"))
            try:
                angle_val = float(item.get("angle", 0.0))
            except (TypeError, ValueError):
                continue
            family = str(item.get("family", "custom"))
            resolved.append((name.strip().lower() or "custom", angle_val % 360.0, family))
    if not resolved:
        return [
            (name, angle, family)
            for name, (angle, family) in _DEFAULT_TRANSIT_ASPECTS.items()
        ]
    return resolved


def scan_transits(
    natal_ts: str,
    start_ts: str,
    end_ts: str,
    *,
    aspects: Iterable[object] | None = None,
    orb_deg: float = 1.0,
    bodies: Iterable[str] | None = None,
    targets: Iterable[str] | None = None,
    step_days: float = 1.0,
) -> list[AspectHit]:
    """Scan transit contacts against natal longitudes."""

    start_dt = _parse_iso8601(start_ts)
    end_dt = _parse_iso8601(end_ts)
    if end_dt <= start_dt:
        return []

    natal_dt = _parse_iso8601(natal_ts)
    adapter = SwissEphemerisAdapter.get_default_adapter()
    service = TransitScanService.with_default_adapter()

    moving_map = _body_name_map(bodies, adapter=adapter)
    target_map = (
        _body_name_map(targets, adapter=adapter)
        if targets is not None
        else dict(moving_map)
    )
    if not moving_map or not target_map:
        return []

    natal_jd = adapter.julian_day(natal_dt)
    target_longitudes: dict[str, float] = {}
    for target_name, target_code in target_map.items():
        sample = adapter.body_position(natal_jd, target_code, body_name=target_name)
        target_longitudes[target_name] = float(sample.longitude % 360.0)

    aspect_defs = _aspect_definitions(aspects)
    if not aspect_defs:
        return []

    step_hours = max(float(step_days) * 24.0, 1.0)
    orb_allow = max(float(orb_deg), 0.0)
    partile_limit = min(orb_allow, 0.1)

    hits: list[AspectHit] = []
    for moving_name, moving_code in moving_map.items():
        for target_name, target_lon in target_longitudes.items():
            for aspect_name, aspect_angle, family in aspect_defs:
                events = service.iter_longitude_crossings(
                    moving_code,
                    target_lon,
                    aspect_angle,
                    start_dt,
                    end_dt,
                    step_hours=step_hours,
                    refinement="accurate",
                )
                for event in events:
                    event_time = event.timestamp
                    if event_time is None:
                        continue

                    moment = event_time.astimezone(_dt.UTC)
                    sample_meta = event.metadata.get("sample")

                    moving_lon: float
                    moving_speed: float
                    if isinstance(sample_meta, dict) and sample_meta.get("longitude") is not None:
                        moving_lon = float(sample_meta["longitude"]) % 360.0
                        moving_speed = float(sample_meta.get("speed_longitude", 0.0))
                    else:
                        sample = service.adapter.sample(moving_code, moment)
                        moving_lon = float(sample.longitude % 360.0)
                        moving_speed = float(sample.speed_longitude)

                    delta_lambda = _normalize_degrees(target_lon - moving_lon)
                    offset = signed_delta(delta_lambda - aspect_angle)
                    if abs(offset) > orb_allow:
                        continue
                    motion = classify_relative_motion(
                        aspect_angle + offset,
                        aspect_angle,
                        moving_speed,
                        0.0,
                    )
                    hits.append(
                        AspectHit(
                            kind=f"aspect_{aspect_name}",
                            when_iso=moment.isoformat().replace("+00:00", "Z"),
                            moving=moving_name,
                            target=target_name,
                            angle_deg=float(aspect_angle),
                            lon_moving=moving_lon,
                            lon_target=float(target_lon),
                            delta_lambda_deg=float(delta_lambda),
                            offset_deg=float(offset),
                            orb_abs=float(abs(offset)),
                            orb_allow=float(orb_allow),
                            is_partile=abs(offset) <= partile_limit,
                            applying_or_separating=motion.state,
                            family=family,
                            corridor_width_deg=None,
                            corridor_profile=None,
                        )
                    )

    hits.sort(key=lambda item: item.when_iso)
    return hits
