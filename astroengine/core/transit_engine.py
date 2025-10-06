"""Transit scanning utilities built on top of the ephemeris adapter."""

# isort: skip_file

from __future__ import annotations

import datetime as _dt

# >>> AUTO-GEN BEGIN: Canonical Scan Adapter v1.0
from collections.abc import Iterable
from collections.abc import Iterable as _TypingIterable
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any as _TypingAny, Literal, cast

from ..chart.natal import DEFAULT_BODIES
from ..detectors_aspects import AspectHit
from ..ephemeris import EphemerisAdapter, EphemerisConfig, EphemerisSample
from ..ephemeris.swisseph_adapter import SwissEphemerisAdapter
from ..ephemeris.refinement import SECONDS_PER_DAY, RefineResult, refine_event
from .qcache import DEFAULT_QSEC, qbin, qcache
from .time import to_tt
from .angles import classify_relative_motion, signed_delta
from .angles import normalize_degrees as _normalize_degrees
from .api import TransitEvent as LegacyTransitEvent

try:
    from ..canonical import TransitEvent, events_from_any
except Exception:  # pragma: no cover
    TransitEvent = object  # type: ignore

    def events_from_any(x):
        return list(x)  # type: ignore


def to_canonical_events(
    events: _TypingIterable[_TypingAny],
) -> _TypingIterable[TransitEvent]:
    """Normalize engine or legacy events to :class:`~astroengine.canonical.TransitEvent`."""

    return events_from_any(events)


# >>> AUTO-GEN END: Canonical Scan Adapter v1.0

__all__ = ["TransitEngine", "TransitEngineConfig"]


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
        return cast(EphemerisSample, cached)
    sample = adapter.sample(body, conversion)
    qcache.put(cache_key, sample)
    return sample


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


