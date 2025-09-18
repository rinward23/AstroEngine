"""Public API for transit scanning."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Sequence, cast

from .detectors import detect_ecliptic_contacts
from .profiles import OrbPolicy, SeverityModel
from .refine import refine_exact


@dataclass(frozen=True)
class TransitScanConfig:
    """Configuration payload for a scan request."""

    start: datetime
    end: datetime
    step: timedelta
    aspects: Sequence[str]
    natal_point: str
    natal_lon: float

    def ticks(self) -> List[datetime]:
        """Generate UTC timestamps for the configured window."""

        ticks: List[datetime] = []
        current = self.start
        while current <= self.end:
            ticks.append(current)
            current += self.step
        return ticks


@dataclass
class TransitEvent:
    """Represents a detected transit contact."""

    timestamp: datetime
    aspect: str
    transiting_body: str
    natal_point: str
    orb_deg: float
    family: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def copy_with(self, **updates: Any) -> "TransitEvent":
        payload = dict(self.metadata)
        if "metadata" in updates:
            payload = dict(updates.pop("metadata"))
        result = replace(self, **updates)
        result.metadata = payload
        return result


class TransitEngine:
    """Utility that orchestrates transit detection and scoring."""

    def __init__(
        self,
        provider: Any,
        orb_policy: OrbPolicy | None = None,
        severity_model: SeverityModel | None = None,
    ) -> None:
        self.provider = provider
        self.orb_policy = orb_policy or OrbPolicy()
        self.severity_model = severity_model or SeverityModel()

    def scan(self, config: TransitScanConfig) -> List[TransitEvent]:
        """Run a scan returning scored transit events."""

        natal: Dict[str, float | str] = {
            "name": config.natal_point,
            "lon_deg": float(config.natal_lon),
        }
        results: List[TransitEvent] = []
        for tick in config.ticks():
            state = self._state_for_tick(tick)
            events = detect_ecliptic_contacts(
                state,
                natal,
                list(config.aspects),
                self.orb_policy,
            )
            for event in events:
                t_exact = refine_exact(self.provider, event, natal)
                state_exact = self._state_for_tick(t_exact)
                refined = self._with_orb(event, state_exact, natal)
                severity = self.severity_model.score_event(refined, self.orb_policy)
                refined.metadata["severity"] = severity
                results.append(refined)
        return results

    def _state_for_tick(self, tick: datetime) -> Dict[str, Any]:
        iso_ts = tick.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        raw_state = self.provider.ecliptic_state(iso_ts)
        state: Dict[str, Any] = dict(raw_state)
        state["__timestamp__"] = tick
        return state

    def _with_orb(
        self,
        event: TransitEvent,
        state: Mapping[str, Any],
        natal: Mapping[str, float | str],
    ) -> TransitEvent:
        from .detectors import compute_orb

        payload = cast(Mapping[str, float], state[event.transiting_body])
        timestamp = cast(datetime, state["__timestamp__"])
        natal_lon = cast(float, natal["lon_deg"])
        lon = float(payload["lon_deg"])
        orb = abs(compute_orb(lon, natal_lon, event.aspect))
        return event.copy_with(timestamp=timestamp, orb_deg=orb)


__all__ = ["TransitEngine", "TransitEvent", "TransitScanConfig"]
