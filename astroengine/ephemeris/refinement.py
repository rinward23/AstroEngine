"""Root-finding helpers for refining transit event timestamps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Tuple

__all__ = [
    "SECONDS_PER_DAY",
    "RefineResult",
    "bracket_root",
    "refine_root",
    "refine_event",
]

SECONDS_PER_DAY: float = 86_400.0


@dataclass(frozen=True, slots=True)
class RefineResult:
    """Result metadata returned by :func:`refine_root` and :func:`refine_event`.

    Attributes
    ----------
    t_exact_jd:
        Julian Day (UTC) representing the refined root estimate.
    iterations:
        Number of iterations executed by the refinement algorithm.
    method:
        Textual description of the algorithm used (e.g. ``"secant+bisection"``).
    achieved_tol_sec:
        Width of the final bracket expressed in seconds.
    status:
        ``"ok"`` when tolerance satisfied, otherwise ``"max_iter"`` or
        ``"bad_bracket"`` to indicate the fallback path that was taken.
    """

    t_exact_jd: float
    iterations: int
    method: str
    achieved_tol_sec: float
    status: str


def _to_days(seconds: float) -> float:
    return float(seconds) / SECONDS_PER_DAY


def bracket_root(
    f: Callable[[float], float], t0_jd: float, t1_jd: float
) -> Tuple[float, float]:
    """Return a bracket ``(t_lo, t_hi)`` ensuring opposite signs.

    Raises
    ------
    ValueError
        If ``f`` evaluated at both endpoints yields the same sign and neither
        endpoint is already a root.
    """

    f0 = f(t0_jd)
    if f0 == 0.0:
        return (t0_jd, t0_jd)
    f1 = f(t1_jd)
    if f1 == 0.0:
        return (t1_jd, t1_jd)
    if f0 * f1 > 0.0:
        raise ValueError("bad_bracket: function has same sign at bracket ends")
    return (t0_jd, t1_jd)


def refine_root(
    f: Callable[[float], float],
    t_lo_jd: float,
    t_hi_jd: float,
    *,
    tol_seconds: float = 1.0,
    max_iter: int = 64,
) -> RefineResult:
    """Refine a root of ``f`` within ``[t_lo_jd, t_hi_jd]``.

    The routine combines a secant step with bisection fallback to guarantee the
    root remains bracketed while converging towards the requested tolerance.
    ``tol_seconds`` is interpreted in **seconds** while the bounds and return
    value remain in Julian Days (UTC).
    """

    try:
        t_lo, t_hi = bracket_root(f, t_lo_jd, t_hi_jd)
    except ValueError:
        mid = 0.5 * (t_lo_jd + t_hi_jd)
        return RefineResult(
            t_exact_jd=mid,
            iterations=0,
            method="none",
            achieved_tol_sec=abs(t_hi_jd - t_lo_jd) * SECONDS_PER_DAY,
            status="bad_bracket",
        )

    tol_days = _to_days(max(tol_seconds, 0.0))
    f_lo = f(t_lo)
    f_hi = f(t_hi)

    method_used = "secant+bisection"
    iterations = 0
    for iterations in range(1, max_iter + 1):
        denom = f_hi - f_lo
        if denom != 0.0:
            t_sec = t_hi - f_hi * (t_hi - t_lo) / denom
        else:
            t_sec = 0.5 * (t_lo + t_hi)
        if not (min(t_lo, t_hi) <= t_sec <= max(t_lo, t_hi)):
            t_sec = 0.5 * (t_lo + t_hi)
        f_sec = f(t_sec)

        if f_sec == 0.0:
            return RefineResult(
                t_exact_jd=t_sec,
                iterations=iterations,
                method=method_used,
                achieved_tol_sec=0.0,
                status="ok",
            )

        if f_lo == 0.0:
            t_lo = t_sec
            f_lo = f_sec
        elif f_lo * f_sec <= 0.0:
            t_hi = t_sec
            f_hi = f_sec
        else:
            t_lo = t_sec
            f_lo = f_sec

        if abs(t_hi - t_lo) <= tol_days:
            t_exact = 0.5 * (t_lo + t_hi)
            return RefineResult(
                t_exact_jd=t_exact,
                iterations=iterations,
                method=method_used,
                achieved_tol_sec=abs(t_hi - t_lo) * SECONDS_PER_DAY,
                status="ok",
            )

    t_exact = 0.5 * (t_lo + t_hi)
    return RefineResult(
        t_exact_jd=t_exact,
        iterations=iterations,
        method=method_used,
        achieved_tol_sec=abs(t_hi - t_lo) * SECONDS_PER_DAY,
        status="max_iter",
    )


def refine_event(
    bracket: Tuple[float, float],
    *,
    delta_fn: Callable[[float], float],
    tol_seconds: float = 1.0,
    max_iter: int = 64,
) -> RefineResult:
    """Refine an event described by ``delta_fn`` across ``bracket``.

    ``delta_fn`` should return the signed separation (e.g. aspect delta) that
    crosses zero inside ``bracket``.
    """

    t_lo, t_hi = bracket
    return refine_root(
        delta_fn,
        float(t_lo),
        float(t_hi),
        tol_seconds=tol_seconds,
        max_iter=max_iter,
    )