@dataclass
class TransitEngine:
    """Lightweight transit scanning orchestrator."""

    adapter: EphemerisAdapter
    config: TransitEngineConfig = field(default_factory=TransitEngineConfig)

    @classmethod
    def with_default_adapter(
        cls,
        config: EphemerisConfig | None = None,
        *,
        engine_config: TransitEngineConfig | None = None,
    ) -> TransitEngine:
        return cls(
            adapter=EphemerisAdapter(config),
            config=engine_config or TransitEngineConfig(),
        )

    def compute_positions(
        self,
        bodies: Sequence[int],
        moment: _dt.datetime,
    ) -> dict[int, float]:
        cache: dict[tuple[int, _dt.datetime], EphemerisSample] = {}

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

    def scan_longitude_crossing(
        self,
        body: int,
        reference_longitude: float,
        aspect_angle_deg: float,
        start: _dt.datetime,
        end: _dt.datetime,
        *,
        step_hours: float | None = None,
        refinement: str | None = None,
    ) -> Iterable[LegacyTransitEvent]:
        if start > end:
            raise ValueError("scan_longitude_crossing requires start <= end")

        step_hours = (
            step_hours if step_hours is not None else self.config.coarse_step_hours
        )
        if step_hours <= 0:
            raise ValueError("step_hours must be positive")

        requested_mode = (refinement or self.config.refinement_mode).lower()
        settings = self.config.resolve_settings(refinement)

        tick_cache: dict[_dt.datetime, EphemerisSample] | None = (
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

        # ``prev`` variables seed the streaming coarse sampler.  This avoids
        # materialising large intermediate lists when callers scan multi-month
        # windows with sub-hour cadences.
        prev_time = start
        prev_sample = sample(prev_time)
        prev_offset = compute_offset(prev_sample)

        def iter_coarse_windows():
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

            bracket_span_seconds = abs(end_sample.jd_utc - start_sample.jd_utc) * SECONDS_PER_DAY
            precision_info = {
                "requested_sec": float(settings.min_step_seconds)
                if settings.enabled
                else float(coarse_step.total_seconds()),
                "achieved_sec": bracket_span_seconds,
                "method": "coarse",
                "iterations": 0,
                "status": (
                    "skipped"
                    if (not settings.enabled or retro_loop or start_time == end_time)
                    else "coarse_only"
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

            # Capture the final ephemeris sample so downstream consumers can reuse
            # the precise longitude without re-sampling the Swiss Ephemeris.
            metadata = {
                "precision": precision_info,
                "sample": {
                    "body": int(body),
                    "jd_utc": float(final_sample.jd_utc),
                    "jd_tt": float(final_sample.jd_tt),
                    "longitude": float(final_sample.longitude),
                    "speed_longitude": float(final_sample.speed_longitude),
                },
            }

            yield LegacyTransitEvent(
                timestamp=final_time,
                body=str(body),
                target="natal",  # placeholder until natal metadata wired in
                aspect=f"{aspect_angle_deg:.0f}",
                orb=abs(final_offset),
                motion=motion_state.state,
                metadata=metadata,
            )


_DEFAULT_TRANSIT_ASPECTS: dict[str, tuple[float, str]] = {
    "conjunction": (0.0, "major"),
    "semisextile": (30.0, "minor"),
    "sextile": (60.0, "major"),
    "square": (90.0, "major"),
    "trine": (120.0, "major"),
    "quincunx": (150.0, "minor"),
    "opposition": (180.0, "major"),
}


def _parse_iso8601(ts: str) -> _dt.datetime:
    dt = _dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=_dt.UTC)
    return dt.astimezone(_dt.UTC)


def _body_name_map(names: Iterable[str] | None) -> dict[str, int]:
    if not names:
        return {name: int(code) for name, code in DEFAULT_BODIES.items()}
    lookup = {name.lower(): (name, int(code)) for name, code in DEFAULT_BODIES.items()}
    resolved: dict[str, int] = {}
    for candidate in names:
        key = str(candidate).lower()
        if key in lookup:
            canonical, code = lookup[key]
            resolved[canonical] = code
    return resolved


def _aspect_definitions(aspects: Iterable[object] | None) -> list[tuple[str, float, str]]:
    if not aspects:
        return [(name, angle, family) for name, (angle, family) in _DEFAULT_TRANSIT_ASPECTS.items()]

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
        return [(name, angle, family) for name, (angle, family) in _DEFAULT_TRANSIT_ASPECTS.items()]
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
    """Scan transit contacts against natal longitudes.

    Parameters
    ----------
    natal_ts, start_ts, end_ts:
        ISO-8601 timestamps in UTC describing the natal moment and scan window.
    aspects:
        Iterable of aspect descriptors. Strings reference the default aspect
        catalogue (conjunction, square, etc.) while numeric entries are treated
        as explicit angles in degrees.
    orb_deg:
        Maximum allowable deviation from the target aspect angle expressed in
        **degrees**. Events exceeding this offset are filtered from the result
        set even if the underlying engine refinement surfaced them.
    bodies:
        Iterable of moving bodies to consider. When omitted the default
        AstroEngine body set is used.
    targets:
        Iterable of natal bodies to compare against. Defaults to the moving
        body set.
    step_days:
        Coarse sampling cadence forwarded to
        :meth:`TransitEngine.scan_longitude_crossing` in **days**.
    """

    start_dt = _parse_iso8601(start_ts)
    end_dt = _parse_iso8601(end_ts)
    if end_dt <= start_dt:
        return []

    natal_dt = _parse_iso8601(natal_ts)
    adapter = SwissEphemerisAdapter.get_default_adapter()
    engine = TransitEngine.with_default_adapter()

    moving_map = _body_name_map(bodies)
    target_map = _body_name_map(targets) if targets is not None else dict(moving_map)
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
                events = engine.scan_longitude_crossing(
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
                    metadata = getattr(event, "metadata", None)
                    sample_meta = (
                        metadata.get("sample")
                        if isinstance(metadata, dict)
                        else None
                    )

                    moving_lon: float
                    moving_speed: float
                    if isinstance(sample_meta, dict) and sample_meta.get("longitude") is not None:
                        moving_lon = float(sample_meta["longitude"]) % 360.0
                        moving_speed = float(sample_meta.get("speed_longitude", 0.0))
                    else:
                        sample = engine.adapter.sample(moving_code, moment)
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
