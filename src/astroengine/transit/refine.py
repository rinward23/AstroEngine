"""Refinement helpers for contact events."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Mapping, cast

from .detectors import compute_orb

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

if TYPE_CHECKING:
    from .api import TransitEvent


def _to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime(ISO_FORMAT)


def refine_exact(
    provider: Any,
    event: TransitEvent,
    natal: Mapping[str, float | str],
    max_iter: int = 8,
    tolerance: float = 1e-3,
) -> datetime:
    """Refine the timestamp of an event using Newton-style iteration."""

    guess = event.timestamp
    for _ in range(max_iter):
        state = provider.ecliptic_state(_to_iso(guess))
        body_state = state[event.transiting_body]
        lon = float(body_state["lon_deg"])
        speed = float(body_state.get("lon_speed_deg_per_day", 0.0))
        natal_lon = cast(float, natal["lon_deg"])
        diff = compute_orb(lon, natal_lon, event.aspect)
        if abs(diff) <= tolerance:
            break
        if abs(speed) < 1e-6:
            break
        delta_days = -diff / speed
        guess += timedelta(days=delta_days)
    return guess


__all__ = ["refine_exact"]
