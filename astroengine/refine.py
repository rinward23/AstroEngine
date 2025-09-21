# >>> AUTO-GEN BEGIN: AE Refinement v1.0
from __future__ import annotations
import datetime as dt
from typing import Callable

from .utils.angles import delta_angle


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
# >>> AUTO-GEN END: AE Refinement v1.0
