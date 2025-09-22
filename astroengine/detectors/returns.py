"""Solar and lunar return detection using Swiss longitudes."""

from __future__ import annotations

from typing import Callable

from ..events import ReturnEvent
from .common import delta_deg, jd_to_iso, moon_lon, solve_zero_crossing, sun_lon

__all__ = ["solar_lunar_returns"]


def _body_accessor(kind: str) -> tuple[str, Callable[[float], float]]:
    key = kind.lower()
    if key == "solar":
        return "Sun", sun_lon
    if key == "lunar":
        return "Moon", moon_lon
    raise ValueError(f"Unsupported return kind '{kind}'")


def solar_lunar_returns(
    natal_jd: float,
    start_jd: float,
    end_jd: float,
    kind: str = "solar",
    *,
    step_days: float | None = None,
) -> list[ReturnEvent]:
    """Return solar or lunar return events within a Julian day window."""

    if end_jd <= start_jd:
        return []

    body_name, accessor = _body_accessor(kind)
    target_lon = accessor(natal_jd) % 360.0
    step = step_days if step_days is not None else (1.0 if body_name == "Sun" else 0.5)

    events: list[ReturnEvent] = []
    seen: set[int] = set()

    prev_jd = start_jd
    prev_delta = delta_deg(accessor(prev_jd), target_lon)
    current = start_jd + step
    while current <= end_jd + step:
        curr_delta = delta_deg(accessor(current), target_lon)
        if prev_delta == 0.0:
            root = prev_jd
        elif prev_delta * curr_delta <= 0.0:
            try:
                root = solve_zero_crossing(
                    lambda x, fn=accessor, tgt=target_lon: delta_deg(fn(x), tgt),
                    prev_jd,
                    min(current, end_jd),
                    tol=1e-5,
                    tol_deg=1e-4,
                )
            except ValueError:
                prev_jd, prev_delta = current, curr_delta
                current += step
                continue
        else:
            prev_jd, prev_delta = current, curr_delta
            current += step
            continue

        key = int(round(root * 86400))
        if key not in seen and start_jd <= root <= end_jd:
            longitude = accessor(root) % 360.0
            events.append(
                ReturnEvent(
                    ts=jd_to_iso(root),
                    jd=root,
                    body=body_name,
                    method=kind.lower(),
                    longitude=longitude,
                )
            )
            seen.add(key)

        prev_jd, prev_delta = current, curr_delta
        current += step

    events.sort(key=lambda event: event.jd)
    return events
