from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

PositionProvider = Callable[[datetime], dict[str, float]]


@dataclass(slots=True)
class EventInterval:
    """Normalized event interval emitted by detectors."""

    kind: str
    start: datetime
    end: datetime
    meta: dict[str, Any]


@dataclass(slots=True)
class CombustCfg:
    """Configuration thresholds for combust / cazimi detection."""

    cazimi_deg: float = 0.2667
    combust_deg: float = 8.0
    under_beams_deg: float = 15.0


_ASPECT_ANGLES: dict[str, float] = {
    "conjunction": 0.0,
    "opposition": 180.0,
    "square": 90.0,
    "trine": 120.0,
    "sextile": 60.0,
    "quincunx": 150.0,
    "semisquare": 45.0,
    "sesquisquare": 135.0,
    "quintile": 72.0,
    "biquintile": 144.0,
}


def _norm360(value: float) -> float:
    return value % 360.0


def _angle_delta(value: float, target: float) -> float:
    diff = (value - target + 180.0) % 360.0 - 180.0
    return diff


def _angle_distance(value: float, target: float) -> float:
    return abs(_angle_delta(value, target))


def next_sign_ingress(
    body: str,
    start: datetime,
    provider: PositionProvider,
    *,
    step_minutes: int = 60,

    max_days: float = 45.0,
) -> datetime | None:
    """Return the timestamp when ``body`` enters the next zodiac sign.

    The detector samples the supplied ``provider`` on a regular cadence and
    linearly interpolates the crossing moment once the sign index advances.
    ``None`` is returned when no ingress occurs within ``max_days``.

    """

    if step_minutes <= 0:
        raise ValueError("step_minutes must be positive")


    positions = provider(start)
    lon = positions.get(body)
    if lon is None:
        raise KeyError(f"{body} position missing from provider output")

    start_lon = _norm360(float(lon))
    start_sign = int(start_lon // 30.0)
    target_boundary = (start_sign + 1) * 30.0
    # ensure we always look ahead to the next sign even if already on a cusp
    if target_boundary <= start_lon + 1e-9:
        target_boundary += 30.0

    end = start + timedelta(days=max_days)
    samples = _sample_range(start, end, step_minutes)

    prev_ts = start
    prev_lon_unwrapped = start_lon

    for ts in samples[1:]:
        positions = provider(ts)
        lon = positions.get(body)
        if lon is None:
            raise KeyError(f"{body} position missing from provider output")
        current_lon = _norm360(float(lon))
        delta = _angle_delta(current_lon, prev_lon_unwrapped % 360.0)
        curr_unwrapped = prev_lon_unwrapped + delta

        if curr_unwrapped == prev_lon_unwrapped:
            prev_ts = ts
            prev_lon_unwrapped = curr_unwrapped
            continue

        if target_boundary <= curr_unwrapped:
            span = (ts - prev_ts).total_seconds()
            if span <= 0:
                return ts
            frac = (target_boundary - prev_lon_unwrapped) / (
                curr_unwrapped - prev_lon_unwrapped
            )
            frac = max(0.0, min(1.0, frac))
            return prev_ts + timedelta(seconds=frac * span)

        prev_ts = ts
        prev_lon_unwrapped = curr_unwrapped


    return None


def _sample_range(window_start: datetime, window_end: datetime, step_minutes: int) -> Sequence[datetime]:
    if step_minutes <= 0:
        raise ValueError("step_minutes must be positive")
    delta = timedelta(minutes=step_minutes)
    samples: list[datetime] = [window_start]
    cursor = window_start
    while cursor < window_end:
        next_cursor = cursor + delta
        if next_cursor >= window_end:
            if samples[-1] != window_end:
                samples.append(window_end)
            break
        samples.append(next_cursor)
        cursor = next_cursor
    if samples[-1] != window_end:
        samples.append(window_end)
    return samples


def next_sign_ingress(
    body: str,
    start: datetime,
    provider: PositionProvider,
    *,
    step_minutes: int = 60,
    max_days: float = 45.0,
) -> datetime | None:
    """Return the next UTC instant when ``body`` enters a new zodiac sign."""

    window_end = start + timedelta(days=max_days)
    samples = _sample_range(start, window_end, step_minutes)

    if not samples:
        return None

    prev_ts = samples[0]
    prev_lon = provider(prev_ts).get(body)
    if prev_lon is None:
        raise KeyError(f"{body} position missing from provider output")
    prev_norm = _norm360(prev_lon)
    prev_sign = int(prev_norm // 30.0)

    for ts in samples[1:]:
        curr_lon = provider(ts).get(body)
        if curr_lon is None:
            raise KeyError(f"{body} position missing from provider output")
        curr_norm = _norm360(curr_lon)
        curr_sign = int(curr_norm // 30.0)

        if curr_sign != prev_sign:
            boundary_sign = (prev_sign + 1) % 12
            boundary_deg = boundary_sign * 30.0

            adj_prev = prev_norm
            adj_curr = curr_norm
            if boundary_deg < adj_prev:
                boundary_deg += 360.0
            if adj_curr < adj_prev:
                adj_curr += 360.0

            span_seconds = (ts - prev_ts).total_seconds()
            if span_seconds <= 0 or adj_curr == adj_prev:
                return ts

            alpha = (boundary_deg - adj_prev) / (adj_curr - adj_prev)
            alpha = max(0.0, min(1.0, alpha))
            return prev_ts + timedelta(seconds=alpha * span_seconds)

        prev_ts = ts
        prev_norm = curr_norm
        prev_sign = curr_sign

    return None


def detect_voc_moon(
    window: Any,
    provider: PositionProvider,
    aspects: Iterable[str],
    policy: dict[str, Any] | None = None,
    other_objects: Iterable[str] = (),
    *,
    step_minutes: int = 60,
) -> list[EventInterval]:
    """Detect intervals where the Moon forms no aspects to the selected objects."""

    start = window.start
    ingress_limit = next_sign_ingress("Moon", start, provider, step_minutes=step_minutes)
    end = window.end
    if ingress_limit is not None and ingress_limit < end:
        end = ingress_limit
    samples = _sample_range(start, end, step_minutes)


    orb_policy = policy or {}
    per_aspect = orb_policy.get("per_aspect", {}) if orb_policy else {}
    default_orb = float(orb_policy.get("default", 3.0)) if orb_policy else 3.0

    aspect_list = [name for name in aspects if name in _ASPECT_ANGLES]
    other_targets = list(other_objects or [])

    def _is_void(ts: datetime) -> bool:
        positions = provider(ts)
        moon_lon = positions.get("Moon")
        if moon_lon is None:
            raise KeyError("Moon position missing from provider output")
        for obj in other_targets:
            other_lon = positions.get(obj)
            if other_lon is None:
                continue
            separation = _norm360(moon_lon - other_lon)
            for aspect_name in aspect_list:
                target = _ASPECT_ANGLES[aspect_name]
                orb = float(per_aspect.get(aspect_name, default_orb))
                if _angle_distance(separation, target) <= orb:
                    return False
        return True

    states = [_is_void(ts) for ts in samples]

    intervals: list[EventInterval] = []
    current_start: datetime | None = None
    current_ingress: datetime | None = None
    for idx, ts in enumerate(samples):
        state = states[idx]
        if state and current_start is None:
            current_start = ts
            remaining_days = max(0.0, (end - ts).total_seconds() / 86400.0)
            current_ingress = next_sign_ingress(
                "Moon",
                ts,
                provider,
                step_minutes=step_minutes,
                max_days=remaining_days + 2.0,
            )
        if (not state or idx == len(samples) - 1) and current_start is not None:

            if not state:
                end_ts = ts
            else:
                end_ts = samples[-1]
                if current_ingress is not None and current_ingress <= end_ts:
                    end_ts = current_ingress

            intervals.append(
                EventInterval(
                    kind="voc_moon",
                    start=current_start,
                    end=end_ts,
                    meta={"step_minutes": step_minutes},
                )
            )
            current_start = None
            current_ingress = None

    return intervals


def detect_combust_cazimi(
    window: Any,
    provider: PositionProvider,
    *,
    planet: str,
    cfg: CombustCfg | None = None,
    step_minutes: int = 10,
) -> list[EventInterval]:
    """Detect cazimi / combust / under-beams intervals for a planet relative to the Sun."""

    if cfg is None:
        cfg = CombustCfg()

    start = window.start
    end = window.end
    samples = _sample_range(start, end, step_minutes)

    def _state(ts: datetime) -> str | None:
        positions = provider(ts)
        sun = positions.get("Sun")
        body = positions.get(planet)
        if sun is None or body is None:
            raise KeyError("Sun or planet position missing from provider output")
        separation = abs(_angle_delta(_norm360(body) - _norm360(sun), 0.0))
        if separation <= cfg.cazimi_deg:
            return "cazimi"
        if separation <= cfg.combust_deg:
            return "combust"
        if separation <= cfg.under_beams_deg:
            return "under_beams"
        return None

    states = [_state(ts) for ts in samples]

    intervals: list[EventInterval] = []
    current_kind: str | None = None
    current_start: datetime | None = None

    for idx, ts in enumerate(samples):
        state = states[idx]
        if state != current_kind:
            if current_kind is not None and current_start is not None:
                intervals.append(
                    EventInterval(
                        kind=current_kind,
                        start=current_start,
                        end=ts,
                        meta={"planet": planet},
                    )
                )
            current_kind = state
            current_start = ts if state is not None else None
        if idx == len(samples) - 1 and current_kind is not None and current_start is not None:
            intervals.append(
                EventInterval(
                    kind=current_kind,
                    start=current_start,
                    end=ts,
                    meta={"planet": planet},
                )
            )
            current_kind = None
            current_start = None

    return intervals


def detect_returns(
    window: Any,
    provider: PositionProvider,
    *,
    body: str,
    target_lon: float,
    step_minutes: int = 720,
    tol_seconds: float = 60.0,
) -> list[EventInterval]:
    """Detect point events when a body returns to ``target_lon`` within ``window``."""

    start = window.start
    end = window.end
    samples = _sample_range(start, end, step_minutes)

    events: list[EventInterval] = []
    prev_ts: datetime | None = None
    prev_diff: float | None = None

    def _record_event(moment: datetime, *, include_orb: bool) -> None:
        if events and abs((moment - events[-1].start).total_seconds()) <= tol_seconds:
            return
        meta: dict[str, Any] = {"body": body, "target_lon": float(target_lon)}
        if include_orb:
            meta["orb"] = 0.0
        events.append(
            EventInterval(
                kind="return",
                start=moment,
                end=moment,
                meta=meta,
            )
        )

    for ts in samples:
        positions = provider(ts)
        lon = positions.get(body)
        if lon is None:
            raise KeyError(f"{body} position missing from provider output")
        diff = _angle_delta(_norm360(lon), _norm360(target_lon))
        if abs(diff) < 1e-6:
            _record_event(ts, include_orb=True)
        elif prev_diff is not None and prev_ts is not None:
            if (prev_diff <= 0.0 < diff) or (prev_diff >= 0.0 > diff):
                span = (ts - prev_ts).total_seconds()
                if span == 0:
                    exact = ts
                else:
                    alpha = prev_diff / (prev_diff - diff)
                    alpha = max(0.0, min(1.0, alpha))
                    exact = prev_ts + timedelta(seconds=alpha * span)
                _record_event(exact, include_orb=False)
        prev_ts = ts
        prev_diff = diff

    return events


__all__ = [
    "CombustCfg",
    "EventInterval",
    "next_sign_ingress",
    "detect_voc_moon",
    "detect_combust_cazimi",
    "detect_returns",
]
