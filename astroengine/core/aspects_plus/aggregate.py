"""Aggregation helpers for aspect search results."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from astroengine.core.scan_plus.ranking import severity as compute_severity

from .harmonics import BASE_ASPECTS

try:  # pragma: no cover - avoid runtime import loop during static analysis
    from .scan import Hit
except Exception:  # pragma: no cover
    Hit = Any  # type: ignore

DateKey = str


def _aspect_name_from_angle(angle: float) -> str:
    for name, base_angle in BASE_ASPECTS.items():
        if abs(float(angle) - float(base_angle)) <= 1e-6:
            return name
    raise ValueError(f"Unsupported aspect angle: {angle}")


def _utc_date(ts: datetime) -> DateKey:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    else:
        ts = ts.astimezone(timezone.utc)
    return ts.strftime("%Y-%m-%d")


def rank_hits(
    hits: Iterable[Hit],
    profile: Mapping[str, Any] | None = None,
    order_by: str = "time",
) -> List[Dict[str, Any]]:
    """Convert raw scan hits into ranked dictionaries ready for serialization."""

    ranked: List[Dict[str, Any]] = []
    for hit in hits:
        aspect_name = _aspect_name_from_angle(getattr(hit, "aspect_angle"))
        sev = compute_severity(aspect_name, float(hit.orb), float(hit.orb_limit), profile)
        ranked.append(
            {
                "a": hit.a,
                "b": hit.b,
                "aspect": aspect_name,
                "harmonic": None,
                "exact_time": hit.exact_time,
                "orb": float(hit.orb),
                "orb_limit": float(hit.orb_limit),
                "severity": float(sev) if sev is not None else None,
                "meta": {"angle": float(getattr(hit, "aspect_angle", 0.0))},
            }
        )

    if order_by == "severity":
        ranked.sort(key=lambda h: (-(h["severity"] or 0.0), h["exact_time"]))
    elif order_by == "orb":
        ranked.sort(key=lambda h: (h["orb"], h["exact_time"]))
    else:
        ranked.sort(key=lambda h: (h["exact_time"], h["orb"]))
    return ranked


def day_bins(hits: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Aggregate ranked hits into UTC day buckets."""

    counts: Dict[DateKey, int] = defaultdict(int)
    scores: Dict[DateKey, List[float]] = defaultdict(list)

    for hit in hits:
        ts = hit.get("exact_time")
        if not isinstance(ts, datetime):
            continue
        key = _utc_date(ts)
        counts[key] += 1
        sev = hit.get("severity")
        if sev is not None:
            scores[key].append(float(sev))

    out: List[Dict[str, Any]] = []
    for key in sorted(counts):
        daily_scores = scores.get(key, [])
        avg = sum(daily_scores) / len(daily_scores) if daily_scores else None
        out.append({"date": key, "count": counts[key], "score": avg})
    return out


def paginate(
    hits: Sequence[Mapping[str, Any]],
    limit: int,
    offset: int,
) -> Tuple[List[Mapping[str, Any]], int]:
    """Return a window slice with total count for pagination."""

    total = len(hits)
    if offset >= total:
        return [], total
    end = offset + limit
    return list(hits[offset:end]), total


__all__ = ["rank_hits", "day_bins", "paginate"]
