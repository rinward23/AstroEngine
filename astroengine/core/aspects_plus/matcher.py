"""Angular separation helpers for aspect matching."""

from __future__ import annotations

__all__ = ["angular_sep_deg"]


def angular_sep_deg(a: float, b: float) -> float:
    """Return the smallest angular distance between two ecliptic longitudes.

    Args:
        a: Longitude in degrees (any real value; wraps modulo 360).
        b: Longitude in degrees (any real value; wraps modulo 360).

    Returns:
        Absolute separation in degrees within the inclusive range [0, 180].
    """

    # Normalize the delta to (-180, 180] using modular arithmetic. The nested
    # modulo keeps the implementation numerically stable for arbitrarily large
    # inputs while avoiding floating-point drift near the wrap-around point.
    delta = (a - b + 180.0) % 360.0 - 180.0
    if delta < -180.0:
        delta += 360.0
    elif delta > 180.0:
        delta -= 360.0
    return abs(delta)
