"""Core engine for Relationship Timeline (SPEC-B-012)."""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

from ..ephemeris.adapter import EphemerisAdapter, EphemerisSample
from ..utils.angles import delta_angle, norm360
from .policy import (
    ASPECT_CAPS,
    ASPECT_FAMILY,
    ASPECT_WEIGHTS,
    BASE_ORBS,
    DEFAULT_ASPECTS,
    DEFAULT_TARGETS,
    DEFAULT_TRANSITERS,
    SCORE_NORMALIZER,
    SERIES_SAMPLE_HOURS,
    TARGET_FAMILY,
    TARGET_WEIGHTS,
    TRANSITER_WEIGHTS,
)

__all__ = [
    "Event",
    "TimelineRequest",
    "TimelineResult",
    "TimelineSummary",
    "compute_relationship_timeline",
]


_MAX_RANGE_DAYS = 366 * 3
_DEDUPE_WINDOW = dt.timedelta(hours=12)
_ROOT_TOL_SECONDS = 1.0
_ORBITAL_ZERO_TOL = 1e-6

try:  # pragma: no cover - import fallback mirrors other packages
    import swisseph as swe
except Exception:  # pragma: no cover - tests rely on dependency stub
    swe = None


_DEFAULT_BODY_IDS = {
    "Venus": getattr(swe, "VENUS", 3),
    "Mars": getattr(swe, "MARS", 4),
    "Jupiter": getattr(swe, "JUPITER", 5),
    "Saturn": getattr(swe, "SATURN", 6),
}


@dataclass(frozen=True)
class TimelineRequest:
    """Input payload describing the requested timeline scan."""

    chart_type: str
    positions: Mapping[str, float]
    range_start: dt.datetime
    range_end: dt.datetime
    transiters: Sequence[str] | None = None
    targets: Sequence[str] | None = None
    aspects: Sequence[int] | None = None
    min_severity: float = 0.0
    top_k: int | None = None
    include_series: bool = False


@dataclass(frozen=True)
class Event:
    """Return or transit event detected by the timeline engine."""

    type: str
    transiter: str
    target: str | None
    aspect: int | None
    exact_utc: dt.datetime
    start_utc: dt.datetime
    end_utc: dt.datetime
    orb: float
    max_severity: float
    score: float
    series: tuple[tuple[dt.datetime, float], ...] | None = None


@dataclass(frozen=True)
class TimelineSummary:
    """Aggregate statistics describing the computed events."""

    counts_by_transiter: Mapping[str, int]
    counts_by_target: Mapping[str, int]
    counts_by_aspect: Mapping[str, int]
    total_score: float
    calendar: Mapping[str, float]


@dataclass(frozen=True)
class TimelineResult:
    """Full result bundle containing events and export payloads."""

    events: tuple[Event, ...]
    summary: TimelineSummary
    csv: str
    ics: str


def compute_relationship_timeline(
    request: TimelineRequest,
    *,
    adapter: EphemerisAdapter | None = None,
    body_ids: Mapping[str, int] | None = None,
) -> TimelineResult:
    """Convenience wrapper creating an engine instance and executing it."""

    engine = _TimelineEngine(adapter=adapter, body_ids=body_ids)
    return engine.compute(request)


