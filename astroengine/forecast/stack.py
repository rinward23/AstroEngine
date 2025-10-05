"""Compose forecast events across transit, progression, and direction techniques."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Iterable, Mapping, Sequence

from ..chart import NatalChart, TransitScanner
from ..chart.natal import DEFAULT_BODIES
from ..config.settings import Settings
from ..core.transit_engine import scan_transits
from ..detectors.directed_aspects import solar_arc_natal_aspects
from ..detectors.progressed_aspects import progressed_natal_aspects
from ..detectors_aspects import AspectHit

__all__ = [
    "ForecastEvent",
    "ForecastWindow",
    "ForecastChart",
    "build_forecast_stack",
]


@dataclass(frozen=True)
class ForecastEvent:
    """Normalised forecast event spanning a start/end window."""

    start: datetime
    end: datetime
    body: str
    aspect: str
    target: str
    exactness: float
    technique: str


@dataclass(frozen=True)
class ForecastWindow:
    """Inclusive window limiting forecast aggregation."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        start = _normalize_datetime(self.start)
        end = _normalize_datetime(self.end)
        object.__setattr__(self, "start", start)
        object.__setattr__(self, "end", end)
        if end <= start:
            raise ValueError("ForecastWindow end must be after start")


@dataclass(frozen=True)
class ForecastChart:
    """Container linking a natal chart with a forecast window."""

    natal_chart: NatalChart
    window: ForecastWindow


_ASPECT_LABELS: Mapping[int, str] = {
    0: "conjunction",
    60: "sextile",
    90: "square",
    120: "trine",
    150: "quincunx",
    180: "opposition",
}


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _isoformat(value: datetime) -> str:
    return _normalize_datetime(value).isoformat().replace("+00:00", "Z")


def _aspect_name(angle: float) -> str:
    rounded = int(round(angle))
    return _ASPECT_LABELS.get(rounded % 360, f"{angle:g}°")


def _chunk_window(window: ForecastWindow, max_days: float | None) -> list[tuple[datetime, datetime]]:
    if max_days is None or max_days <= 0:
        return [(window.start, window.end)]
    chunk = timedelta(days=max_days)
    if chunk <= timedelta(0):
        return [(window.start, window.end)]
    segments: list[tuple[datetime, datetime]] = []
    cursor = window.start
    while cursor < window.end:
        segment_end = min(window.end, cursor + chunk)
        segments.append((cursor, segment_end))
        if segment_end >= window.end:
            break
        cursor = segment_end
    return segments


def _resolve_transit_aspects(settings: Settings) -> list[str]:
    enabled = []
    sets = settings.aspects.sets
    if sets.get("ptolemaic", True):
        enabled.extend(["conjunction", "sextile", "square", "trine", "opposition"])
    if sets.get("minor", True):
        enabled.append("quincunx")
    return enabled or ["conjunction", "sextile", "square", "trine", "opposition"]


def _resolve_progression_angles(settings: Settings) -> Sequence[int]:
    base: list[int] = [0, 60, 90, 120, 180]
    if settings.aspects.sets.get("minor", True):
        base.append(150)
    return tuple(sorted(set(base)))


def _clamp_window(
    moment: datetime, window: ForecastWindow, *, span_hours: float
) -> tuple[datetime, datetime]:
    if span_hours <= 0.0:
        clipped = min(max(moment, window.start), window.end)
        return clipped, clipped
    delta = timedelta(hours=span_hours)
    start = max(window.start, moment - delta)
    end = min(window.end, moment + delta)
    if end < start:
        clipped = min(max(moment, window.start), window.end)
        return clipped, clipped
    return start, end


def _speed_hours(speed_deg_per_day: float | None, orb_allow: float) -> float:
    if speed_deg_per_day is None or abs(speed_deg_per_day) < 1e-6:
        return 0.0
    return (orb_allow / abs(speed_deg_per_day)) * 24.0


