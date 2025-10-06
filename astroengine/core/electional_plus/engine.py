"""Electional window scoring engine used by REST and UI layers."""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

PositionProvider = Callable[[datetime], Mapping[str, float]]

_ASPECT_ANGLES: dict[str, float] = {
    "conjunction": 0.0,
    "opposition": 180.0,
    "square": 90.0,
    "trine": 120.0,
    "sextile": 60.0,
    "quincunx": 150.0,
    "semisquare": 45.0,
    "sesquisquare": 135.0,
    "quintile": 72.0,
    "biquintile": 144.0,
}

_MAJOR_ASPECTS: tuple[str, ...] = (
    "conjunction",
    "opposition",
    "square",
    "trine",
    "sextile",
)


def _norm360(value: float) -> float:
    return value % 360.0


def _angle_delta(a: float, b: float) -> float:
    return (a - b + 180.0) % 360.0 - 180.0


def _angle_distance(a: float, b: float) -> float:
    return abs(_angle_delta(a, b))


def _sample_range(start: datetime, end: datetime, step_minutes: int) -> Sequence[datetime]:
    if step_minutes <= 0:
        raise ValueError("step_minutes must be positive")
    samples: list[datetime] = []
    delta = timedelta(minutes=step_minutes)
    cursor = start
    while cursor <= end:
        samples.append(cursor)
        cursor = cursor + delta
    if samples[-1] != end:
        samples.append(end)
    return samples


def _coarse_step_minutes(step_minutes: int, window_minutes: int) -> int:
    base = max(int(step_minutes), 1)
    if window_minutes <= base:
        return base
    coarse = max(base * 4, 60)
    return min(coarse, max(window_minutes, base))


def _align_forward(moment: datetime, base: datetime, step_minutes: int) -> datetime:
    if moment <= base:
        return base
    offset = (moment - base).total_seconds() / 60.0
    steps = math.ceil(offset / step_minutes - 1e-9)
    return base + timedelta(minutes=int(steps) * step_minutes)


def _align_backward(moment: datetime, base: datetime, step_minutes: int) -> datetime:
    if moment <= base:
        return base
    offset = (moment - base).total_seconds() / 60.0
    steps = math.floor(offset / step_minutes + 1e-9)
    return base + timedelta(minutes=int(steps) * step_minutes)


def _merge_ranges(
    ranges: Sequence[tuple[datetime, datetime, float]]
) -> list[tuple[datetime, datetime, float]]:
    if not ranges:
        return []
    ordered = sorted(ranges, key=lambda item: item[0])
    merged: list[tuple[datetime, datetime, float]] = []
    for start, end, score in ordered:
        if not merged:
            merged.append((start, end, score))
            continue
        prev_start, prev_end, prev_score = merged[-1]
        if start <= prev_end:
            merged[-1] = (prev_start, max(prev_end, end), prev_score + score)
        else:
            merged.append((start, end, score))
    return merged


def _split_range(
    start: datetime,
    end: datetime,
    max_span: timedelta | None,
) -> list[tuple[datetime, datetime]]:
    if max_span is None or max_span.total_seconds() <= 0:
        return [(start, end)]
    segments: list[tuple[datetime, datetime]] = []
    cursor = start
    while cursor <= end:
        segment_end = min(end, cursor + max_span)
        segments.append((cursor, segment_end))
        if segment_end >= end:
            break
        cursor = segment_end
    return segments


def _parse_ranges(ranges: list[tuple[str, str]] | None) -> list[tuple[int, int]]:
    parsed: list[tuple[int, int]] = []
    if not ranges:
        return parsed
    for start_s, end_s in ranges:
        sh, sm = [int(part) for part in start_s.split(":", 1)]
        eh, em = [int(part) for part in end_s.split(":", 1)]
        parsed.append((sh * 60 + sm, eh * 60 + em))
    return parsed


def _minute_of_day(ts: datetime) -> int:
    return ts.hour * 60 + ts.minute


def _in_ranges(minute: int, ranges: Sequence[tuple[int, int]]) -> bool:
    if not ranges:
        return True
    for start, end in ranges:
        if start <= end:
            if start <= minute < end:
                return True
        else:  # Wraps midnight
            if minute >= start or minute < end:
                return True
    return False