class _TimelineEngine:
    """Internal helper coordinating sampling, detection, and scoring."""

    _STEP_HOURS: Mapping[str, int] = {
        "Venus": 6,
        "Mars": 6,
        "Jupiter": 12,
        "Saturn": 12,
    }

    def __init__(
        self,
        *,
        adapter: EphemerisAdapter | None = None,
        body_ids: Mapping[str, int] | None = None,
    ) -> None:
        self._adapter = adapter or EphemerisAdapter()
        self._body_ids = dict(_DEFAULT_BODY_IDS)
        if body_ids:
            self._body_ids.update(body_ids)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def compute(self, request: TimelineRequest) -> TimelineResult:
        normalized = self._normalize_request(request)
        samples = self._sample_transiters(normalized)
        events = self._detect_events(normalized, samples)
        filtered = self._apply_filters(events, normalized)
        summary = self._summaries(filtered)
        from .csvout import events_to_csv
        from .ics import events_to_ics

        csv_payload = events_to_csv(filtered, chart_type=normalized.chart_type)
        ics_payload = events_to_ics(filtered, chart_type=normalized.chart_type)
        return TimelineResult(
            events=tuple(filtered),
            summary=summary,
            csv=csv_payload,
            ics=ics_payload,
        )

    # ------------------------------------------------------------------
    # Validation & normalisation helpers
    # ------------------------------------------------------------------
    def _normalize_request(self, request: TimelineRequest) -> TimelineRequest:
        if request.chart_type not in {"Composite", "Davison"}:
            raise ValueError("chart_type must be 'Composite' or 'Davison'")
        start = _ensure_utc(request.range_start)
        end = _ensure_utc(request.range_end)
        if end <= start:
            raise ValueError("range_end must be after range_start")
        if (end - start).days > _MAX_RANGE_DAYS:
            raise ValueError("range exceeds 3-year supported span")

        raw_transiters = (
            request.transiters if request.transiters is not None else DEFAULT_TRANSITERS
        )
        transiters = [name for name in raw_transiters if name in DEFAULT_TRANSITERS]
        if not transiters:
            raise ValueError("No supported transiters specified")

        raw_aspects = request.aspects if request.aspects is not None else DEFAULT_ASPECTS
        aspects = [int(angle) for angle in raw_aspects if int(angle) in ASPECT_CAPS]
        if not aspects:
            raise ValueError("No supported aspects specified")

        raw_targets = request.targets if request.targets is not None else DEFAULT_TARGETS
        targets = [str(name) for name in raw_targets]

        positions = {key: norm360(float(val)) for key, val in request.positions.items()}

        return TimelineRequest(
            chart_type=request.chart_type,
            positions=positions,
            range_start=start,
            range_end=end,
            transiters=tuple(transiters),
            targets=tuple(targets),
            aspects=tuple(aspects),
            min_severity=float(max(request.min_severity, 0.0)),
            top_k=request.top_k,
            include_series=request.include_series,
        )

    # ------------------------------------------------------------------
    # Sampling
    # ------------------------------------------------------------------
    def _sample_transiters(
        self, request: TimelineRequest
    ) -> dict[str, list[tuple[dt.datetime, float]]]:
        samples: dict[str, list[tuple[dt.datetime, float]]] = {}
        for name in request.transiters:
            code = self._resolve_body(name)
            step_hours = self._STEP_HOURS.get(name, 12)
            step = dt.timedelta(hours=step_hours)
            current = request.range_start
            entries: list[tuple[dt.datetime, float]] = []
            while current <= request.range_end:
                lon = self._longitude(code, current)
                entries.append((current, lon))
                current += step
            if entries[-1][0] < request.range_end:
                lon = self._longitude(code, request.range_end)
                entries.append((request.range_end, lon))
            samples[name] = entries
        return samples

    def _longitude(self, code: int, moment: dt.datetime) -> float:
        sample: EphemerisSample = self._adapter.sample(code, moment)
        return norm360(float(sample.longitude))

    def _resolve_body(self, name: str) -> int:
        try:
            return int(self._body_ids[name])
        except KeyError as exc:  # pragma: no cover - guard rail
            raise ValueError(f"Unsupported transiter '{name}'") from exc

    # ------------------------------------------------------------------
    # Event detection
    # ------------------------------------------------------------------
    def _detect_events(
        self,
        request: TimelineRequest,
        samples: Mapping[str, list[tuple[dt.datetime, float]]],
    ) -> list[Event]:
        events: list[Event] = []
        for transiter in request.transiters:
            entries = samples[transiter]
            code = self._resolve_body(transiter)
            base_long = request.positions.get(transiter)
            if base_long is not None:
                events.extend(
                    self._detect_returns(
                        request,
                        transiter,
                        code,
                        float(base_long),
                        entries,
                    )
                )
            events.extend(
                self._detect_transits(request, transiter, code, entries)
            )
        deduped = self._dedupe(events)
        return deduped

    def _detect_returns(
        self,
        request: TimelineRequest,
        transiter: str,
        code: int,
        base_long: float,
        entries: Sequence[tuple[dt.datetime, float]],
    ) -> list[Event]:
        events: list[Event] = []
        orb = _effective_orb(transiter, 0)
        if orb <= 0:
            return events
        for idx in range(1, len(entries)):
            t0, lon0 = entries[idx - 1]
            t1, lon1 = entries[idx]
            d0 = delta_angle(lon0, base_long)
            d1 = delta_angle(lon1, base_long)
            if _is_bracket(d0, d1):
                exact = self._refine_zero(
                    lambda moment: delta_angle(
                        self._longitude(code, moment), base_long
                    ),
                    t0,
                    t1,
                    d0,
                    d1,
                )
                events.append(
                    self._build_event(
                        request,
                        type_="return",
                        transiter=transiter,
                        target=None,
                        aspect=None,
                        orb=orb,
                        exact=exact,
                        delta=lambda moment: abs(
                            delta_angle(self._longitude(code, moment), base_long)
                        ),
                    )
                )
        return events

    def _detect_transits(
        self,
        request: TimelineRequest,
        transiter: str,
        code: int,
        entries: Sequence[tuple[dt.datetime, float]],
    ) -> list[Event]:
        events: list[Event] = []
        target_positions = {
            target: request.positions[target]
            for target in request.targets
            if target in request.positions
        }
        for target, target_lon in target_positions.items():
            axis_target = _is_node_axis(target)
            for aspect in request.aspects:
                orb = _effective_orb(transiter, aspect)
                if orb <= 0:
                    continue
                for idx in range(1, len(entries)):
                    t0, lon0 = entries[idx - 1]
                    t1, lon1 = entries[idx]
                    d0 = _aspect_delta(lon0, target_lon, aspect, axis_target)
                    d1 = _aspect_delta(lon1, target_lon, aspect, axis_target)
                    if _is_bracket(d0, d1):
                        exact = self._refine_zero(
                            lambda moment, targ=target_lon: _aspect_delta(
                                self._longitude(code, moment), targ, aspect, axis_target
                            ),
                            t0,
                            t1,
                            d0,
                            d1,
                        )
                        events.append(
                            self._build_event(
                                request,
                                type_="transit",
                                transiter=transiter,
                                target=target,
                                aspect=aspect,
                                orb=orb,
                                exact=exact,
                                delta=lambda moment, targ=target_lon: abs(
                                    _aspect_delta(
                                        self._longitude(code, moment),
                                        targ,
                                        aspect,
                                        axis_target,
                                    )
                                ),
                            )
                        )
        return events

    def _refine_zero(
        self,
        func,
        t0: dt.datetime,
        t1: dt.datetime,
        v0: float,
        v1: float,
    ) -> dt.datetime:
        if abs(v0) <= _ORBITAL_ZERO_TOL:
            return t0
        if abs(v1) <= _ORBITAL_ZERO_TOL:
            return t1
        if v0 * v1 > 0:
            return t0 if abs(v0) < abs(v1) else t1
        lower, upper = (t0, t1) if t0 < t1 else (t1, t0)
        f_lower, f_upper = (v0, v1) if lower == t0 else (v1, v0)
        for _ in range(64):
            midpoint = lower + (upper - lower) / 2
            value = float(func(midpoint))
            if abs(value) <= _ORBITAL_ZERO_TOL or (
                upper - lower
            ).total_seconds() <= _ROOT_TOL_SECONDS:
                return midpoint
            if f_lower * value <= 0:
                upper = midpoint
                f_upper = value
            else:
                lower = midpoint
                f_lower = value
        return lower + (upper - lower) / 2

    def _build_event(
        self,
        request: TimelineRequest,
        *,
        type_: str,
        transiter: str,
        target: str | None,
        aspect: int | None,
        orb: float,
        exact: dt.datetime,
        delta,
    ) -> Event:
        step_hours = self._STEP_HOURS.get(transiter, 12)
        step = dt.timedelta(hours=step_hours)
        start = self._expand_to_orb(
            exact,
            request.range_start,
            -step,
            orb,
            delta,
        )
        end = self._expand_to_orb(
            exact,
            request.range_end,
            step,
            orb,
            delta,
        )
        severity = lambda moment: _severity_from_delta(delta(moment), orb)
        series = self._series_samples(start, end, severity) if request.include_series else None
        score = self._score_event(transiter, target, aspect, start, end, severity)
        max_sev = severity(exact)
        return Event(
            type=type_,
            transiter=transiter,
            target=target,
            aspect=aspect,
            exact_utc=exact,
            start_utc=start,
            end_utc=end,
            orb=orb,
            max_severity=max_sev,
            score=score,
            series=series,
        )

    def _expand_to_orb(
        self,
        exact: dt.datetime,
        limit: dt.datetime,
        step: dt.timedelta,
        orb: float,
        delta,
    ) -> dt.datetime:
        direction = -1 if step.total_seconds() < 0 else 1
        current = exact
        inside = exact
        while True:
            candidate = current + step
            if direction < 0 and candidate <= limit:
                boundary = limit
                if delta(boundary) <= orb + _ORBITAL_ZERO_TOL:
                    return boundary
                break
            if direction > 0 and candidate >= limit:
                boundary = limit
                if delta(boundary) <= orb + _ORBITAL_ZERO_TOL:
                    return boundary
                break
            dist = delta(candidate)
            if dist > orb + _ORBITAL_ZERO_TOL:
                boundary = candidate
                break
            inside = candidate
            current = candidate
        lo = inside if inside < boundary else boundary
        hi = boundary if boundary > inside else inside
        f_lo = delta(lo) - orb
        f_hi = delta(hi) - orb
        if f_lo == 0:
            return lo
        if f_hi == 0:
            return hi
        if f_lo > 0 and f_hi > 0:
            return lo
        for _ in range(64):
            mid = lo + (hi - lo) / 2
            value = delta(mid) - orb
            if abs(value) <= _ORBITAL_ZERO_TOL or (
                hi - lo
            ).total_seconds() <= _ROOT_TOL_SECONDS:
                return mid
            if f_lo * value <= 0:
                hi = mid
                f_hi = value
            else:
                lo = mid
                f_lo = value
        return lo + (hi - lo) / 2

    def _series_samples(self, start, end, severity_fn):
        step = dt.timedelta(hours=SERIES_SAMPLE_HOURS)
        samples: list[tuple[dt.datetime, float]] = []
        moment = start
        while moment < end:
            samples.append((moment, severity_fn(moment)))
            moment += step
        samples.append((end, severity_fn(end)))
        return tuple(samples)

    # ------------------------------------------------------------------
    # Scoring & filters
    # ------------------------------------------------------------------
    def _score_event(
        self,
        transiter: str,
        target: str | None,
        aspect: int | None,
        start: dt.datetime,
        end: dt.datetime,
        severity_fn,
    ) -> float:
        if end <= start:
            return 0.0
        step = dt.timedelta(hours=3)
        samples: list[tuple[dt.datetime, float]] = []
        moment = start
        while moment < end:
            samples.append((moment, severity_fn(moment)))
            moment += step
        samples.append((end, severity_fn(end)))
        area = 0.0
        for idx in range(1, len(samples)):
            prev_time, prev_val = samples[idx - 1]
            current_time, current_val = samples[idx]
            hours = (current_time - prev_time).total_seconds() / 3600.0
            area += 0.5 * (prev_val + current_val) * hours
        aspect_weight = ASPECT_WEIGHTS.get(
            ASPECT_FAMILY.get(aspect or 0, "neutral"), 1.0
        )
        transiter_weight = TRANSITER_WEIGHTS.get(transiter, 1.0)
        target_weight = TARGET_WEIGHTS.get(
            TARGET_FAMILY.get(target or "", "points"), 1.0
        )
        if aspect is None:
            aspect_weight = ASPECT_WEIGHTS.get("neutral", 0.95)
        if target is None:
            target_weight = 1.0
        raw_score = area * aspect_weight * transiter_weight * target_weight
        return raw_score / SCORE_NORMALIZER

    def _apply_filters(
        self, events: Sequence[Event], request: TimelineRequest
    ) -> list[Event]:
        filtered = [
            event for event in events if event.max_severity >= request.min_severity
        ]
        if request.top_k is not None and request.top_k >= 0:
            filtered.sort(key=lambda event: event.score, reverse=True)
            filtered = filtered[: request.top_k]
        else:
            filtered.sort(key=lambda event: event.exact_utc)
        return filtered

    def _summaries(self, events: Sequence[Event]) -> TimelineSummary:
        by_transiter: dict[str, int] = {}
        by_target: dict[str, int] = {}
        by_aspect: dict[str, int] = {}
        calendar: dict[str, float] = {}
        total_score = 0.0
        for event in events:
            by_transiter[event.transiter] = by_transiter.get(event.transiter, 0) + 1
            if event.target:
                by_target[event.target] = by_target.get(event.target, 0) + 1
            if event.aspect is not None:
                key = str(event.aspect)
                by_aspect[key] = by_aspect.get(key, 0) + 1
            total_score += event.score
            _update_calendar(calendar, event)
        return TimelineSummary(
            counts_by_transiter=dict(by_transiter),
            counts_by_target=dict(by_target),
            counts_by_aspect=dict(by_aspect),
            total_score=total_score,
            calendar=dict(calendar),
        )

    def _dedupe(self, events: Iterable[Event]) -> list[Event]:
        ordered = sorted(events, key=lambda e: e.exact_utc)
        merged: list[Event] = []
        last_for_key: dict[tuple[str, str, str | None, int | None], int] = {}
        for event in ordered:
            key = (event.type, event.transiter, event.target, event.aspect)
            index = last_for_key.get(key)
            if index is not None:
                existing = merged[index]
                delta = abs((event.exact_utc - existing.exact_utc).total_seconds())
                if delta <= _DEDUPE_WINDOW.total_seconds():
                    if event.max_severity > existing.max_severity:
                        merged[index] = event
                    continue
            merged.append(event)
            last_for_key[key] = len(merged) - 1
        return merged


