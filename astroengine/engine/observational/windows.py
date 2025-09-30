"""Visibility window estimation and heliacal event helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import math
from typing import Callable, Iterable, Sequence

from ...ephemeris.adapter import EphemerisAdapter, ObserverLocation
from .events import rise_set_times
from .topocentric import (
    MetConditions,
    horizontal_from_equatorial,
    topocentric_equatorial,
)

try:  # pragma: no cover - optional Swiss Ephemeris dependency
    import swisseph as swe
except ModuleNotFoundError:  # pragma: no cover - fallback for tests without swe
    swe = None


_SUN_ID = getattr(swe, "SUN", 0)
_MOON_ID = getattr(swe, "MOON", 1)


@dataclass(frozen=True)
class VisibilityConstraints:
    """Thresholds used when constructing visibility windows."""

    min_altitude_deg: float = 0.0
    sun_altitude_max_deg: float | None = None
    sun_separation_min_deg: float | None = None
    moon_altitude_max_deg: float | None = None
    refraction: bool = True
    met: MetConditions = field(default_factory=MetConditions)
    horizon_dip_deg: float = 0.0
    step_seconds: int = 300
    sun_body: int = _SUN_ID
    moon_body: int = _MOON_ID


@dataclass(frozen=True)
class VisibilityWindow:
    """Describe a continuous interval that satisfies the supplied constraints."""

    start: datetime
    end: datetime
    max_altitude_deg: float
    max_altitude_time: datetime
    min_sun_separation_deg: float | None
    max_sun_separation_deg: float | None
    score: float
    details: dict[str, float | None]

    @property
    def duration_seconds(self) -> float:
        return (self.end - self.start).total_seconds()


@dataclass(frozen=True)
class HeliacalProfile:
    """Profile describing heliacal visibility thresholds."""

    mode: str = "rising"  # "rising" or "setting"
    min_object_altitude_deg: float = 5.0
    sun_altitude_max_deg: float = -10.0
    sun_separation_min_deg: float = 12.0
    max_airmass: float | None = None
    refraction: bool = True
    search_window_hours: float = 2.0


def visibility_windows(
    adapter: EphemerisAdapter,
    body: int,
    start: datetime,
    end: datetime,
    observer: ObserverLocation,
    constraints: VisibilityConstraints,
) -> list[VisibilityWindow]:
    """Return visibility windows for ``body`` over ``[start, end]``."""

    if start >= end:
        return []
    step = max(60, constraints.step_seconds)
    samples = _sample_track(adapter, body, start, end, observer, constraints, step)
    if not samples:
        return []
    evaluator = _ConstraintEvaluator(adapter, observer, constraints)
    return evaluator.extract_windows(samples)


@dataclass
class _Sample:
    time: datetime
    altitude_deg: float
    azimuth_deg: float
    sun_altitude_deg: float | None
    sun_separation_deg: float | None
    moon_altitude_deg: float | None


def _sample_track(
    adapter: EphemerisAdapter,
    body: int,
    start: datetime,
    end: datetime,
    observer: ObserverLocation,
    constraints: VisibilityConstraints,
    step_seconds: int,
) -> list[_Sample]:
    samples: list[_Sample] = []
    step = timedelta(seconds=step_seconds)
    moment = start.astimezone(UTC) if start.tzinfo else start.replace(tzinfo=UTC)
    finish = end.astimezone(UTC) if end.tzinfo else end.replace(tzinfo=UTC)
    evaluator = _ConstraintEvaluator(adapter, observer, constraints)
    while moment <= finish:
        alt, az, sun_alt, sun_sep, moon_alt = evaluator.state(moment, body)
        samples.append(
            _Sample(moment, alt, az, sun_alt, sun_sep, moon_alt)
        )
        moment += step
    return samples


class _ConstraintEvaluator:
    def __init__(
        self,
        adapter: EphemerisAdapter,
        observer: ObserverLocation,
        constraints: VisibilityConstraints,
    ) -> None:
        self.adapter = adapter
        self.observer = observer
        self.constraints = constraints

    def state(self, moment: datetime, body: int) -> tuple[float, float, float | None, float | None, float | None]:
        equ = topocentric_equatorial(self.adapter, body, moment, self.observer)
        horiz = horizontal_from_equatorial(
            equ.right_ascension_deg,
            equ.declination_deg,
            moment,
            self.observer,
            refraction=self.constraints.refraction,
            met=self.constraints.met,
            horizon_dip_deg=self.constraints.horizon_dip_deg,
        )
        sun_alt: float | None = None
        sun_sep: float | None = None
        if self.constraints.sun_altitude_max_deg is not None or self.constraints.sun_separation_min_deg is not None:
            sun_equ = topocentric_equatorial(
                self.adapter, self.constraints.sun_body, moment, self.observer
            )
            sun_horiz = horizontal_from_equatorial(
                sun_equ.right_ascension_deg,
                sun_equ.declination_deg,
                moment,
                self.observer,
                refraction=self.constraints.refraction,
                met=self.constraints.met,
                horizon_dip_deg=self.constraints.horizon_dip_deg,
            )
            sun_alt = sun_horiz.altitude_deg
            sun_sep = _angular_separation(
                equ.right_ascension_deg,
                equ.declination_deg,
                sun_equ.right_ascension_deg,
                sun_equ.declination_deg,
            )
        moon_alt: float | None = None
        if self.constraints.moon_altitude_max_deg is not None:
            moon_equ = topocentric_equatorial(
                self.adapter, self.constraints.moon_body, moment, self.observer
            )
            moon_horiz = horizontal_from_equatorial(
                moon_equ.right_ascension_deg,
                moon_equ.declination_deg,
                moment,
                self.observer,
                refraction=self.constraints.refraction,
                met=self.constraints.met,
                horizon_dip_deg=self.constraints.horizon_dip_deg,
            )
            moon_alt = moon_horiz.altitude_deg
        return (
            horiz.altitude_deg,
            horiz.azimuth_deg,
            sun_alt,
            sun_sep,
            moon_alt,
        )

    def check(self, sample: _Sample) -> bool:
        c = self.constraints
        if sample.altitude_deg < c.min_altitude_deg:
            return False
        if c.sun_altitude_max_deg is not None and (
            sample.sun_altitude_deg is None
            or sample.sun_altitude_deg > c.sun_altitude_max_deg
        ):
            return False
        if c.sun_separation_min_deg is not None and (
            sample.sun_separation_deg is None
            or sample.sun_separation_deg < c.sun_separation_min_deg
        ):
            return False
        if c.moon_altitude_max_deg is not None and (
            sample.moon_altitude_deg is None
            or sample.moon_altitude_deg > c.moon_altitude_max_deg
        ):
            return False
        return True

    def extract_windows(self, samples: Sequence[_Sample]) -> list[VisibilityWindow]:
        windows: list[VisibilityWindow] = []
        active: list[_Sample] = []
        prev_sample: _Sample | None = None
        for sample in samples:
            ok = self.check(sample)
            if ok:
                active.append(sample)
            else:
                if active:
                    window = self._finalize_window(active, prev_sample, sample)
                    if window is not None:
                        windows.append(window)
                    active = []
            prev_sample = sample
        if active:
            window = self._finalize_window(active, prev_sample, None)
            if window is not None:
                windows.append(window)
        windows.sort(key=lambda w: w.score, reverse=True)
        return windows

    def _finalize_window(
        self,
        active: Sequence[_Sample],
        prev_sample: _Sample | None,
        next_sample: _Sample | None,
    ) -> VisibilityWindow | None:
        if not active:
            return None
        start_sample = active[0]
        end_sample = active[-1]
        start = start_sample.time
        end = end_sample.time
        if prev_sample is not None:
            start = _refine_transition(prev_sample, start_sample, self.check)
        if next_sample is not None:
            end = _refine_transition(end_sample, next_sample, self.check)
        max_sample = max(active, key=lambda s: s.altitude_deg)
        score = _score_window(start, end, max_sample)
        sun_seps = [s.sun_separation_deg for s in active if s.sun_separation_deg is not None]
        sun_alts = [s.sun_altitude_deg for s in active if s.sun_altitude_deg is not None]
        min_sun_sep = min(sun_seps) if sun_seps else None
        max_sun_sep = max(sun_seps) if sun_seps else None
        min_sun_alt = min(sun_alts) if sun_alts else None
        max_sun_alt = max(sun_alts) if sun_alts else None
        details = {
            "max_altitude": max_sample.altitude_deg,
            "min_sun_separation": min_sun_sep,
            "max_sun_separation": max_sun_sep,
            "min_sun_altitude": min_sun_alt,
            "max_sun_altitude": max_sun_alt,
        }
        return VisibilityWindow(
            start=start,
            end=end,
            max_altitude_deg=max_sample.altitude_deg,
            max_altitude_time=max_sample.time,
            min_sun_separation_deg=min_sun_sep,
            max_sun_separation_deg=max_sun_sep,
            score=score,
            details=details,
        )


def _score_window(start: datetime, end: datetime, max_sample: _Sample) -> float:
    duration_hours = (end - start).total_seconds() / 3600.0
    return max_sample.altitude_deg + duration_hours * 2.0


def _refine_transition(
    before: _Sample,
    after: _Sample,
    predicate: Callable[[_Sample], bool],
) -> datetime:
    t0 = before.time
    t1 = after.time
    for _ in range(12):
        if (t1 - t0).total_seconds() <= 30:
            break
        mid = t0 + (t1 - t0) / 2
        mid_sample = _interpolate_sample(before, after, mid)
        if predicate(mid_sample):
            t1 = mid
            after = mid_sample
        else:
            t0 = mid
            before = mid_sample
    return t1


def _interpolate_sample(a: _Sample, b: _Sample, moment: datetime) -> _Sample:
    total = (b.time - a.time).total_seconds()
    if total <= 0:
        return a
    frac = (moment - a.time).total_seconds() / total
    return _Sample(
        moment,
        a.altitude_deg + (b.altitude_deg - a.altitude_deg) * frac,
        a.azimuth_deg + (b.azimuth_deg - a.azimuth_deg) * frac,
        _interp_optional(a.sun_altitude_deg, b.sun_altitude_deg, frac),
        _interp_optional(a.sun_separation_deg, b.sun_separation_deg, frac),
        _interp_optional(a.moon_altitude_deg, b.moon_altitude_deg, frac),
    )


def _interp_optional(a: float | None, b: float | None, frac: float) -> float | None:
    if a is None or b is None:
        return None
    return a + (b - a) * frac


def _angular_separation(ra1_deg: float, dec1_deg: float, ra2_deg: float, dec2_deg: float) -> float:
    ra1 = math.radians(ra1_deg)
    ra2 = math.radians(ra2_deg)
    dec1 = math.radians(dec1_deg)
    dec2 = math.radians(dec2_deg)
    cos_sep = (
        math.sin(dec1) * math.sin(dec2)
        + math.cos(dec1) * math.cos(dec2) * math.cos(ra1 - ra2)
    )
    cos_sep = max(-1.0, min(1.0, cos_sep))
    return math.degrees(math.acos(cos_sep))


def heliacal_candidates(
    adapter: EphemerisAdapter,
    body: int,
    date_range: tuple[datetime, datetime],
    observer: ObserverLocation,
    profile: HeliacalProfile,
) -> list[datetime]:
    """Return candidate heliacal visibility instants within ``date_range``."""

    start, end = date_range
    if start >= end:
        return []
    out: list[datetime] = []
    current = start
    step_day = timedelta(days=1)
    while current <= end:
        dawn_dusk = _heliacal_window(adapter, body, current, observer, profile)
        if dawn_dusk is not None:
            out.append(dawn_dusk)
        current += step_day
    return out


def _heliacal_window(
    adapter: EphemerisAdapter,
    body: int,
    date: datetime,
    observer: ObserverLocation,
    profile: HeliacalProfile,
) -> datetime | None:
    sun_events = rise_set_times(adapter, _SUN_ID, date, observer, h0_deg=-0.5667)
    sunrise, sunset = sun_events
    if profile.mode == "rising":
        reference = sunrise
        direction = -1
    else:
        reference = sunset
        direction = 1
    if reference is None:
        return None
    window_start = reference + timedelta(hours=direction * -profile.search_window_hours)
    window_end = reference + timedelta(hours=direction * profile.search_window_hours)
    if window_start > window_end:
        window_start, window_end = window_end, window_start
    step = timedelta(minutes=5)

    def passes(moment: datetime) -> bool:
        equ = topocentric_equatorial(adapter, body, moment, observer)
        horiz = horizontal_from_equatorial(
            equ.right_ascension_deg,
            equ.declination_deg,
            moment,
            observer,
            refraction=profile.refraction,
            met=MetConditions(),
        )
        sun_equ = topocentric_equatorial(adapter, _SUN_ID, moment, observer)
        sun_horiz = horizontal_from_equatorial(
            sun_equ.right_ascension_deg,
            sun_equ.declination_deg,
            moment,
            observer,
            refraction=profile.refraction,
            met=MetConditions(),
        )
        if horiz.altitude_deg < profile.min_object_altitude_deg:
            return False
        if sun_horiz.altitude_deg > profile.sun_altitude_max_deg:
            return False
        separation = _angular_separation(
            equ.right_ascension_deg,
            equ.declination_deg,
            sun_equ.right_ascension_deg,
            sun_equ.declination_deg,
        )
        if separation < profile.sun_separation_min_deg:
            return False
        if profile.max_airmass is not None:
            if _airmass(horiz.altitude_deg) > profile.max_airmass:
                return False
        return True

    moment = window_start
    last_result: datetime | None = None
    while moment <= window_end:
        if passes(moment):
            last_result = moment
            if profile.mode == "rising":
                return moment
        moment += step
    return last_result


def _airmass(altitude_deg: float) -> float:
    alt_rad = math.radians(max(0.1, altitude_deg))
    sin_alt = math.sin(alt_rad)
    if sin_alt <= 0:
        return float("inf")
    return 1.0 / sin_alt


__all__ = [
    "HeliacalProfile",
    "VisibilityConstraints",
    "VisibilityWindow",
    "heliacal_candidates",
    "visibility_windows",
]
