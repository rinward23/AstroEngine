"""Fixed star paran and heliacal phase analytics backed by Skyfield."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, date as date_cls, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Iterable, Iterator, Mapping, Sequence

from ..chart.natal import ChartLocation
from ..detectors.common import iso_to_jd
from ..infrastructure.paths import datasets_dir

try:  # pragma: no cover - optional dependency
    from skyfield.api import Star, load, wgs84
except Exception:  # pragma: no cover - handled via HAS_SKYFIELD flag
    Star = None  # type: ignore
    load = None  # type: ignore
    wgs84 = None  # type: ignore


DATASET = datasets_dir() / "star_names_iau.csv"

_PLANET_KERNEL_KEYS: Mapping[str, str] = {
    "sun": "sun",
    "moon": "moon",
    "mercury": "mercury",
    "venus": "venus",
    "mars": "mars",
    "jupiter": "jupiter barycenter",
    "saturn": "saturn barycenter",
    "uranus": "uranus barycenter",
    "neptune": "neptune barycenter",
    "pluto": "pluto barycenter",
}

_ANGLE_CODES = {
    "rising": "ASC",
    "culminating": "MC",
    "setting": "DESC",
    "anti_culminating": "IC",
}

HAS_SKYFIELD = Star is not None and load is not None and wgs84 is not None

__all__ = [
    "HAS_SKYFIELD",
    "ParanEvent",
    "HeliacalPhase",
    "compute_star_parans",
    "compute_heliacal_phases",
]


@dataclass(frozen=True)
class HorizonEvent:
    """Angular crossing for a target relative to the local horizon."""

    target: str
    kind: str
    timestamp: datetime
    altitude: float
    azimuth: float


@dataclass(frozen=True)
class ParanEvent:
    """Moment when a fixed star and planet share simultaneous angularity."""

    star: str
    body: str
    star_angle: str
    body_angle: str
    midpoint_ts: str
    julian_day: float
    delta_minutes: float
    star_event: HorizonEvent
    body_event: HorizonEvent


@dataclass(frozen=True)
class HeliacalPhase:
    """Visibility estimate for a heliacal rising or setting."""

    star: str
    phase: str
    timestamp: str
    julian_day: float
    star_altitude: float
    sun_altitude: float
    sun_star_separation: float
    metadata: Mapping[str, object]


class _ObserverContext:
    """Reusable Skyfield objects for horizon calculations."""

    def __init__(self, location: ChartLocation) -> None:
        if not HAS_SKYFIELD:  # pragma: no cover - exercised in ImportError tests
            raise ImportError("skyfield/jplephem not installed")
        self.kernel = _load_kernel()
        self.loader = load
        self.ts = load.timescale()
        self.earth = self.kernel["earth"]
        self.location = location
        self.observer = self.earth + wgs84.latlon(location.latitude, location.longitude)

    def time_from_datetime(self, moment: datetime):
        return self.ts.from_datetime(moment)


def _normalize_day(moment: datetime | date_cls | str) -> datetime:
    if isinstance(moment, datetime):
        dt_utc = moment.astimezone(timezone.utc)
    elif isinstance(moment, date_cls):
        dt_utc = datetime.combine(moment, time(0, 0, tzinfo=timezone.utc))
    else:
        parsed = datetime.fromisoformat(str(moment).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        dt_utc = parsed.astimezone(timezone.utc)
    return dt_utc.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=UTC)


def _load_kernel():
    assert load is not None
    for name in ("de440s.bsp", "de421.bsp", "de430t.bsp"):
        path = Path(name)
        try:
            return load(str(path))
        except Exception:
            continue
    raise FileNotFoundError("No local JPL kernel found (expected de440s.bsp)")


def _lookup_ra_dec(name: str) -> tuple[float, float]:
    if not DATASET.exists():  # pragma: no cover - dataset guaranteed in repo
        raise FileNotFoundError(f"Fixed star dataset missing: {DATASET}")
    needle = name.strip().lower()
    with open(DATASET, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row["name"].strip().lower() == needle:
                return float(row["ra_deg"]), float(row["dec_deg"])
    raise KeyError(f"Star not found in dataset: {name}")


def _build_star(name: str) -> Star:
    if not HAS_SKYFIELD:  # pragma: no cover - exercised in ImportError tests
        raise ImportError("skyfield/jplephem not installed")
    ra_deg, dec_deg = _lookup_ra_dec(name)
    return Star(ra_hours=ra_deg / 15.0, dec_degrees=dec_deg)


def _format_iso(moment: datetime) -> str:
    return moment.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sample_range(day_start: datetime, *, minutes: int) -> Iterator[datetime]:
    step = timedelta(minutes=minutes)
    current = day_start
    end = day_start + timedelta(days=1)
    while current <= end:
        yield current
        current += step


def _alt_az(ctx: _ObserverContext, target: Star | str, moment: datetime) -> tuple[float, float]:
    time_obj = ctx.time_from_datetime(moment)
    if isinstance(target, Star):
        astrometric = ctx.observer.at(time_obj).observe(target)
    else:
        body = ctx.kernel.get(target)
        if body is None:
            raise KeyError(f"Kernel body not available: {target}")
        astrometric = ctx.observer.at(time_obj).observe(body)
    alt, az, _ = astrometric.apparent().altaz()
    return float(alt.degrees), float(az.degrees % 360.0)


def _generate_samples(
    ctx: _ObserverContext,
    target: Star | str,
    name: str,
    day_start: datetime,
    *,
    minutes: int,
) -> list[HorizonEvent]:
    samples: list[tuple[datetime, float, float]] = []
    for moment in _sample_range(day_start, minutes=minutes):
        altitude, azimuth = _alt_az(ctx, target, moment)
        samples.append((moment, altitude, azimuth))

    events: list[HorizonEvent] = []
    for idx in range(1, len(samples)):
        prev_t, prev_alt, prev_az = samples[idx - 1]
        curr_t, curr_alt, curr_az = samples[idx]
        if prev_alt <= 0.0 < curr_alt:
            when = _bisect_altitude(ctx, target, prev_t, curr_t)
            alt, az = _alt_az(ctx, target, when)
            events.append(HorizonEvent(target=name, kind="rising", timestamp=when, altitude=alt, azimuth=az))
        elif prev_alt >= 0.0 > curr_alt:
            when = _bisect_altitude(ctx, target, prev_t, curr_t)
            alt, az = _alt_az(ctx, target, when)
            events.append(HorizonEvent(target=name, kind="setting", timestamp=when, altitude=alt, azimuth=az))

    for idx in range(1, len(samples) - 1):
        prev_t, prev_alt, _ = samples[idx - 1]
        curr_t, curr_alt, _ = samples[idx]
        next_t, next_alt, _ = samples[idx + 1]
        if curr_alt > prev_alt and curr_alt > next_alt:
            when = _refine_extremum(ctx, target, prev_t, curr_t, next_t)
            alt, az = _alt_az(ctx, target, when)
            events.append(
                HorizonEvent(target=name, kind="culminating", timestamp=when, altitude=alt, azimuth=az)
            )
        elif curr_alt < prev_alt and curr_alt < next_alt:
            when = _refine_extremum(ctx, target, prev_t, curr_t, next_t)
            alt, az = _alt_az(ctx, target, when)
            events.append(
                HorizonEvent(
                    target=name,
                    kind="anti_culminating",
                    timestamp=when,
                    altitude=alt,
                    azimuth=az,
                )
            )

    events.sort(key=lambda evt: evt.timestamp)
    return events


def _bisect_altitude(
    ctx: _ObserverContext,
    target: Star | str,
    start: datetime,
    end: datetime,
    *,
    max_iter: int = 18,
) -> datetime:
    low = start
    high = end
    low_alt, _ = _alt_az(ctx, target, low)
    high_alt, _ = _alt_az(ctx, target, high)
    for _ in range(max_iter):
        mid = low + (high - low) / 2
        mid_alt, _ = _alt_az(ctx, target, mid)
        if abs(mid_alt) < 1e-4 or (high - low) <= timedelta(seconds=5):
            return mid
        if low_alt * mid_alt <= 0:
            high = mid
            high_alt = mid_alt
        else:
            low = mid
            low_alt = mid_alt
    return low + (high - low) / 2


def _refine_extremum(
    ctx: _ObserverContext,
    target: Star | str,
    before: datetime,
    center: datetime,
    after: datetime,
) -> datetime:
    step_seconds = (after - center).total_seconds()
    if step_seconds == 0:
        return center
    alt_before, _ = _alt_az(ctx, target, before)
    alt_center, _ = _alt_az(ctx, target, center)
    alt_after, _ = _alt_az(ctx, target, after)
    denom = (alt_before - 2.0 * alt_center + alt_after)
    if abs(denom) < 1e-6:
        return center
    offset = 0.5 * (alt_before - alt_after) / denom
    offset = max(min(offset, 1.0), -1.0)
    delta_seconds = offset * step_seconds
    moment = center + timedelta(seconds=delta_seconds)
    return moment


def _match_parans(
    star: str,
    body: str,
    star_events: Sequence[HorizonEvent],
    body_events: Sequence[HorizonEvent],
    *,
    threshold_minutes: float,
) -> list[ParanEvent]:
    matches: list[ParanEvent] = []
    for star_evt in star_events:
        for body_evt in body_events:
            delta = abs((star_evt.timestamp - body_evt.timestamp).total_seconds()) / 60.0
            if delta <= threshold_minutes:
                midpoint = star_evt.timestamp + (body_evt.timestamp - star_evt.timestamp) / 2
                midpoint_iso = _format_iso(midpoint)
                matches.append(
                    ParanEvent(
                        star=star,
                        body=body,
                        star_angle=_ANGLE_CODES.get(star_evt.kind, star_evt.kind),
                        body_angle=_ANGLE_CODES.get(body_evt.kind, body_evt.kind),
                        midpoint_ts=midpoint_iso,
                        julian_day=iso_to_jd(midpoint_iso),
                        delta_minutes=delta,
                        star_event=star_evt,
                        body_event=body_evt,
                    )
                )
    matches.sort(key=lambda evt: evt.delta_minutes)
    return matches


def compute_star_parans(
    star: str,
    day: datetime | date_cls | str,
    location: ChartLocation,
    *,
    bodies: Iterable[str] | None = None,
    step_minutes: int = 4,
    threshold_minutes: float = 12.0,
) -> list[ParanEvent]:
    """Return fixed star parans for ``star`` on ``day`` at ``location``."""

    ctx = _ObserverContext(location)
    star_obj = _build_star(star)
    day_start = _normalize_day(day)
    star_events = _generate_samples(ctx, star_obj, star, day_start, minutes=step_minutes)
    bodies = tuple(bodies or _PLANET_KERNEL_KEYS.keys())
    matches: list[ParanEvent] = []
    for body in bodies:
        key = _PLANET_KERNEL_KEYS.get(body.lower())
        if not key:
            continue
        body_events = _generate_samples(ctx, key, body, day_start, minutes=step_minutes)
        matches.extend(_match_parans(star, body, star_events, body_events, threshold_minutes=threshold_minutes))
    matches.sort(key=lambda evt: (evt.midpoint_ts, evt.delta_minutes))
    return matches


def compute_heliacal_phases(
    star: str,
    day: datetime | date_cls | str,
    location: ChartLocation,
    *,
    altitude_threshold: float = 1.5,
    sun_altitude_limit: float = -8.0,
    step_minutes: int = 4,
) -> list[HeliacalPhase]:
    """Estimate heliacal rising and setting for ``star`` at ``location``."""

    ctx = _ObserverContext(location)
    star_obj = _build_star(star)
    day_start = _normalize_day(day)
    star_events = _generate_samples(ctx, star_obj, star, day_start, minutes=step_minutes)
    sun_events = _generate_samples(ctx, "sun", "sun", day_start, minutes=step_minutes)

    phases: list[HeliacalPhase] = []
    for star_evt in star_events:
        if star_evt.kind == "rising":
            sunrise = _next_event(sun_events, "rising", star_evt.timestamp)
            if sunrise is None:
                continue
            visibility = _scan_visibility(
                ctx,
                star_obj,
                "sun",
                start=star_evt.timestamp,
                end=sunrise.timestamp,
                altitude_threshold=altitude_threshold,
                sun_altitude_limit=sun_altitude_limit,
            )
            if visibility is None:
                continue
            sun_alt, _ = _alt_az(ctx, "sun", visibility)
            star_alt, star_az = _alt_az(ctx, star_obj, visibility)
            separation = _separation(ctx, star_obj, "sun", visibility)
            visibility_iso = _format_iso(visibility)
            phases.append(
                HeliacalPhase(
                    star=star,
                    phase="heliacal_rising",
                    timestamp=visibility_iso,
                    julian_day=iso_to_jd(visibility_iso),
                    star_altitude=star_alt,
                    sun_altitude=sun_alt,
                    sun_star_separation=separation,
                    metadata={
                        "sunrise": _format_iso(sunrise.timestamp),
                        "star_azimuth": star_az,
                    },
                )
            )
        elif star_evt.kind == "setting":
            sunset = _previous_event(sun_events, "setting", star_evt.timestamp)
            if sunset is None:
                continue
            visibility = _scan_visibility(
                ctx,
                star_obj,
                "sun",
                start=sunset.timestamp,
                end=star_evt.timestamp,
                altitude_threshold=altitude_threshold,
                sun_altitude_limit=sun_altitude_limit,
            )
            if visibility is None:
                continue
            sun_alt, _ = _alt_az(ctx, "sun", visibility)
            star_alt, star_az = _alt_az(ctx, star_obj, visibility)
            separation = _separation(ctx, star_obj, "sun", visibility)
            visibility_iso = _format_iso(visibility)
            phases.append(
                HeliacalPhase(
                    star=star,
                    phase="heliacal_setting",
                    timestamp=visibility_iso,
                    julian_day=iso_to_jd(visibility_iso),
                    star_altitude=star_alt,
                    sun_altitude=sun_alt,
                    sun_star_separation=separation,
                    metadata={
                        "sunset": _format_iso(sunset.timestamp),
                        "star_azimuth": star_az,
                    },
                )
            )

    phases.sort(key=lambda phase: phase.timestamp)
    return phases


def _scan_visibility(
    ctx: _ObserverContext,
    star_target: Star,
    sun_key: str,
    *,
    start: datetime,
    end: datetime,
    altitude_threshold: float,
    sun_altitude_limit: float,
) -> datetime | None:
    step = timedelta(minutes=1)
    current = start
    best: datetime | None = None
    while current <= end:
        star_alt, _ = _alt_az(ctx, star_target, current)
        sun_alt, _ = _alt_az(ctx, sun_key, current)
        if star_alt >= altitude_threshold and sun_alt <= sun_altitude_limit:
            best = current
        current += step
    return best


def _next_event(events: Sequence[HorizonEvent], kind: str, moment: datetime) -> HorizonEvent | None:
    for event in events:
        if event.kind == kind and event.timestamp >= moment:
            return event
    return None


def _previous_event(events: Sequence[HorizonEvent], kind: str, moment: datetime) -> HorizonEvent | None:
    for event in reversed(events):
        if event.kind == kind and event.timestamp <= moment:
            return event
    return None


def _separation(
    ctx: _ObserverContext,
    star_target: Star,
    sun_key: str,
    moment: datetime,
) -> float:
    time_obj = ctx.time_from_datetime(moment)
    star_position = ctx.earth.at(time_obj).observe(star_target).apparent()
    sun_position = ctx.earth.at(time_obj).observe(ctx.kernel[sun_key]).apparent()
    return float(star_position.separation_from(sun_position).degrees)

