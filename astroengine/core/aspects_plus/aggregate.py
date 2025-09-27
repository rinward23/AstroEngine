"""Utilities to rank scan hits, bin them by day, and paginate results."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from astroengine.core.scan_plus.ranking import severity

from .scan import Hit

# Best-effort mapping angle → canonical aspect name; keep in sync with scanner
_ASPECT_LOOKUP: Dict[float, str] = {
    0.0: "conjunction",
    30.0: "semisextile",
    45.0: "semisquare",
    60.0: "sextile",
    72.0: "quintile",
    90.0: "square",
    120.0: "trine",
    135.0: "sesquisquare",
    144.0: "biquintile",
    150.0: "quincunx",
    180.0: "opposition",
}


def _aspect_name_from_angle(angle: float) -> str:
    """Normalize an aspect angle to the canonical scanner label."""

    key = round(float(angle), 6)
    return _ASPECT_LOOKUP.get(key, str(key))


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _utc_date_key(dt: datetime) -> str:
    return _ensure_utc(dt).strftime("%Y-%m-%d")


def _hit_dict(hit: Hit, aspect_name: str, sev: float) -> Dict[str, Any]:
    return {
        "a": hit.a,
        "b": hit.b,
        "aspect": aspect_name,
        "aspect_angle": float(hit.aspect_angle),
        "exact_time": hit.exact_time,
        "orb": float(hit.orb),
        "orb_limit": float(hit.orb_limit),
        "severity": float(sev),
    }


def _sort_key(order_by: str):
    if order_by == "severity":
        return lambda item: (-item["severity"], item["exact_time"])
    if order_by == "orb":
        return lambda item: (item["orb"], item["exact_time"])
    return lambda item: item["exact_time"]


def rank_hits(
    hits: Iterable[Hit],
    profile: Optional[Mapping[str, Any]] = None,
    order_by: str = "time",
) -> List[Dict[str, Any]]:
    """Attach severity to each hit and return a sorted list of mappings."""

    ranked: List[Dict[str, Any]] = []
    for hit in hits:
        aspect_name = _aspect_name_from_angle(hit.aspect_angle)
        sev = severity(aspect_name, hit.orb, hit.orb_limit, profile)
        ranked.append(_hit_dict(hit, aspect_name, sev))

    ranked.sort(key=_sort_key(order_by))
    return ranked


def day_bins(hits_with_severity: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Aggregate hits per UTC date, computing counts and average severity."""

    counts: Dict[str, int] = defaultdict(int)
    severity_values: Dict[str, List[float]] = defaultdict(list)

    for hit in hits_with_severity:
        exact = hit.get("exact_time")
        if not isinstance(exact, datetime):
            continue
        day_key = _utc_date_key(exact)
        counts[day_key] += 1
        severity_val = hit.get("severity")
        try:
            if severity_val is not None:
                severity_values[day_key].append(float(severity_val))
        except Exception:
            continue

    bins: List[Dict[str, Any]] = []
    for day in sorted(counts):
        values = severity_values.get(day, [])
        score: Optional[float]
        if values:
            score = sum(values) / len(values)
        else:
            score = None
        bins.append({"date": day, "count": counts[day], "score": score})
    return bins


def paginate(
    items: Iterable[Mapping[str, Any]],
    limit: int,
    offset: int,
) -> Tuple[List[Mapping[str, Any]], int]:
    """Return a window of ``items`` alongside the total length."""

    if limit < 0 or offset < 0:
        raise ValueError("limit and offset must be non-negative")

    if isinstance(items, list):
        total = len(items)
        return items[offset : offset + limit], total

    materialized = list(items)
    total = len(materialized)
    return materialized[offset : offset + limit], total
