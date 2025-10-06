from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from math import cos, pi

# Default aspect weights; can be overridden by SeverityProfile.weights
DEFAULT_WEIGHTS: dict[str, float] = {
    "conjunction": 1.00,
    "opposition": 0.95,
    "square": 0.90,
    "trine": 0.80,
    "sextile": 0.60,
    "quincunx": 0.50,
    "semisquare": 0.45,
    "sesquisquare": 0.45,
    "quintile": 0.40,
    "biquintile": 0.40,
}


def _weight_for(aspect_name: str, profile_weights: Mapping[str, float] | None) -> float:
    key = aspect_name.lower()
    if profile_weights and key in profile_weights:
        return float(profile_weights[key])
    return DEFAULT_WEIGHTS.get(key, 0.50)


def taper_by_orb(orb_deg: float, orb_limit_deg: float) -> float:
    """Cosine taper from 1.0 at exact to 0.0 at orb_limit.

    - If orb >= limit → 0.0
    - If orb == 0 → 1.0
    - Smooth, monotonic decay: 0.5 * (1 + cos(pi * orb/limit))
    """
    if orb_limit_deg <= 0:
        return 0.0
    x = max(0.0, min(1.0, float(orb_deg) / float(orb_limit_deg)))
    return 0.5 * (1.0 + cos(pi * x)) if x < 1.0 else 0.0


def apply_modifiers(base: float, modifiers: Mapping[str, float] | None) -> float:
    """Multiply base by each modifier (e.g., dignity, house strength). None → 1.0.
    Values should be >=0; clip at 0.
    """
    if not modifiers:
        return base
    m = 1.0
    for _, val in modifiers.items():
        try:
            f = float(val)
        except Exception:
            f = 1.0
        m *= max(0.0, f)
    return base * m


def severity(
    aspect_name: str,
    orb_deg: float,
    orb_limit_deg: float,
    profile: Mapping[str, object] | None = None,
    modifiers: Mapping[str, float] | None = None,
) -> float:
    """Compute a severity score.

    Args:
        aspect_name: e.g., "square".
        orb_deg: absolute orb distance in degrees (>=0).
        orb_limit_deg: allowed orb for this pair/aspect.
        profile: dict with key "weights" (mapping aspect→weight), optional.
        modifiers: optional multiplicative factors (e.g., dignity/house), floats.

    Returns:
        Non-negative float score.
    """
    weights = (profile or {}).get("weights") if profile else None
    profile_weights: Mapping[str, float] | None
    if isinstance(weights, Mapping):
        profile_weights = weights  # type: ignore[assignment]
    else:
        profile_weights = None
    base_w = _weight_for(aspect_name, profile_weights)
    taper = taper_by_orb(orb_deg, orb_limit_deg)
    score = base_w * taper
    score = apply_modifiers(score, modifiers)
    return max(0.0, float(score))


@dataclass(frozen=True)
class EventPoint:
    ts: datetime  # timezone-aware UTC preferred
    score: float


def _date_key_utc(dt: datetime) -> str:
    # Normalize to UTC date key YYYY-MM-DD
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)
    return dt.strftime("%Y-%m-%d")


def daily_composite(events: Iterable[EventPoint]) -> dict[str, float]:
    """Average event scores per UTC day.
    Returns mapping YYYY-MM-DD → average score.
    """
    buckets: dict[str, list[float]] = {}
    for ev in events:
        k = _date_key_utc(ev.ts)
        buckets.setdefault(k, []).append(float(ev.score))
    return {k: (sum(v) / len(v)) if v else 0.0 for k, v in sorted(buckets.items())}


def monthly_composite(daily_series: Mapping[str, float]) -> dict[str, float]:
    """Average of daily values per month.
    Input keys: YYYY-MM-DD → value. Output keys: YYYY-MM → average.
    """
    months: dict[str, list[float]] = {}
    for day_key, val in daily_series.items():
        month = day_key[:7]
        months.setdefault(month, []).append(float(val))
    return {m: (sum(v) / len(v)) if v else 0.0 for m, v in sorted(months.items())}
