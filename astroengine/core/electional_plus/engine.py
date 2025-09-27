"""Electional window scoring engine used by REST and UI layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

PositionProvider = Callable[[datetime], Mapping[str, float]]

_ASPECT_ANGLES: Dict[str, float] = {
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

_MAJOR_ASPECTS: Tuple[str, ...] = (
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
    samples: List[datetime] = []
    delta = timedelta(minutes=step_minutes)
    cursor = start
    while cursor <= end:
        samples.append(cursor)
        cursor = cursor + delta
    if samples[-1] != end:
        samples.append(end)
    return samples


def _parse_ranges(ranges: Optional[List[Tuple[str, str]]]) -> List[Tuple[int, int]]:
    parsed: List[Tuple[int, int]] = []
    if not ranges:
        return parsed
    for start_s, end_s in ranges:
        sh, sm = [int(part) for part in start_s.split(":", 1)]
        eh, em = [int(part) for part in end_s.split(":", 1)]
        parsed.append((sh * 60 + sm, eh * 60 + em))
    return parsed


def _minute_of_day(ts: datetime) -> int:
    return ts.hour * 60 + ts.minute


def _in_ranges(minute: int, ranges: Sequence[Tuple[int, int]]) -> bool:
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
    allowed_weekdays: Optional[Sequence[int]] = None
    allowed_utc_ranges: Optional[List[Tuple[str, str]]] = None
    orb_policy: Optional[Dict[str, Any]] = None
    required_aspects: Sequence[AspectRule] = field(default_factory=list)
    forbidden_aspects: Sequence[ForbiddenRule] = field(default_factory=list)


@dataclass(slots=True)
class InstantResult:
    ts: datetime
    score: float
    reason: str | None = None
    matches: List[Dict[str, Any]] = field(default_factory=list)
    violations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class WindowResult:
    start: datetime
    end: datetime
    score: float
    samples: int
    avg_score: float
    top_instants: List[InstantResult]
    breakdown: Dict[str, Any] = field(default_factory=dict)


def _gather_objects(rules: ElectionalRules) -> List[str]:
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
) -> Tuple[float, List[Dict[str, Any]]]:
    pa = positions.get(rule.a)
    pb = positions.get(rule.b)
    if pa is None or pb is None:
        return 0.0, []
    separation = _norm360(pa - pb)
    best_score = 0.0
    best: Dict[str, Any] | None = None
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
) -> Tuple[float, List[Dict[str, Any]]]:
    pa = positions.get(rule.a)
    pb = positions.get(rule.b)
    if pa is None or pb is None:
        return 0.0, []
    separation = _norm360(pa - pb)
    total_penalty = 0.0
    hits: List[Dict[str, Any]] = []
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


def search_best_windows(rules: ElectionalRules, provider: PositionProvider) -> List[WindowResult]:
    start = rules.window.start
    end = rules.window.end
    if start >= end:
        return []

    window_delta = timedelta(minutes=rules.window_minutes)
    step_delta = timedelta(minutes=rules.step_minutes)
    allowed_ranges = _parse_ranges(list(rules.allowed_utc_ranges) if rules.allowed_utc_ranges else None)
    allowed_weekdays = set(rules.allowed_weekdays) if rules.allowed_weekdays is not None else None

    per_aspect = (rules.orb_policy or {}).get("per_aspect", {})
    default_orb = float((rules.orb_policy or {}).get("default", 3.0))

    tracked_objects = _gather_objects(rules)

    windows: List[WindowResult] = []

    cursor = start
    while cursor + window_delta <= end:
        window_start = cursor
        window_end = cursor + window_delta
        samples = _sample_range(window_start, window_end, rules.step_minutes)

        instants: List[InstantResult] = []
        total_score = 0.0
        match_count = 0
        violation_count = 0

        for ts in samples:
            reason: str | None = None
            if allowed_weekdays is not None and ts.weekday() not in allowed_weekdays:
                reason = "weekday_filtered"

            minute = _minute_of_day(ts)
            if reason is None and not _in_ranges(minute, allowed_ranges):
                reason = "utc_range_filtered"

            positions = provider(ts)

            if reason is None and rules.avoid_voc_moon:
                if _is_voc(positions, per_aspect, default_orb, tracked_objects):
                    reason = "void_of_course_moon"

            matches: List[Dict[str, Any]] = []
            violations: List[Dict[str, Any]] = []
            score = 0.0

            if reason is None:
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
                match_count += len(matches)
                violation_count += len(violations)
            else:
                score = 0.0

            instant = InstantResult(ts=ts, score=score, reason=reason, matches=matches, violations=violations)
            instants.append(instant)
            total_score += score

        samples_count = len(instants)
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

        windows.append(
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

        cursor += step_delta

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
