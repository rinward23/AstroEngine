"""Legacy midpoint composite helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .natal import NatalChart

__all__ = ["CompositePosition", "MidpointCompositeChart", "compute_midpoint_composite"]


@dataclass(frozen=True)
class CompositePosition:
    """Composite midpoint computed from two source charts."""

    body: str
    midpoint_longitude: float
    source_a_longitude: float
    source_b_longitude: float


@dataclass(frozen=True)
class MidpointCompositeChart:
    """Midpoint composite chart derived from two natal charts."""

    positions: Mapping[str, CompositePosition]


def _midpoint(a: float, b: float) -> float:
    diff = (b - a) % 360.0
    midpoint = (a + diff / 2.0) % 360.0
    return midpoint if midpoint >= 0 else midpoint + 360.0


def compute_midpoint_composite(
    chart_a: NatalChart,
    chart_b: NatalChart,
    *,
    bodies: Sequence[str] | None = None,
) -> MidpointCompositeChart:
    """Return a midpoint composite chart using the shared bodies of both charts."""

    available_a = set(chart_a.positions.keys())
    available_b = set(chart_b.positions.keys())
    if bodies is None:
        selected = available_a & available_b
    else:
        selected = {body for body in bodies if body in available_a and body in available_b}
    if not selected:
        raise ValueError("No overlapping bodies to compute midpoint composite")

    positions: dict[str, CompositePosition] = {}
    for body in sorted(selected):
        pos_a = chart_a.positions[body].longitude
        pos_b = chart_b.positions[body].longitude
        positions[body] = CompositePosition(
            body=body,
            midpoint_longitude=_midpoint(pos_a, pos_b),
            source_a_longitude=pos_a,
            source_b_longitude=pos_b,
        )

    return MidpointCompositeChart(positions=positions)