def _transit_window(
    scanner: TransitScanner,
    natal_chart: NatalChart,
    hit: AspectHit,
    *,
    window: ForecastWindow,
) -> tuple[datetime, datetime]:
    center = datetime.fromisoformat(hit.when_iso.replace("Z", "+00:00")).astimezone(UTC)
    contacts = scanner.scan(natal_chart, center)
    angle = int(round(float(hit.angle_deg)))
    for contact in contacts:
        if (
            contact.transiting_body.lower() == hit.moving.lower()
            and contact.natal_body.lower() == hit.target.lower()
            and contact.angle == angle
        ):
            start_dt = contact.ingress.astimezone(UTC) if contact.ingress else center
            end_dt = contact.egress.astimezone(UTC) if contact.egress else center
            if end_dt < start_dt:
                start_dt, end_dt = end_dt, start_dt
            start_dt = max(start_dt, window.start)
            end_dt = min(end_dt, window.end)
            return start_dt, end_dt
    code = DEFAULT_BODIES.get(hit.moving)
    if code is not None:
        moment = center
        adapter = scanner.adapter
        jd = adapter.julian_day(moment)
        sample = adapter.body_position(jd, code, body_name=hit.moving)
        speed = float(sample.speed_longitude)
    else:
        speed = 0.0
    span_hours = _speed_hours(speed, float(hit.orb_allow))
    return _clamp_window(center, window, span_hours=span_hours)


def _progression_window(
    hit: AspectHit,
    *,
    window: ForecastWindow,
) -> tuple[datetime, datetime]:
    center = datetime.fromisoformat(hit.when_iso.replace("Z", "+00:00")).astimezone(UTC)
    speed = float(getattr(hit, "speed_deg_per_day", 0.0) or 0.0)
    span_hours = _speed_hours(speed, float(hit.orb_allow))
    return _clamp_window(center, window, span_hours=span_hours)


def _transit_events(
    settings: Settings,
    chart: ForecastChart,
    *,
    natal_iso: str,
    start_iso: str,
    end_iso: str,
) -> Iterable[ForecastEvent]:
    aspects = _resolve_transit_aspects(settings)
    if not aspects:
        return []
    orb_allow = float(settings.aspects.orbs_global)
    perf_cfg = getattr(settings, "perf", None)
    raw_max_days = getattr(perf_cfg, "max_scan_days", None) if perf_cfg is not None else None
    try:
        max_days = float(raw_max_days) if raw_max_days is not None else None
    except (TypeError, ValueError):
        max_days = None
    if max_days is not None and max_days <= 0:
        max_days = None

    raw_workers = getattr(perf_cfg, "workers", 1) if perf_cfg is not None else 1
    try:
        worker_count = int(raw_workers)
    except (TypeError, ValueError):
        worker_count = 1

    chunks = _chunk_window(chart.window, max_days)

    def _scan_chunk(bounds: tuple[datetime, datetime]) -> list[AspectHit]:
        chunk_start, chunk_end = bounds
        return scan_transits(
            natal_ts=natal_iso,
            start_ts=_isoformat(chunk_start),
            end_ts=_isoformat(chunk_end),
            aspects=aspects,
            orb_deg=orb_allow,
            bodies=None,
            targets=None,
            step_days=1.0,
        )

    hits: list[AspectHit] = []
    if worker_count > 1 and len(chunks) > 1:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [executor.submit(_scan_chunk, bounds) for bounds in chunks]
            for future in futures:
                hits.extend(future.result())
    else:
        for bounds in chunks:
            hits.extend(_scan_chunk(bounds))

    hits.sort(key=lambda item: getattr(item, "when_iso", ""))
    scanner = TransitScanner()
    events: list[ForecastEvent] = []
    for hit in hits:
        start_dt, end_dt = _transit_window(scanner, chart.natal_chart, hit, window=chart.window)
        events.append(
            ForecastEvent(
                start=start_dt,
                end=end_dt,
                body=hit.moving,
                aspect=_aspect_name(float(hit.angle_deg)),
                target=hit.target,
                exactness=float(hit.orb_abs),
                technique="transits",
            )
        )
    return events


