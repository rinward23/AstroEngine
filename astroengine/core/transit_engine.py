"""Transit scanning utilities built on top of the ephemeris adapter."""

from __future__ import annotations

import datetime as _dt

# >>> AUTO-GEN BEGIN: Canonical Scan Adapter v1.0
from collections.abc import Iterable, Sequence
from collections.abc import Iterable as _TypingIterable
from dataclasses import dataclass, field
from typing import Any as _TypingAny
from typing import Literal

from ..ephemeris import EphemerisAdapter, EphemerisConfig, EphemerisSample
from ..ephemeris.refinement import RefinementBracket, refine_event
from .angles import classify_relative_motion, signed_delta
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

        coarse_times: list[_dt.datetime] = [start]
        if start != end:
            current = start
            while current < end:
                next_tick = current + coarse_step
                if next_tick <= current:
                    raise ValueError("step_hours too small to advance timeline")
                if next_tick >= end:
                    coarse_times.append(end)
                    break
                coarse_times.append(next_tick)
                current = next_tick
        samples = [sample(moment) for moment in coarse_times]
        offsets = [compute_offset(item) for item in samples]

        for idx in range(1, len(coarse_times)):
            start_time = coarse_times[idx - 1]
            end_time = coarse_times[idx]
            start_sample = samples[idx - 1]
            end_sample = samples[idx]
            start_offset = offsets[idx - 1]
            end_offset = offsets[idx]

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
            final_time, final_sample, final_offset = min(
                coarse_candidates,
                key=lambda entry: (abs(entry[2]), entry[0]),
            )

            if settings.enabled and not retro_loop and start_time != end_time:
                bracket = RefinementBracket(
                    body=body,
                    start=start_time,
                    end=end_time,
                    start_sample=start_sample,
                    end_sample=end_sample,
                    start_offset=start_offset,
                    end_offset=end_offset,
                )
                try:
                    timestamp, refined_sample = refine_event(
                        self.adapter,
                        bracket,
                        compute_offset,
                        max_iterations=settings.max_iterations,
                        min_step_seconds=settings.min_step_seconds,
                    )
                except Exception:
                    timestamp = final_time
                    refined_sample = final_sample
                else:
                    final_time = timestamp
                    final_sample = refined_sample
                finally:
                    final_offset = compute_offset(final_sample)

            final_separation = aspect_angle_deg + final_offset
            motion_state = classify_relative_motion(
                final_separation,
                aspect_angle_deg,
                final_sample.speed_longitude,
                0.0,
            )

            yield LegacyTransitEvent(
                timestamp=final_time,
                body=str(body),
                target="natal",  # placeholder until natal metadata wired in
                aspect=f"{aspect_angle_deg:.0f}",
                orb=abs(final_offset),
                motion=motion_state.state,
            )