@dataclass(slots=True)
class AspectRule:
    a: str
    b: str
    aspects: Sequence[str]
    weight: float = 1.0
    orb_override: float | None = None


@dataclass(slots=True)
class ForbiddenRule:
    a: str
    b: str
    aspects: Sequence[str]
    penalty: float = 1.0
    orb_override: float | None = None


@dataclass(slots=True)
class ElectionalRules:
    window: Any
    window_minutes: int
    step_minutes: int
    top_k: int
    avoid_voc_moon: bool = False
    allowed_weekdays: Sequence[int] | None = None
    allowed_utc_ranges: list[tuple[str, str]] | None = None
    orb_policy: dict[str, Any] | None = None
    required_aspects: Sequence[AspectRule] = field(default_factory=list)
    forbidden_aspects: Sequence[ForbiddenRule] = field(default_factory=list)


@dataclass(slots=True)
class InstantResult:
    ts: datetime
    score: float
    reason: str | None = None
    matches: list[dict[str, Any]] = field(default_factory=list)
    violations: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class WindowResult:
    start: datetime
    end: datetime
    score: float
    samples: int
    avg_score: float
    top_instants: list[InstantResult]
    breakdown: dict[str, Any] = field(default_factory=dict)


def _gather_objects(rules: ElectionalRules) -> list[str]:
    objs: set[str] = set()
    for rule in list(rules.required_aspects) + list(rules.forbidden_aspects):
        objs.add(rule.a)
        objs.add(rule.b)
    objs.add("Moon")
    return sorted(objs)


def _is_voc(positions: Mapping[str, float], per_aspect: Mapping[str, float], default_orb: float, others: Iterable[str]) -> bool:
    moon = positions.get("Moon")
    if moon is None:
        raise KeyError("Moon position missing from provider output")
    for obj in others:
        if obj == "Moon":
            continue
        other_pos = positions.get(obj)
        if other_pos is None:
            continue
        separation = _norm360(moon - other_pos)
        for aspect_name in _MAJOR_ASPECTS:
            angle = _ASPECT_ANGLES.get(aspect_name)
            if angle is None:
                continue
            orb = float(per_aspect.get(aspect_name, default_orb))
            if _angle_distance(separation, angle) <= orb:
                return False
    return True


def _evaluate_required(
    rule: AspectRule,
    positions: Mapping[str, float],
    per_aspect: Mapping[str, float],
    default_orb: float,
) -> tuple[float, list[dict[str, Any]]]:
    pa = positions.get(rule.a)
    pb = positions.get(rule.b)
    if pa is None or pb is None:
        return 0.0, []
    separation = _norm360(pa - pb)
    best_score = 0.0
    best: dict[str, Any] | None = None
    for aspect_name in rule.aspects:
        angle = _ASPECT_ANGLES.get(aspect_name)
        if angle is None:
            continue
        orb_limit = rule.orb_override if rule.orb_override is not None else float(per_aspect.get(aspect_name, default_orb))
        if orb_limit <= 0:
            continue
        delta = _angle_distance(separation, angle)
        if delta <= orb_limit:
            closeness = max(0.0, 1.0 - delta / orb_limit)
            score = rule.weight * closeness
            if score > best_score:
                best_score = score
                best = {
                    "pair": f"{rule.a}-{rule.b}",
                    "aspect": aspect_name,
                    "orb": delta,
                    "limit": orb_limit,
                    "score": score,
                }
    if best is None:
        return 0.0, []
    return best_score, [best]


def _evaluate_forbidden(
    rule: ForbiddenRule,
    positions: Mapping[str, float],
    per_aspect: Mapping[str, float],
    default_orb: float,
) -> tuple[float, list[dict[str, Any]]]:
    pa = positions.get(rule.a)
    pb = positions.get(rule.b)
    if pa is None or pb is None:
        return 0.0, []
    separation = _norm360(pa - pb)
    total_penalty = 0.0
    hits: list[dict[str, Any]] = []
    for aspect_name in rule.aspects:
        angle = _ASPECT_ANGLES.get(aspect_name)
        if angle is None:
            continue
        orb_limit = rule.orb_override if rule.orb_override is not None else float(per_aspect.get(aspect_name, default_orb))
        if orb_limit <= 0:
            continue
        delta = _angle_distance(separation, angle)
        if delta <= orb_limit:
            closeness = max(0.0, 1.0 - delta / orb_limit)
            penalty = rule.penalty * closeness
            total_penalty += penalty
            hits.append(
                {
                    "pair": f"{rule.a}-{rule.b}",
                    "aspect": aspect_name,
                    "orb": delta,
                    "limit": orb_limit,
                    "penalty": penalty,
                }
            )
    return total_penalty, hits