def _progression_events(
    settings: Settings,
    *,
    natal_iso: str,
    start_iso: str,
    end_iso: str,
    window: ForecastWindow,
    technique: str,
    resolver,
    aspects: Sequence[int],
) -> Iterable[ForecastEvent]:
    if not aspects:
        return []
    orb_allow = float(settings.aspects.orbs_global)
    hits = resolver(
        natal_ts=natal_iso,
        start_ts=start_iso,
        end_ts=end_iso,
        aspects=aspects,
        orb_deg=orb_allow,
        bodies=None,
        step_days=1.0,
    )
    events: list[ForecastEvent] = []
    for hit in hits:
        start_dt, end_dt = _progression_window(hit, window=window)
        events.append(
            ForecastEvent(
                start=start_dt,
                end=end_dt,
                body=hit.moving,
                aspect=_aspect_name(float(hit.angle_deg)),
                target=hit.target,
                exactness=float(hit.orb_abs),
                technique=technique,
            )
        )
    return events


def _filter_components(settings: Settings) -> Mapping[str, bool]:
    components = getattr(settings, "forecast_stack", None)
    if components is None:
        return {"transits": True, "progressions": True, "solar_arc": True}
    enabled = dict(getattr(components, "components", {}) or {})
    defaulted = {
        "transits": True,
        "progressions": True,
        "solar_arc": True,
    }
    defaulted.update((key, bool(val)) for key, val in enabled.items())
    return defaulted


def build_forecast_stack(settings: Settings, chart: ForecastChart) -> list[dict[str, object]]:
    """Return a merged list of forecast events for ``chart`` respecting ``settings``."""

    natal_iso = _isoformat(chart.natal_chart.moment)
    start_iso = _isoformat(chart.window.start)
    end_iso = _isoformat(chart.window.end)

    enabled = _filter_components(settings)

    events: list[ForecastEvent] = []
    if enabled.get("transits", True):
        events.extend(
            _transit_events(settings, chart, natal_iso=natal_iso, start_iso=start_iso, end_iso=end_iso)
        )

    angles = _resolve_progression_angles(settings)
    if enabled.get("progressions", True):
        events.extend(
            _progression_events(
                settings,
                natal_iso=natal_iso,
                start_iso=start_iso,
                end_iso=end_iso,
                window=chart.window,
                technique="progressions",
                resolver=progressed_natal_aspects,
                aspects=angles,
            )
        )

    if enabled.get("solar_arc", True):
        events.extend(
            _progression_events(
                settings,
                natal_iso=natal_iso,
                start_iso=start_iso,
                end_iso=end_iso,
                window=chart.window,
                technique="solar_arc",
                resolver=solar_arc_natal_aspects,
                aspects=angles,
            )
        )

    dedup: dict[tuple[str, str, str, str, str, str], ForecastEvent] = {}
    for event in events:
        key = (
            event.technique,
            event.body.lower(),
            event.target.lower(),
            event.aspect.lower(),
            _isoformat(event.start),
            _isoformat(event.end),
        )
        existing = dedup.get(key)
        if existing is None or event.exactness < existing.exactness - 1e-6:
            dedup[key] = event

    ordered = sorted(
        dedup.values(),
        key=lambda item: (
            _isoformat(item.start),
            item.technique,
            item.body.lower(),
            item.target.lower(),
            item.aspect.lower(),
        ),
    )

    return [
        {
            "start": _isoformat(event.start),
            "end": _isoformat(event.end),
            "body": event.body,
            "aspect": event.aspect,
            "target": event.target,
            "exactness": float(event.exactness),
            "technique": event.technique,
        }
        for event in ordered
    ]
