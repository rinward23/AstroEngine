"""Outer-planet timeline helpers backed by the Swiss ephemeris."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from itertools import combinations

from astroengine.detectors.common import norm360
from astroengine.ephemeris import SwissEphemerisAdapter
from astroengine.timeline import TransitWindow, window_envelope

try:  # pragma: no cover - pyswisseph guard
    from astroengine.ephemeris.swe import swe
except Exception:  # pragma: no cover - exercised when ephemeris missing
    swe = None  # type: ignore[assignment]

__all__ = ["OuterCycleEvent", "outer_cycle_events", "outer_cycle_windows"]

_DEFAULT_BODIES: tuple[str, ...] = ("jupiter", "saturn", "uranus", "neptune", "pluto")
_DEFAULT_ASPECTS: Mapping[float, str] = {
    0.0: "conjunction",
    60.0: "sextile",
    90.0: "square",
    120.0: "trine",
    180.0: "opposition",
}


@dataclass(frozen=True)
class OuterCycleEvent:
    """Moment where two outer bodies perfect an aspect."""

    timestamp: datetime
    bodies: tuple[str, str]
    aspect_deg: float
    aspect_label: str
    orb_deg: float
    longitude_a: float
    longitude_b: float
    speed_a: float
    speed_b: float
    metadata: Mapping[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp.astimezone(UTC)
            .isoformat()
            .replace("+00:00", "Z"),
            "bodies": list(self.bodies),
            "aspect_deg": self.aspect_deg,
            "aspect_label": self.aspect_label,
            "orb_deg": self.orb_deg,
            "longitude_a": self.longitude_a,
            "longitude_b": self.longitude_b,
            "speed_a": self.speed_a,
            "speed_b": self.speed_b,
            "metadata": dict(self.metadata),
        }


def _require_swisseph() -> None:
    if swe is None:  # pragma: no cover - dependency guard
        raise RuntimeError(
            "Outer cycle timelines require pyswisseph. Install AstroEngine with "
            "the 'mundane' extra to compute planetary cycles."
        )


def _resolve_body_code(body: str) -> int:
    key = body.lower()
    if not hasattr(swe, key.upper()):
        raise KeyError(f"Unsupported body for outer cycle timelines: {body}")
    return int(getattr(swe, key.upper()))


def _moment_to_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def _angular_gap(lon_a: float, lon_b: float, aspect: float) -> float:
    difference = norm360(lon_a - lon_b)
    target = norm360(aspect)
    gap = difference - target
    if gap > 180.0:
        gap -= 360.0
    elif gap < -180.0:
        gap += 360.0
    return gap


def _refine_event(
    adapter: SwissEphemerisAdapter,
    start: datetime,
    end: datetime,
    *,
    codes: Mapping[str, int],
    bodies: tuple[str, str],
    aspect: float,
    max_iter: int = 12,
) -> tuple[datetime, float]:
    low = _moment_to_utc(start)
    high = _moment_to_utc(end)
    pair_codes = {name: codes[name] for name in bodies}
    for _ in range(max_iter):
        mid = low + (high - low) / 2
        jd_mid = adapter.julian_day(mid)
        mid_positions = adapter.compute_bodies_many(jd_mid, pair_codes)
        lon_a = mid_positions[bodies[0]].longitude
        lon_b = mid_positions[bodies[1]].longitude
        gap = _angular_gap(lon_a, lon_b, aspect)
        if abs(gap) < 1e-3:
            return mid, gap
        jd_low = adapter.julian_day(low)
        low_positions = adapter.compute_bodies_many(jd_low, pair_codes)
        lon_a_low = low_positions[bodies[0]].longitude
        lon_b_low = low_positions[bodies[1]].longitude
        gap_low = _angular_gap(lon_a_low, lon_b_low, aspect)
        if gap_low * gap <= 0:
            high = mid
        else:
            low = mid
    return mid, gap


def outer_cycle_events(
    start: datetime,
    end: datetime,
    *,
    bodies: Sequence[str] | None = None,
    aspects: Mapping[float, str] | None = None,
    adapter: SwissEphemerisAdapter | None = None,
    step_days: float = 1.0,
) -> list[OuterCycleEvent]:
    """Return perfected outer-planet aspects within ``start``/``end``."""

    _require_swisseph()

    start_utc = _moment_to_utc(start)
    end_utc = _moment_to_utc(end)
    if end_utc <= start_utc:
        raise ValueError("end must be after start for outer cycle timelines")

    adapter = adapter or SwissEphemerisAdapter.get_default_adapter()
    bodies = tuple(bodies) if bodies is not None else _DEFAULT_BODIES
    aspects = aspects or dict(_DEFAULT_ASPECTS)

    codes = {body: _resolve_body_code(body) for body in bodies}

    events: list[OuterCycleEvent] = []
    current = start_utc
    step = timedelta(days=step_days)

    prev: dict[tuple[tuple[str, str], float], tuple[datetime, float]] = {}
    while current <= end_utc:
        jd = adapter.julian_day(current)
        positions = adapter.compute_bodies_many(jd, codes)
        longitudes = {body: positions[body].longitude for body in bodies}
        speeds = {body: positions[body].speed_longitude for body in bodies}

        for a, b in combinations(bodies, 2):
            for aspect_deg, label in aspects.items():
                gap = _angular_gap(longitudes[a], longitudes[b], aspect_deg)
                key = ((a, b), aspect_deg)
                previous = prev.get(key)
                if previous is not None:
                    prev_time, prev_gap = previous
                    if gap == 0.0 or prev_gap == 0.0 or gap * prev_gap <= 0:
                        refined_time, refined_gap = _refine_event(
                            adapter,
                            prev_time,
                            current,
                            codes=codes,
                            bodies=(a, b),
                            aspect=aspect_deg,
                        )
                        jd_event = adapter.julian_day(refined_time)
                        pair_positions = adapter.compute_bodies_many(
                            jd_event, {name: codes[name] for name in (a, b)}
                        )
                        pos_a = pair_positions[a]
                        pos_b = pair_positions[b]
                        events.append(
                            OuterCycleEvent(
                                timestamp=refined_time,
                                bodies=(a, b),
                                aspect_deg=aspect_deg,
                                aspect_label=label,
                                orb_deg=abs(
                                    _angular_gap(
                                        pos_a.longitude, pos_b.longitude, aspect_deg
                                    )
                                ),
                                longitude_a=pos_a.longitude,
                                longitude_b=pos_b.longitude,
                                speed_a=pos_a.speed_longitude,
                                speed_b=pos_b.speed_longitude,
                                metadata={"step_days": step_days},
                            )
                        )
                prev[key] = (current, gap)
        current += step

    events.sort(key=lambda event: event.timestamp)
    return events


def outer_cycle_windows(
    start: datetime,
    end: datetime,
    *,
    bodies: Sequence[str] | None = None,
    aspects: Mapping[float, str] | None = None,
    adapter: SwissEphemerisAdapter | None = None,
    step_days: float = 1.0,
    orb_allow: float = 1.0,
) -> list[TransitWindow]:
    """Return transit windows around perfected outer-planet aspects."""

    events = outer_cycle_events(
        start,
        end,
        bodies=bodies,
        aspects=aspects,
        adapter=adapter,
        step_days=step_days,
    )
    windows: list[TransitWindow] = []
    for event in events:
        speed_delta = abs(event.speed_a - event.speed_b)
        speed_delta = max(speed_delta, 1e-3)
        hours_per_degree = 24.0 / speed_delta
        width_deg = min(
            5.0, max(orb_allow, orb_allow * (1.5 if speed_delta < 0.5 else 1.0))
        )
        window = window_envelope(
            event.timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            width_deg,
            hours_per_degree=hours_per_degree,
            metadata={
                "aspect": event.aspect_label,
                "aspect_deg": event.aspect_deg,
                "bodies": list(event.bodies),
                "orb_allow": orb_allow,
                "speed_delta": speed_delta,
            },
        )
        windows.append(window)
    return windows