# ----------------------------------------------------------------------
# Helper utilities
# ----------------------------------------------------------------------


def _ensure_utc(moment: dt.datetime) -> dt.datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=dt.timezone.utc)
    return moment.astimezone(dt.timezone.utc)


def _is_bracket(a: float, b: float) -> bool:
    if abs(a) <= _ORBITAL_ZERO_TOL or abs(b) <= _ORBITAL_ZERO_TOL:
        return True
    return (a < 0 <= b) or (b < 0 <= a)


def _aspect_delta(
    moving: float, target: float, aspect: int, axis: bool
) -> float:
    target_angle = norm360(target + aspect)
    diff = delta_angle(moving, target_angle)
    if axis:
        alt = norm360(target + 180.0 + aspect)
        diff_alt = delta_angle(moving, alt)
        if abs(diff_alt) < abs(diff):
            diff = diff_alt
    return diff


def _is_node_axis(name: str) -> bool:
    normalized = name.lower()
    return normalized in {"node", "north node", "true node", "mean node"}


def _effective_orb(transiter: str, aspect: int) -> float:
    base = BASE_ORBS.get(transiter, 0.0)
    cap = ASPECT_CAPS.get(aspect, base)
    return float(min(base, cap))


def _severity_from_delta(delta: float, orb: float) -> float:
    if orb <= 0:
        return 0.0
    ratio = min(1.0, abs(delta) / orb)
    return 0.5 * (1.0 + math.cos(math.pi * ratio))


def _update_calendar(storage: dict[str, float], event: Event) -> None:
    start = event.start_utc
    end = event.end_utc
    total_hours = max((end - start).total_seconds() / 3600.0, 1e-6)
    cursor = start
    while cursor < end:
        next_day = dt.datetime.combine(
            (cursor + dt.timedelta(days=1)).date(),
            dt.time.min,
            tzinfo=dt.timezone.utc,
        )
        segment_end = min(next_day, end)
        hours = (segment_end - cursor).total_seconds() / 3600.0
        date_key = cursor.date().isoformat()
        storage[date_key] = storage.get(date_key, 0.0) + event.score * (
            hours / total_hours
        )
        cursor = segment_end

