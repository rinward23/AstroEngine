"""Collision-aware polar label placement."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from math import cos, degrees, radians, sin
from typing import Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class LabelRequest:
    """Description of a label to be positioned around a polar chart."""

    identifier: str
    angle: float  # degrees
    radius: float
    width: float
    height: float
    priority: int = 0
    metadata: Tuple[Tuple[str, object], ...] = field(default_factory=tuple)

    def normalised_angle(self) -> float:
        return self.angle % 360.0

    def __post_init__(self) -> None:
        meta: Any = self.metadata
        if isinstance(meta, dict):
            sorted_items = tuple((str(key), meta[key]) for key in sorted(meta))
            object.__setattr__(self, "metadata", sorted_items)
        elif isinstance(meta, (list, tuple)):
            object.__setattr__(self, "metadata", tuple(meta))
        else:
            raise TypeError("metadata must be a mapping or sequence of pairs")


@dataclass
class LabelPlacement:
    """Resolved position for a label."""

    identifier: str
    angle: float
    radius: float
    x: float
    y: float
    request: LabelRequest = field(repr=False, compare=False)
    leader: bool
    leader_start: Optional[Tuple[float, float]] = None
    leader_end: Optional[Tuple[float, float]] = None

    def bounds(self) -> "PolarBounds":
        return PolarBounds.from_request(self.request, self.angle, self.radius)


@dataclass
class PolarBounds:
    angle_min: float
    angle_max: float
    radius_min: float
    radius_max: float

    @classmethod
    def from_request(cls, request: LabelRequest, angle: float, radius: float) -> "PolarBounds":
        # Convert width expressed along the tangent into an angular span.
        span = 360.0
        if radius > 0.0 and request.width > 0.0:
            span = degrees(request.width / radius)
        span = min(max(span, 0.0), 360.0)
        half_span = span / 2.0
        angle_min = (angle - half_span) % 360.0
        angle_max = (angle + half_span) % 360.0
        half_height = request.height / 2.0
        radius_min = radius - half_height
        radius_max = radius + half_height
        return cls(angle_min, angle_max, radius_min, radius_max)

    def overlaps(self, other: "PolarBounds", angle_tolerance: float = 0.01, radial_tolerance: float = 0.01) -> bool:
        if not _radial_overlap(self.radius_min, self.radius_max, other.radius_min, other.radius_max, radial_tolerance):
            return False
        return _angular_overlap(self.angle_min, self.angle_max, other.angle_min, other.angle_max, angle_tolerance)


def _radial_overlap(a_min: float, a_max: float, b_min: float, b_max: float, tolerance: float) -> bool:
    return (a_min - tolerance) < (b_max + tolerance) and (b_min - tolerance) < (a_max + tolerance)


def _angular_overlap(a_min: float, a_max: float, b_min: float, b_max: float, tolerance: float) -> bool:
    def _interval_overlap(x_min: float, x_max: float, y_min: float, y_max: float) -> bool:
        return (x_min - tolerance) < (y_max + tolerance) and (y_min - tolerance) < (x_max + tolerance)

    # Handle wrap-around by expanding intervals that cross zero into two ranges.
    a_ranges = _split_range(a_min, a_max)
    b_ranges = _split_range(b_min, b_max)
    for ax_min, ax_max in a_ranges:
        for bx_min, bx_max in b_ranges:
            if _interval_overlap(ax_min, ax_max, bx_min, bx_max):
                return True
    return False


def _split_range(start: float, end: float) -> List[Tuple[float, float]]:
    if start <= end:
        return [(start, end)]
    return [(start, 360.0), (0.0, end)]


class Labeler:
    """Place labels in a polar band while avoiding overlaps."""

    def __init__(
        self,
        band_radius: float,
        band_height: float,
        *,
        outer_radius: Optional[float] = None,
        radial_step: float = 6.0,
        max_iterations: int = 5,
    ) -> None:
        self.band_radius = band_radius
        self.band_height = band_height
        self.outer_radius = outer_radius or (band_radius + band_height * 1.5)
        self.radial_step = radial_step
        self.max_iterations = max_iterations

    def place(self, labels: Sequence[LabelRequest]) -> List[LabelPlacement]:
        ordered = sorted(labels, key=lambda item: (item.priority, item.identifier))
        placements: List[LabelPlacement] = []
        occupied: List[PolarBounds] = []
        for request in ordered:
            angle = request.normalised_angle()
            base_radius = request.radius or self.band_radius
            result = self._place_single(request, angle, base_radius, occupied)
            placements.append(result)
            if not result.leader:
                occupied.append(result.bounds())
        return placements

    # Internal helpers --------------------------------------------------
    def _place_single(
        self,
        request: LabelRequest,
        angle: float,
        base_radius: float,
        occupied: Sequence[PolarBounds],
    ) -> LabelPlacement:
        for offset in self._nudge_sequence():
            radius = base_radius + offset
            if radius < (self.band_radius - self.band_height / 2.0):
                continue
            bounds = PolarBounds.from_request(request, angle, radius)
            if any(bounds.overlaps(existing) for existing in occupied):
                continue
            x, y = _polar_to_cartesian(angle, radius)
            return LabelPlacement(
                identifier=request.identifier,
                angle=angle,
                radius=radius,
                x=x,
                y=y,
                leader=False,
                request=request,
            )
        # Leader line fallback.
        anchor_x, anchor_y = _polar_to_cartesian(angle, base_radius)
        label_x, label_y = _polar_to_cartesian(angle, self.outer_radius)
        return LabelPlacement(
            identifier=request.identifier,
            angle=angle,
            radius=self.outer_radius,
            x=label_x,
            y=label_y,
            leader=True,
            leader_start=(anchor_x, anchor_y),
            leader_end=(label_x, label_y),
            request=request,
        )

    def _nudge_sequence(self) -> Iterable[float]:
        yield 0.0
        for iteration in range(1, self.max_iterations + 1):
            delta = iteration * self.radial_step
            yield delta
            yield -delta


def _polar_to_cartesian(angle: float, radius: float) -> Tuple[float, float]:
    theta = radians(angle)
    return radius * cos(theta), radius * sin(theta)
