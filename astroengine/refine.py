# >>> AUTO-GEN BEGIN: AE Refinement v1.0
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from typing import Callable, Sequence

from .utils.angles import delta_angle

__all__ = [
    "bisection_time",
    "refine_mirror_exact",
    "gaussian_membership",
    "sigmoid_membership",
    "fuzzy_membership",
    "adaptive_corridor_width",
    "CorridorModel",
    "branch_sensitive_angles",
]


def _to_dt(iso: str) -> dt.datetime:
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))


def bisection_time(
    iso_lo: str,
    iso_hi: str,
    f: Callable[[str], float],
    *,
    max_iter: int = 32,
    tol_seconds: float = 0.5,
) -> str:
    """Find time where f(t) crosses 0 using bisection; returns ISO-8601Z.
    Assumes f(lo) and f(hi) have opposite signs.
    """
    lo = _to_dt(iso_lo)
    hi = _to_dt(iso_hi)
    for _ in range(max_iter):
        mid = lo + (hi - lo) / 2
        v = f(mid.replace(tzinfo=dt.timezone.utc).isoformat().replace("+00:00", "Z"))
        if abs((hi - lo).total_seconds()) <= tol_seconds:
            return mid.replace(tzinfo=dt.timezone.utc).isoformat().replace("+00:00", "Z")
        if v > 0:
            hi = mid
        else:
            lo = mid
    return mid.replace(tzinfo=dt.timezone.utc).isoformat().replace("+00:00", "Z")


def refine_mirror_exact(provider, iso_lo: str, iso_hi: str, moving: str, target: str, *, kind: str) -> str:
    """Refine antiscia/contra-antiscia exact time between brackets.
    kind in {"antiscia", "contra_antiscia"}.
    """
    from .astro.declination import antiscia_lon, contra_antiscia_lon

    def metric(t_iso: str) -> float:
        pos = provider.positions_ecliptic(t_iso, [moving, target])
        lm = pos[moving]["lon"]
        lt = pos[target]["lon"]
        mirror = antiscia_lon(lm) if kind == "antiscia" else contra_antiscia_lon(lm)
        return abs(delta_angle(mirror, lt))

    # Use sign of derivative via small step
    return bisection_time(iso_lo, iso_hi, lambda s: metric(s))


def gaussian_membership(delta_deg: float, width_deg: float, *, softness: float = 0.5) -> float:
    """Return a Gaussian membership score for ``delta_deg`` within ``width_deg``.

    Parameters
    ----------
    delta_deg:
        Absolute separation (in degrees) from the exact aspect.
    width_deg:
        Effective corridor half-width in degrees derived from orb policy
        or refinement heuristics. The value must be > 0 in real data usage.
    softness:
        Ratio controlling how quickly the corridor decays. Values < 0.5
        tighten the peak while values > 0.5 allow smoother shoulders.
    """

    width = max(float(width_deg), 1e-9)
    sigma = max(width * max(float(softness), 1e-3), 1e-9)
    return math.exp(-0.5 * (float(delta_deg) / sigma) ** 2)


def sigmoid_membership(delta_deg: float, width_deg: float, *, steepness: float = 4.0) -> float:
    """Return a logistic membership curve for ``delta_deg`` within ``width_deg``."""

    width = max(float(width_deg), 1e-9)
    x = float(delta_deg) / width
    return 1.0 / (1.0 + math.exp(steepness * (x - 1.0)))


def fuzzy_membership(
    delta_deg: float,
    width_deg: float,
    *,
    profile: str = "gaussian",
    softness: float = 0.5,
    steepness: float = 4.0,
) -> float:
    """Return a smooth membership value based on the requested ``profile``.

    ``profile`` may be ``"gaussian"`` or ``"sigmoid"``. Additional profiles
    can be wired in downstream registries without changing this helper.
    """

    profile_normalized = (profile or "gaussian").lower()
    if profile_normalized == "sigmoid":
        return sigmoid_membership(delta_deg, width_deg, steepness=steepness)
    return gaussian_membership(delta_deg, width_deg, softness=softness)


def adaptive_corridor_width(
    base_orb_deg: float,
    moving_speed_deg_per_day: float,
    target_speed_deg_per_day: float,
    *,
    aspect_strength: float = 1.0,
    retrograde: bool = False,
    minimum_orb_deg: float = 0.1,
) -> float:
    """Return an adaptive orb width derived from real velocity inputs.

    The function widens corridors when the relative velocity between the
    moving and target bodies increases, echoing traditional fast-planet orb
    allowances. Retrograde motion dampens the width slightly to reflect the
    interpretive ambiguity of reversing bodies.
    """

    base = max(float(base_orb_deg), float(minimum_orb_deg))
    speed_m = abs(float(moving_speed_deg_per_day))
    speed_t = abs(float(target_speed_deg_per_day))
    mean_speed = (speed_m + speed_t) / 2.0
    relative = abs(speed_m - speed_t)
    if mean_speed <= 1e-9:
        velocity_factor = 1.0
    else:
        velocity_factor = 1.0 + (relative / (mean_speed + 1e-9))
    if retrograde:
        velocity_factor *= 0.85
    strength = max(float(aspect_strength), 0.25)
    widened = base * velocity_factor * strength
    return max(widened, float(minimum_orb_deg))


@dataclass(frozen=True)
class CorridorModel:
    """Descriptor capturing a soft transit corridor around an exact aspect."""

    center_iso: str
    width_deg: float
    membership_profile: str = "gaussian"
    softness: float = 0.5
    metadata: dict[str, object] | None = None

    def membership(self, delta_deg: float) -> float:
        return fuzzy_membership(
            delta_deg,
            self.width_deg,
            profile=self.membership_profile,
            softness=self.softness,
        )

    def describe(self) -> dict[str, object]:
        payload = {
            "center_iso": self.center_iso,
            "width_deg": self.width_deg,
            "membership_profile": self.membership_profile,
            "softness": self.softness,
        }
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload


def branch_sensitive_angles(
    base_angle_deg: float,
    *,
    harmonics: Sequence[int] = (2, 3, 4, 6),
    include_cardinals: bool = True,
) -> tuple[float, ...]:
    """Return a tuple of harmonic angles derived from ``base_angle_deg``.

    The harmonic expansion mirrors fractal/chaotic triggering where the same
    geometry repeats across multiples (e.g., opposition, square, sextile).
    """

    base = float(base_angle_deg) % 360.0
    angles: set[float] = {round(base, 6)}
    if include_cardinals:
        for offset in (180.0, 120.0, 90.0, 60.0):
            angles.add(round((base + offset) % 360.0, 6))
            angles.add(round((base - offset) % 360.0, 6))
    for harmonic in harmonics:
        if harmonic <= 0:
            continue
        step = 360.0 / harmonic
        for idx in range(harmonic):
            angles.add(round((idx * step) % 360.0, 6))
    ordered = sorted({(angle + 360.0) % 360.0 for angle in angles})
    return tuple(ordered)
# >>> AUTO-GEN END: AE Refinement v1.0
