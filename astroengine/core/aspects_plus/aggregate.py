
"""Aggregation helpers for aspect search results."""


from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from astroengine.core.scan_plus.ranking import severity as compute_severity

from .harmonics import BASE_ASPECTS

try:  # pragma: no cover - avoid runtime import loop during static analysis
    from .scan import Hit
except Exception:  # pragma: no cover
    Hit = Any  # type: ignore

DateKey = str


def _aspect_name_from_angle(angle: float) -> str | None:
    for name, base_angle in BASE_ASPECTS.items():
        if abs(float(angle) - float(base_angle)) <= 1e-6:
            return name
    return None


def _utc_date(ts: datetime) -> DateKey:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    else:
        ts = ts.astimezone(UTC)
    return ts.strftime("%Y-%m-%d")



def rank_hits(
    hits: Iterable[Hit],

    profile: Mapping[str, Any] | None = None,
    order_by: str = "time",
) -> list[dict[str, Any]]:
    """Convert raw scan hits into ranked dictionaries ready for serialization."""

    ranked: list[dict[str, Any]] = []
    for hit in hits:
        hit_meta = getattr(hit, "meta", {}) or {}
        if isinstance(hit_meta, Mapping):
            meta: dict[str, Any] = dict(hit_meta)
        else:
            meta = {}

        aspect_name = meta.get("aspect")
        inferred = _aspect_name_from_angle(hit.aspect_angle)
        if not aspect_name:
            aspect_name = inferred or f"angle_{float(hit.aspect_angle):.3f}"
        harmonic = meta.get("harmonic")

        if inferred:
            sev = compute_severity(aspect_name, float(hit.orb), float(hit.orb_limit), profile)
        else:
            sev = None

        meta_out: dict[str, Any] = {"angle": float(getattr(hit, "aspect_angle", 0.0))}
        for k, v in meta.items():
            if k in {"aspect", "harmonic"}:
                continue
            meta_out[k] = v
        ranked.append(
            {
                "a": hit.a,
                "b": hit.b,
                "aspect": aspect_name,
                "harmonic": harmonic,
                "exact_time": hit.exact_time,
                "orb": float(hit.orb),
                "orb_limit": float(hit.orb_limit),
                "severity": float(sev) if sev is not None else None,
                "meta": meta_out,
            }
        )

    if order_by == "severity":
        ranked.sort(key=lambda h: (-(h["severity"] or 0.0), h["exact_time"]))
    elif order_by == "orb":
        ranked.sort(key=lambda h: (h["orb"], h["exact_time"]))
    else:
        ranked.sort(key=lambda h: (h["exact_time"], h["orb"]))
    return ranked


def day_bins(hits: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate ranked hits into UTC day buckets."""

    counts: dict[DateKey, int] = defaultdict(int)
    scores: dict[DateKey, list[float]] = defaultdict(list)

    for hit in hits:
        ts = hit.get("exact_time")
        if not isinstance(ts, datetime):
            continue
        key = _utc_date(ts)
        counts[key] += 1
        sev = hit.get("severity")
        if sev is not None:
            scores[key].append(float(sev))

    out: list[dict[str, Any]] = []
    for key in sorted(counts):
        daily_scores = scores.get(key, [])
        avg = sum(daily_scores) / len(daily_scores) if daily_scores else None
        out.append({"date": key, "count": counts[key], "score": avg})
    return out


def paginate(
    hits: Sequence[Mapping[str, Any]],
    limit: int,
    offset: int,
) -> tuple[list[Mapping[str, Any]], int]:
    """Return a window slice with total count for pagination."""


    if limit < 0:
        raise ValueError("limit must be non-negative")
    if offset < 0:
        raise ValueError("offset must be non-negative")


    total = len(hits)
    if offset >= total:
        return [], total
    end = offset + limit
    return list(hits[offset:end]), total


__all__ = ["rank_hits", "day_bins", "paginate"]

