"""Overlay construction utilities."""

from __future__ import annotations

from collections.abc import Iterable

from .models import ChartPositions, Hit, Overlay, OverlayLine

__all__ = ["make_overlay"]


def make_overlay(
    pos_a: ChartPositions,
    pos_b: ChartPositions,
    hits: Iterable[Hit],
) -> Overlay:
    """Return overlay payload for wheels A/B and aspect lines."""

    wheel_a = [(body, float(lon)) for body, lon in pos_a.iter_longitudes()]
    wheel_b = [(body, float(lon)) for body, lon in pos_b.iter_longitudes()]
    lines = [
        OverlayLine(
            bodyA=hit.body_a,
            bodyB=hit.body_b,
            aspect=hit.aspect,
            severity=float(hit.severity),
            offset=float(hit.delta),
        )
        for hit in hits
    ]
    return Overlay(wheelA=wheel_a, wheelB=wheel_b, lines=lines)
