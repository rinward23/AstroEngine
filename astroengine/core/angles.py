"""Angular utilities shared across transit calculations.

The runtime routinely compares longitudinal separations against aspect
targets.  Doing so with raw modulo arithmetic invites subtle bugs around
the 0°/360° boundary.  The helpers in this module centralise degree
normalisation along with a tiny stateful tracker that exposes a
continuous view of an angle series.  Downstream code can therefore track
Δλ without the familiar 359°→1° discontinuity.

The :func:`classify_relative_motion` helper also encapsulates the
applying vs. separating decision so both scoring and narrative layers
reason about events consistently.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

__all__ = [
    "AngleTracker",
    "AspectMotion",
    "DeltaLambdaTracker",
    "classify_relative_motion",
    "signed_delta",
    "normalize_degrees",
]


EPSILON_DEG: Final[float] = 1e-9


def normalize_degrees(angle: float) -> float:
    """Return ``angle`` normalised to the ``[0, 360)`` interval.

    Parameters
    ----------
    angle:
        Value in **degrees**. Inputs outside the canonical range are
        wrapped by multiples of 360° without altering the underlying
        provenance.

    Returns
    -------
    float
        A degree value in ``[0, 360)``. Values within ``1e-9`` of
        ``360`` are coerced to ``0`` so callers can rely on a consistent
        wrap-around contract when comparing angles sourced from Solar
        Fire or Swiss Ephemeris data.
    """

    wrapped = float(angle) % 360.0
    if wrapped >= 360.0 - EPSILON_DEG:
        wrapped = 0.0
    return wrapped if wrapped >= 0.0 else wrapped + 360.0


def signed_delta(angle: float) -> float:
    """Return ``angle`` wrapped to the ``[-180, 180)`` interval.

    This helper is commonly used when comparing longitudinal
    separations. The value is expressed in **degrees** so downstream
    scoring code can feed it directly into orb calculations.
    """

    wrapped = normalize_degrees(angle)
    if wrapped >= 180.0:
        return wrapped - 360.0
    return wrapped


@dataclass
class AngleTracker:
    """Track a continuous angle sequence without wrap-around jumps."""

    _turns: int = 0
    _last: float | None = None

    def update(self, angle: float) -> float:
        normalized = normalize_degrees(angle)
        if self._last is None:
            self._last = normalized
            return normalized

        delta = normalized - self._last
        if delta > 180.0:
            self._turns -= 1
        elif delta < -180.0:
            self._turns += 1

        self._last = normalized
        return normalized + self._turns * 360.0


class DeltaLambdaTracker:
    """Continuously track longitudinal separation between two bodies."""

    def __init__(self) -> None:
        self._tracker = AngleTracker()

    def update(self, moving_longitude: float, reference_longitude: float) -> float:
        separation = normalize_degrees(moving_longitude - reference_longitude)
        return self._tracker.update(separation)


@dataclass(frozen=True)
class AspectMotion:
    """Classify the relative motion around an aspect target."""

    state: str
    offset_deg: float
    relative_speed_deg_per_day: float

    @property
    def is_applying(self) -> bool:
        return self.state == "applying"

    @property
    def is_separating(self) -> bool:
        return self.state == "separating"


def classify_relative_motion(
    separation_deg: float,
    aspect_angle_deg: float,
    moving_speed_deg_per_day: float,
    reference_speed_deg_per_day: float,
    *,
    tolerance: float = 1e-4,
) -> AspectMotion:
    """Return :class:`AspectMotion` describing applying vs separating."""

    offset = separation_deg - aspect_angle_deg
    relative_speed = moving_speed_deg_per_day - reference_speed_deg_per_day

    if abs(offset) <= tolerance:
        if abs(relative_speed) <= tolerance:
            state = "stationary"
        else:
            state = "separating" if relative_speed > 0 else "applying"
        return AspectMotion(
            state=state, offset_deg=0.0, relative_speed_deg_per_day=relative_speed
        )

    if abs(relative_speed) <= tolerance:
        state = "stationary"
    else:
        state = "applying" if offset * relative_speed < 0.0 else "separating"

    return AspectMotion(
        state=state, offset_deg=offset, relative_speed_deg_per_day=relative_speed
    )
