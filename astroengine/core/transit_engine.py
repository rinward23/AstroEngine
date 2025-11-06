"""Transit scanning utilities built on top of the ephemeris adapter."""

# isort: skip_file

from __future__ import annotations

import datetime as _dt
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from ..detectors_aspects import AspectHit
from ..ephemeris import EphemerisAdapter, EphemerisConfig
from ..ephemeris.swisseph_adapter import SwissEphemerisAdapter, VariantConfig
from ..transits.engine import (
    TransitEngineConfig,
    TransitScanEvent,
    TransitScanService,
    _aspect_definitions,
    scan_transits as _scan_transits_impl,
    to_canonical_events,
)

from .api import TransitEvent as LegacyTransitEvent

__all__ = ["TransitEngine", "TransitEngineConfig", "scan_transits", "_aspect_definitions"]


@dataclass
class TransitEngine:
    """Compatibility wrapper over :class:`~astroengine.transits.engine.TransitScanService`."""

    adapter: EphemerisAdapter
    config: TransitEngineConfig = field(default_factory=TransitEngineConfig)

    def __post_init__(self) -> None:
        self._service = TransitScanService(self.adapter, self.config)

    @classmethod
    def with_default_adapter(
        cls,
        config: EphemerisConfig | None = None,
        *,
        engine_config: TransitEngineConfig | None = None,
    ) -> "TransitEngine":
        return cls(
            adapter=EphemerisAdapter(config),
            config=engine_config or TransitEngineConfig(),
        )

    def compute_positions(
        self,
        bodies: Sequence[int],
        moment: _dt.datetime,
    ) -> dict[int, float]:
        """Proxy to :meth:`TransitScanService.compute_positions`."""

        return dict(self._service.compute_positions(bodies, moment))

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
        """Yield legacy events built from the consolidated transit scan service."""

        events: Iterable[TransitScanEvent]
        events = self._service.iter_longitude_crossings(
            body,
            reference_longitude,
            aspect_angle_deg,
            start,
            end,
            step_hours=step_hours,
            refinement=refinement,
        )
        for event in events:
            metadata = dict(event.metadata)
            yield LegacyTransitEvent(
                timestamp=event.timestamp,
                body=str(event.body),
                target="natal",
                aspect=f"{event.aspect_angle_deg:.0f}",
                orb=abs(event.offset_deg),
                motion=event.motion,
                metadata=metadata,
            )


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
    """Delegated entry point preserved for backward compatibility."""

    return _scan_transits_impl(
        natal_ts,
        start_ts,
        end_ts,
        aspects=aspects,
        orb_deg=orb_deg,
        bodies=bodies,
        targets=targets,
        step_days=step_days,
    )