def _score_instant(
    ts: datetime,
    *,
    rules: ElectionalRules,
    provider: PositionProvider,
    allowed_weekdays: set[int] | None,
    allowed_ranges: Sequence[tuple[int, int]],
    tracked_objects: Sequence[str],
    per_aspect: Mapping[str, float],
    default_orb: float,
) -> tuple[float, str | None, list[dict[str, Any]], list[dict[str, Any]]]:
    if allowed_weekdays is not None and ts.weekday() not in allowed_weekdays:
        return 0.0, "weekday_filtered", [], []

    minute = _minute_of_day(ts)
    if not _in_ranges(minute, allowed_ranges):
        return 0.0, "utc_range_filtered", [], []

    positions = provider(ts)

    if rules.avoid_voc_moon and _is_voc(positions, per_aspect, default_orb, tracked_objects):
        return 0.0, "void_of_course_moon", [], []

    matches: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []
    score = 0.0
    for rule in rules.required_aspects:
        contribution, hits = _evaluate_required(rule, positions, per_aspect, default_orb)
        if hits:
            matches.extend(hits)
            score += contribution
    for rule in rules.forbidden_aspects:
        penalty, hits = _evaluate_forbidden(rule, positions, per_aspect, default_orb)
        if hits:
            violations.extend(hits)
            score -= penalty
    return score, None, matches, violations


def _score_window(
    window_start: datetime,
    window_end: datetime,
    sample_step_minutes: int,
    *,
    rules: ElectionalRules,
    provider: PositionProvider,
    allowed_weekdays: set[int] | None,
    allowed_ranges: Sequence[tuple[int, int]],
    tracked_objects: Sequence[str],
    per_aspect: Mapping[str, float],
    default_orb: float,
    collect_details: bool,
) -> tuple[float, int, int, int, list[InstantResult] | None]:
    samples = _sample_range(window_start, window_end, sample_step_minutes)
    total_score = 0.0
    match_count = 0
    violation_count = 0
    instants: list[InstantResult] | None = [] if collect_details else None

    for ts in samples:
        score, reason, matches, violations = _score_instant(
            ts,
            rules=rules,
            provider=provider,
            allowed_weekdays=allowed_weekdays,
            allowed_ranges=allowed_ranges,
            tracked_objects=tracked_objects,
            per_aspect=per_aspect,
            default_orb=default_orb,
        )
        if reason is None:
            total_score += score
            match_count += len(matches)
            violation_count += len(violations)
            if collect_details:
                instants.append(
                    InstantResult(
                        ts=ts,
                        score=score,
                        reason=None,
                        matches=matches,
                        violations=violations,
                    )
                )
        elif collect_details:
            instants.append(
                InstantResult(
                    ts=ts,
                    score=0.0,
                    reason=reason,
                    matches=[],
                    violations=[],
                )
            )

    return total_score, len(samples), match_count, violation_count, instants


