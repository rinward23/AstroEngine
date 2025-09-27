from __future__ import annotations


from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Iterable, List, Sequence

PositionProvider = Callable[[datetime], Dict[str, float]]


@dataclass(slots=True)
class EventInterval:
    """Normalized event interval emitted by detectors."""

    kind: str
    start: datetime
    end: datetime
    meta: Dict[str, Any]


@dataclass(slots=True)
class CombustCfg:
    """Configuration thresholds for combust / cazimi detection."""

    cazimi_deg: float = 0.2667
    combust_deg: float = 8.0
    under_beams_deg: float = 15.0


_ASPECT_ANGLES: Dict[str, float] = {
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
    max_days: float = 60.0,
) -> datetime | None:
    """Return the timestamp when a body enters the next zodiac sign.

    The calculation samples ephemeris positions using ``provider`` and
    refines the crossing by bisecting the final interval to minute-level
    precision. If the body fails to change signs within ``max_days`` the
    function returns ``None``.
    """

    if step_minutes <= 0:
        raise ValueError("step_minutes must be positive")

    start_positions = provider(start)
    if body not in start_positions:
        raise KeyError(f"{body!r} not provided by ephemeris")

    start_lon = _norm360(start_positions[body])
    start_sign = int(start_lon // 30.0)
    window_end = start + timedelta(days=max_days)
    samples = _sample_range(start, window_end, step_minutes)

    prev_ts = samples[0]
    prev_lon = start_lon
    prev_sign = start_sign
    for ts in samples[1:]:
        positions = provider(ts)
        lon_raw = positions.get(body)
        if lon_raw is None:
            raise KeyError(f"{body!r} not provided by ephemeris")
        lon = _norm360(lon_raw)
        delta = _angle_delta(lon, prev_lon)
        if delta == 0.0:
            prev_ts, prev_lon = ts, lon
            continue

        direction = 1 if delta > 0 else -1
        current_sign = int(lon // 30.0)
        if current_sign != prev_sign:
            boundary_sign = (prev_sign + direction) % 12 if direction > 0 else prev_sign % 12
            boundary_deg = boundary_sign * 30.0

            # Ensure offsets straddle the boundary before bisecting.
            start_offset = _angle_delta(prev_lon, boundary_deg)
            end_offset = _angle_delta(lon, boundary_deg)
            if start_offset == 0.0:
                return prev_ts
            if end_offset == 0.0:
                return ts

            if start_offset > 0 and end_offset > 0:
                # Adjust boundary if wrap-around mis-detected.
                boundary_deg = prev_sign * 30.0
                start_offset = _angle_delta(prev_lon, boundary_deg)
                end_offset = _angle_delta(lon, boundary_deg)

            lower_ts, upper_ts = (prev_ts, ts)
            lower_offset, upper_offset = start_offset, end_offset

            for _ in range(16):
                mid = lower_ts + (upper_ts - lower_ts) / 2
                if (upper_ts - lower_ts).total_seconds() <= 60:
                    return mid
                mid_lon = _norm360(provider(mid)[body])
                mid_offset = _angle_delta(mid_lon, boundary_deg)
                if mid_offset == 0.0:
                    return mid
                if (mid_offset > 0 and lower_offset > 0) or (mid_offset < 0 and lower_offset < 0):
                    lower_ts, lower_offset = mid, mid_offset
                else:
                    upper_ts, upper_offset = mid, mid_offset

            return lower_ts if abs(lower_offset) < abs(upper_offset) else upper_ts

        prev_ts, prev_lon, prev_sign = ts, lon, current_sign

    return None


def _sample_range(window_start: datetime, window_end: datetime, step_minutes: int) -> Sequence[datetime]:
    if step_minutes <= 0:
        raise ValueError("step_minutes must be positive")
    delta = timedelta(minutes=step_minutes)
    samples: List[datetime] = [window_start]
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


def detect_voc_moon(
    window: Any,
    provider: PositionProvider,
    aspects: Iterable[str],
    orb_policy: Dict[str, Any] | None = None,
    other_objects: Iterable[str] | None = None,
    *,
    step_minutes: int = 60,
    policy: Dict[str, Any] | None = None,
) -> List[EventInterval]:
    """Detect intervals where the Moon forms no aspects to the selected objects."""

    start = window.start
    end = window.end
    samples = _sample_range(start, end, step_minutes)

    ingress_limit = None
    try:
        ingress_limit = next_sign_ingress("Moon", start, provider, step_minutes=step_minutes)
        if ingress_limit is not None and ingress_limit < start:
            ingress_limit = None
    except Exception:
        ingress_limit = None

    policy_data = orb_policy if orb_policy is not None else policy
    per_aspect = policy_data.get("per_aspect", {}) if policy_data else {}
    default_orb = float(policy_data.get("default", 3.0)) if policy_data else 3.0
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

    intervals: List[EventInterval] = []
    current_start: datetime | None = None
    for idx, ts in enumerate(samples):
        state = states[idx]
        if state and current_start is None:
            current_start = ts
        if (not state or idx == len(samples) - 1) and current_start is not None:
            end_ts = ts if not state else samples[-1]
            if ingress_limit is not None and ingress_limit < end_ts:
                end_ts = ingress_limit
            intervals.append(
                EventInterval(
                    kind="voc_moon",
                    start=current_start,
                    end=end_ts,
                    meta={"step_minutes": step_minutes},
                )
            )
            current_start = None

    return intervals


def detect_combust_cazimi(
    window: Any,
    provider: PositionProvider,
    *,
    planet: str,
    cfg: CombustCfg | None = None,
    step_minutes: int = 10,
) -> List[EventInterval]:
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

    intervals: List[EventInterval] = []
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
) -> List[EventInterval]:
    """Detect point events when a body returns to ``target_lon`` within ``window``."""

    start = window.start
    end = window.end
    samples = _sample_range(start, end, step_minutes)

    events: List[EventInterval] = []
    prev_ts: datetime | None = None
    prev_diff: float | None = None

    def _record_event(moment: datetime, *, include_orb: bool) -> None:
        if events and abs((moment - events[-1].start).total_seconds()) <= tol_seconds:
            return
        meta: Dict[str, Any] = {"body": body, "target_lon": float(target_lon)}
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
    "detect_voc_moon",
    "detect_combust_cazimi",
    "detect_returns",
]

