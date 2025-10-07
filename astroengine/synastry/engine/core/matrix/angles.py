"""Angular helpers for synastry matrix computations."""

from __future__ import annotations

from collections.abc import Iterable

from astroengine.utils.angles import delta_angle, norm360

__all__ = [
    "normalize",
    "shortest_arc",
    "node_axis_delta",
    "node_to_node_delta",
    "is_node",
    "NODE_NAMES",
]

NODE_NAMES: frozenset[str] = frozenset({
    "node",
    "true node",
    "north node",
    "south node",
    "mean node",
})


def _normalize_name(name: str) -> str:
    return name.strip().lower()


def normalize(value: float) -> float:
    """Return ``value`` normalized to ``[0, 360)`` degrees."""

    return norm360(float(value))


def shortest_arc(a: float, b: float) -> float:
    """Return the absolute shortest angular distance between ``a`` and ``b``."""

    return abs(delta_angle(float(a), float(b)))


def node_axis_delta(node_lon: float, other_lon: float) -> float:
    """Return the shortest distance from ``other_lon`` to the node axis.

    The node axis is treated as the pair of points ``node_lon`` and ``node_lon + 180``.
    """

    base = normalize(node_lon)
    other = normalize(other_lon)
    north = shortest_arc(base, other)
    south = shortest_arc((base + 180.0) % 360.0, other)
    return north if north < south else south


def node_to_node_delta(a_lon: float, b_lon: float) -> float:
    """Return the nearest distance between two node axes."""

    base_a = normalize(a_lon)
    base_b = normalize(b_lon)
    candidates = (
        shortest_arc(base_a, base_b),
        shortest_arc(base_a, (base_b + 180.0) % 360.0),
        shortest_arc((base_a + 180.0) % 360.0, base_b),
    )
    return min(candidates)


def is_node(name: str, aliases: Iterable[str] | None = None) -> bool:
    """Return ``True`` when ``name`` refers to the lunar node axis."""

    normalized = _normalize_name(name)
    if aliases:
        return normalized in NODE_NAMES or normalized in {_normalize_name(a) for a in aliases}
    return normalized in NODE_NAMES