def search_best_windows(
    rules: ElectionalRules,
    provider: PositionProvider,
    *,
    max_scan_days: float | None = None,
    workers: int = 1,
) -> list[WindowResult]:
    start = rules.window.start
    end = rules.window.end
    if start >= end:
        return []

    window_delta = timedelta(minutes=rules.window_minutes)
    step_delta = timedelta(minutes=rules.step_minutes)
    last_start_allowed = end - window_delta
    if last_start_allowed < start:
        return []

    allowed_ranges = _parse_ranges(list(rules.allowed_utc_ranges) if rules.allowed_utc_ranges else None)
    allowed_weekdays = set(rules.allowed_weekdays) if rules.allowed_weekdays is not None else None

    per_aspect = (rules.orb_policy or {}).get("per_aspect", {})
    default_orb = float((rules.orb_policy or {}).get("default", 3.0))

    tracked_objects = _gather_objects(rules)

    coarse_step_minutes = _coarse_step_minutes(rules.step_minutes, rules.window_minutes)
    coarse_sample_minutes = max(rules.step_minutes, coarse_step_minutes)
    coarse_delta = timedelta(minutes=coarse_step_minutes)

    coarse_hits: list[tuple[datetime, float]] = []
    cursor = start
    while cursor <= last_start_allowed:
        window_start = cursor
        window_end = window_start + window_delta
        total_score, _, _, _, _ = _score_window(
            window_start,
            window_end,
            coarse_sample_minutes,
            rules=rules,
            provider=provider,
            allowed_weekdays=allowed_weekdays,
            allowed_ranges=allowed_ranges,
            tracked_objects=tracked_objects,
            per_aspect=per_aspect,
            default_orb=default_orb,
            collect_details=False,
        )
        if total_score > 0.0:
            coarse_hits.append((window_start, total_score))
        cursor += coarse_delta

    if coarse_hits:
        candidate_ranges: list[tuple[datetime, datetime, float]] = []
        for coarse_start, coarse_score in coarse_hits:
            range_start = max(start, coarse_start - coarse_delta)
            range_end = min(last_start_allowed, coarse_start + coarse_delta)
            if range_end >= range_start:
                candidate_ranges.append((range_start, range_end, coarse_score))
        merged = _merge_ranges(candidate_ranges)
    else:
        merged = [(start, last_start_allowed, 0.0)]

    max_span_td = None
    if max_scan_days is not None and max_scan_days > 0:
        max_span_td = timedelta(days=float(max_scan_days))

    segments: list[tuple[datetime, datetime]] = []
    for range_start, range_end, _score in merged:
        segments.extend(_split_range(range_start, range_end, max_span_td))

    if not segments:
        return []

    windows: list[WindowResult] = []

    def _refine(segment: tuple[datetime, datetime]) -> list[WindowResult]:
        seg_start, seg_end = segment
        aligned_start = _align_forward(seg_start, start, rules.step_minutes)
        aligned_end = _align_backward(seg_end, start, rules.step_minutes)
        if aligned_start > aligned_end or aligned_start > last_start_allowed:
            return []
        results: list[WindowResult] = []
        cursor_start = max(aligned_start, start)
        cursor_end = min(aligned_end, last_start_allowed)
        cursor_local = cursor_start
        while cursor_local <= cursor_end:
            window_start = cursor_local
            window_end = window_start + window_delta
            total_score, samples_count, match_count, violation_count, instants = _score_window(
                window_start,
                window_end,
                rules.step_minutes,
                rules=rules,
                provider=provider,
                allowed_weekdays=allowed_weekdays,
                allowed_ranges=allowed_ranges,
                tracked_objects=tracked_objects,
                per_aspect=per_aspect,
                default_orb=default_orb,
                collect_details=True,
            )
            instants = instants or []
            avg_score = total_score / samples_count if samples_count else 0.0
            top_sorted = sorted(instants, key=lambda item: item.score, reverse=True)
            top_instants = top_sorted[: min(5, len(top_sorted))]
            breakdown = {
                "required_matches": match_count,
                "forbidden_violations": violation_count,
                "filters": {
                    "allowed_weekdays": sorted(allowed_weekdays) if allowed_weekdays is not None else None,
                    "allowed_utc_ranges": rules.allowed_utc_ranges,
                    "avoid_voc_moon": rules.avoid_voc_moon,
                },
            }
            results.append(
                WindowResult(
                    start=window_start,
                    end=window_end,
                    score=total_score,
                    samples=samples_count,
                    avg_score=avg_score,
                    top_instants=top_instants,
                    breakdown=breakdown,
                )
            )
            cursor_local += step_delta
        return results

    worker_count = max(int(workers), 1)
    if worker_count > 1 and len(segments) > 1:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [executor.submit(_refine, segment) for segment in segments]
            for future in futures:
                windows.extend(future.result())
    else:
        for segment in segments:
            windows.extend(_refine(segment))

    windows.sort(key=lambda w: (-w.score, w.start))
    return windows[: rules.top_k]


__all__ = [
    "AspectRule",
    "ForbiddenRule",
    "ElectionalRules",
    "InstantResult",
    "WindowResult",
    "search_best_windows",
]
