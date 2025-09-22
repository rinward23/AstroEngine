"""Transit scanning utilities built on top of the ephemeris adapter."""

from __future__ import annotations

import datetime as _dt
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from ..ephemeris import EphemerisAdapter, EphemerisConfig, EphemerisSample
from ..ephemeris.refinement import RefinementBracket, refine_event
from .angles import classify_relative_motion, signed_delta
from .api import TransitEvent as LegacyTransitEvent

# >>> AUTO-GEN BEGIN: Canonical Scan Adapter v1.0
from typing import Iterable as _TypingIterable, Any as _TypingAny

try:
    from ..canonical import TransitEvent, events_from_any
except Exception:  # pragma: no cover
    TransitEvent = object  # type: ignore

    def events_from_any(x):
        return list(x)  # type: ignore


def to_canonical_events(events: _TypingIterable[_TypingAny]) -> _TypingIterable[TransitEvent]:
    """Normalize engine or legacy events to :class:`~astroengine.canonical.TransitEvent`."""

    return events_from_any(events)


# >>> AUTO-GEN END: Canonical Scan Adapter v1.0

__all__ = ["TransitEngine"]


@dataclass
class TransitEngine:
    """Lightweight transit scanning orchestrator."""

    adapter: EphemerisAdapter

    @classmethod
    def with_default_adapter(cls, config: EphemerisConfig | None = None) -> TransitEngine:
        return cls(adapter=EphemerisAdapter(config))

    def compute_positions(
        self,
        bodies: Sequence[int],
        moment: _dt.datetime,
    ) -> dict[int, float]:
        return {body: self.adapter.sample(body, moment).longitude for body in bodies}

    def scan_longitude_crossing(
        self,
        body: int,
        reference_longitude: float,
        aspect_angle_deg: float,
        start: _dt.datetime,
        end: _dt.datetime,
        *,
        step_hours: float = 6.0,
    ) -> Iterable[LegacyTransitEvent]:
        current = start
        previous_sample = self.adapter.sample(body, current)
        previous_offset = (
            signed_delta(previous_sample.longitude - reference_longitude) - aspect_angle_deg
        )

        while current <= end:
            current += _dt.timedelta(hours=step_hours)
            if current > end:
                break

            sample = self.adapter.sample(body, current)
            offset = signed_delta(sample.longitude - reference_longitude) - aspect_angle_deg

            if previous_offset == 0.0:
                previous_offset = -1e-9

            if previous_offset * offset <= 0.0:
                bracket = RefinementBracket(
                    body=body,
                    start=current - _dt.timedelta(hours=step_hours),
                    end=current,
                    start_sample=previous_sample,
                    end_sample=sample,
                    start_offset=previous_offset,
                    end_offset=offset,
                )

                def offset_fn(candidate: EphemerisSample) -> float:
                    return (
                        signed_delta(candidate.longitude - reference_longitude) - aspect_angle_deg
                    )

                try:
                    timestamp, refined_sample = refine_event(
                        self.adapter,
                        bracket,
                        offset_fn,
                    )
                    final_offset = offset_fn(refined_sample)
                except Exception:
                    timestamp = current
                    refined_sample = sample
                    final_offset = offset

                final_separation = aspect_angle_deg + final_offset
                motion_state = classify_relative_motion(
                    final_separation,
                    aspect_angle_deg,
                    refined_sample.speed_longitude,
                    0.0,
                )

                event = LegacyTransitEvent(
                    timestamp=timestamp,
                    body=str(body),
                    target="natal",  # placeholder until natal metadata wired in
                    aspect=f"{aspect_angle_deg:.0f}",
                    orb=abs(final_offset),
                    motion=motion_state.state,
                )
                yield event

            previous_sample = sample
            previous_offset = offset
