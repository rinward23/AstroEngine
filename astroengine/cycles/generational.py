"""Generational and mundane cycle analytics derived from Swiss Ephemeris."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from itertools import combinations
from typing import Mapping, Sequence

try:  # pragma: no cover - optional dependency guard
    import swisseph as swe
except Exception:  # pragma: no cover - handled by _ensure_swisseph
    swe = None  # type: ignore

from ..detectors.common import jd_to_iso
from ..ephemeris import SwissEphemerisAdapter

DEFAULT_OUTER_BODIES: Sequence[str] = ("Jupiter", "Saturn", "Uranus", "Neptune", "Pluto")

DEFAULT_OUTER_ASPECTS: Mapping[int, str] = {
    0: "conjunction",
    45: "semi-square",
    60: "sextile",
    90: "square",
    120: "trine",
    135: "sesquiquadrate",
    150: "quincunx",
    180: "opposition",
}

__all__ = [
    "DEFAULT_OUTER_ASPECTS",
    "DEFAULT_OUTER_BODIES",
    "CyclePairSample",
    "CycleTimeline",
    "WavePoint",
    "WaveSeries",
    "outer_cycle_timeline",
    "neptune_pluto_wave",
]


@dataclass(frozen=True)
class CyclePairSample:
    """Single observation for an outer-planet pair."""

    pair: tuple[str, str]
    timestamp: str
    julian_day: float
    separation: float
    signed_delta: float
    phase: str
    aspect: str | None
    aspect_orb: float | None


@dataclass(frozen=True)
class CycleTimeline:
    """Timeline of outer-cycle samples across a date range."""

    start_ts: str
    end_ts: str
    step_days: float
    samples: tuple[CyclePairSample, ...]


@dataclass(frozen=True)
class WavePoint:
    """Single point in a Neptune–Pluto wave analysis."""

    timestamp: str
    julian_day: float
    separation: float
    signed_delta: float
    phase: str
    aspect: str | None
    aspect_orb: float | None
    rate_deg_per_year: float | None


@dataclass(frozen=True)
class WaveSeries:
    """Ordered series of :class:`WavePoint` entries for a planet pair."""

    pair: tuple[str, str]
    step_days: float
    samples: tuple[WavePoint, ...]


def _ensure_swisseph() -> None:
    if swe is None:  # pragma: no cover - environment dependent
        raise ImportError("pyswisseph not installed; install astroengine[ephem] to enable cycles")


def _canonical_body(name: str) -> str:
    return name.strip().title()


def _resolve_body_codes(bodies: Sequence[str]) -> dict[str, int]:
    _ensure_swisseph()
    codes: dict[str, int] = {}
    for raw in bodies:
        canon = _canonical_body(raw)
        key = canon.lower()
        mapping = {
            "jupiter": swe.JUPITER,
            "saturn": swe.SATURN,
            "uranus": swe.URANUS,
            "neptune": swe.NEPTUNE,
            "pluto": swe.PLUTO,
        }
        if key not in mapping:
            raise ValueError(f"Unsupported outer planet '{raw}'")
        codes[canon] = int(mapping[key])
    return codes


def _iso(moment: datetime) -> str:
    return moment.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _signed_delta(a: float, b: float) -> float:
    delta = (b - a) % 360.0
    if delta > 180.0:
        delta -= 360.0
    return delta


def _classify_aspect(
    separation: float,
    aspects: Mapping[int, str],
    orb: float,
) -> tuple[str | None, float | None]:
    candidate: str | None = None
    diff_min: float | None = None
    for angle, name in aspects.items():
        diff = abs(separation - float(angle))
        if diff <= orb and (diff_min is None or diff < diff_min):
            candidate = name
            diff_min = diff
    return candidate, diff_min


def outer_cycle_timeline(
    start_year: int,
    end_year: int,
    *,
    bodies: Sequence[str] | None = None,
    step_days: float = 30.0,
    adapter: SwissEphemerisAdapter | None = None,
    aspect_angles: Mapping[int, str] | None = None,
    aspect_orb: float = 3.0,
) -> CycleTimeline:
    """Generate an outer-planet separation timeline suitable for dashboards."""

    if start_year > end_year:
        raise ValueError("start_year must be <= end_year")
    if step_days <= 0:
        raise ValueError("step_days must be positive")

    bodies = tuple(_canonical_body(name) for name in (bodies or DEFAULT_OUTER_BODIES))
    body_codes = _resolve_body_codes(bodies)
    adapter = adapter or SwissEphemerisAdapter()
    aspects = aspect_angles or DEFAULT_OUTER_ASPECTS

    start_dt = datetime(start_year, 1, 1, tzinfo=UTC)
    end_dt = datetime(end_year, 12, 31, tzinfo=UTC)

    samples: list[CyclePairSample] = []
    current = start_dt
    while current <= end_dt:
        jd = adapter.julian_day(current)
        positions = adapter.body_positions(jd, body_codes)
        timestamp = jd_to_iso(jd)
        for left, right in combinations(bodies, 2):
            lon_a = positions[left].longitude
            lon_b = positions[right].longitude
            delta_signed = _signed_delta(lon_a, lon_b)
            separation = abs(delta_signed)
            phase = "waxing" if delta_signed >= 0 else "waning"
            aspect_name, diff = _classify_aspect(separation, aspects, aspect_orb)
            samples.append(
                CyclePairSample(
                    pair=(left, right),
                    timestamp=timestamp,
                    julian_day=jd,
                    separation=separation,
                    signed_delta=delta_signed,
                    phase=phase,
                    aspect=aspect_name,
                    aspect_orb=diff,
                )
            )
        current += timedelta(days=step_days)

    return CycleTimeline(
        start_ts=_iso(start_dt),
        end_ts=_iso(end_dt),
        step_days=float(step_days),
        samples=tuple(samples),
    )


def _rate_deg_per_year(prev_delta: float, current_delta: float, delta_jd: float) -> float:
    diff = current_delta - prev_delta
    while diff > 180.0:
        diff -= 360.0
    while diff < -180.0:
        diff += 360.0
    years = delta_jd / 365.2425
    if years == 0:
        return 0.0
    return diff / years


def neptune_pluto_wave(
    start_year: int,
    end_year: int,
    *,
    step_days: float = 60.0,
    adapter: SwissEphemerisAdapter | None = None,
    aspect_angles: Mapping[int, str] | None = None,
    aspect_orb: float = 3.0,
) -> WaveSeries:
    """Return a Neptune–Pluto wave timeline with derivative metrics."""

    timeline = outer_cycle_timeline(
        start_year,
        end_year,
        bodies=("Neptune", "Pluto"),
        step_days=step_days,
        adapter=adapter,
        aspect_angles=aspect_angles,
        aspect_orb=aspect_orb,
    )
    wave_points: list[WavePoint] = []
    prev_delta: float | None = None
    prev_jd: float | None = None
    for sample in timeline.samples:
        if sample.pair != ("Neptune", "Pluto"):
            continue
        if prev_delta is None:
            rate = None
        else:
            assert prev_jd is not None
            rate = _rate_deg_per_year(prev_delta, sample.signed_delta, sample.julian_day - prev_jd)
        wave_points.append(
            WavePoint(
                timestamp=sample.timestamp,
                julian_day=sample.julian_day,
                separation=sample.separation,
                signed_delta=sample.signed_delta,
                phase=sample.phase,
                aspect=sample.aspect,
                aspect_orb=sample.aspect_orb,
                rate_deg_per_year=rate,
            )
        )
        prev_delta = sample.signed_delta
        prev_jd = sample.julian_day

    return WaveSeries(pair=("Neptune", "Pluto"), step_days=timeline.step_days, samples=tuple(wave_points))

