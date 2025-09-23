"""Astrological Age analytics built from Aries ingress ephemerides."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Sequence

try:  # pragma: no cover - optional dependency guard
    import swisseph as swe
except Exception:  # pragma: no cover - handled by _ensure_swisseph
    swe = None  # type: ignore

from ..detectors.common import body_lon, iso_to_jd, jd_to_iso, solve_zero_crossing
from ..ephemeris import SwissEphemerisAdapter
from ..ephemeris.sidereal import DEFAULT_SIDEREAL_AYANAMSHA, normalize_ayanamsha_name

ZODIAC_SIGNS: tuple[str, ...] = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)

__all__ = [
    "AgeSample",
    "AgeSeries",
    "AgeBoundary",
    "compute_age_series",
    "derive_age_boundaries",
]


@dataclass(frozen=True)
class AgeSample:
    """Computed astrological age metadata for a single Aries ingress."""

    year: int
    zodiac_sign: str
    ingress_ts: str
    ingress_jd: float
    ayanamsha_degrees: float
    sidereal_longitude: float
    ayanamsha_name: str


@dataclass(frozen=True)
class AgeSeries:
    """Collection of :class:`AgeSample` instances for a year range."""

    ayanamsha_name: str
    samples: tuple[AgeSample, ...]


@dataclass(frozen=True)
class AgeBoundary:
    """Boundary marker for the start of a new astrological age."""

    zodiac_sign: str
    start_year: int
    ingress_ts: str
    ingress_jd: float
    sidereal_longitude: float
    ayanamsha_name: str


def _ensure_swisseph() -> None:
    if swe is None:  # pragma: no cover - environment dependent
        raise ImportError("pyswisseph not installed; install astroengine[ephem] to compute ages")


def _available_ayanamshas() -> dict[str, int]:
    _ensure_swisseph()
    mapping = {key: value for key, value in SwissEphemerisAdapter._AYANAMSHA_MODES.items()}
    return mapping


def _resolve_ayanamsha(ayanamsha: str | None) -> tuple[str, int]:
    mapping = _available_ayanamshas()
    base = ayanamsha or SwissEphemerisAdapter._DEFAULT_AYANAMSHA or DEFAULT_SIDEREAL_AYANAMSHA
    normalized = normalize_ayanamsha_name(base)
    if normalized not in mapping:
        options = ", ".join(sorted(mapping))
        raise ValueError(f"Unsupported ayanamsha '{base}'. Supported options: {options}")
    return normalized, int(mapping[normalized])


def _default_ayanamsha_code() -> int:
    normalized, code = _resolve_ayanamsha(SwissEphemerisAdapter._DEFAULT_AYANAMSHA)
    return code


@contextmanager
def _sidereal_mode(code: int) -> Iterator[None]:
    _ensure_swisseph()
    restore_code = _default_ayanamsha_code()
    swe.set_sid_mode(code, 0.0, 0.0)
    try:
        yield
    finally:
        swe.set_sid_mode(restore_code, 0.0, 0.0)


def _sign_index(longitude: float) -> int:
    return int((longitude % 360.0) // 30.0)


def _aries_ingress(year: int, step_hours: float) -> tuple[str, float]:
    start_jd = iso_to_jd(f"{year}-01-01T00:00:00Z")
    end_jd = iso_to_jd(f"{year+1}-01-01T00:00:00Z")
    step_days = max(step_hours, 1.0) / 24.0

    prev_jd = start_jd
    prev_lon = body_lon(prev_jd, "sun")
    prev_sign = _sign_index(prev_lon)
    jd = prev_jd + step_days
    while jd <= end_jd:
        lon = body_lon(jd, "sun")
        sign = _sign_index(lon)
        if sign != prev_sign:
            if sign % 12 == 0:  # Aries ingress detected

                def fn(candidate_jd: float) -> float:
                    lon_candidate = body_lon(candidate_jd, "sun")
                    delta = (lon_candidate + 180.0) % 360.0 - 180.0
                    return delta

                refined = solve_zero_crossing(fn, prev_jd, jd, tol=1e-6, tol_deg=1e-5)
                return jd_to_iso(refined), refined
            prev_sign = sign
        prev_jd = jd
        jd += step_days
    raise ValueError(f"No Aries ingress found for {year}")


def compute_age_series(
    start_year: int,
    end_year: int,
    *,
    ayanamsha: str | None = None,
    step_hours: float = 6.0,
) -> AgeSeries:
    """Compute astrological age metadata for each year in ``start_year`` → ``end_year``."""

    if start_year > end_year:
        raise ValueError("start_year must be <= end_year")

    normalized, code = _resolve_ayanamsha(ayanamsha)
    samples: list[AgeSample] = []

    with _sidereal_mode(code):
        for year in range(start_year, end_year + 1):
            ingress_ts, ingress_jd = _aries_ingress(year, step_hours)
            ayanamsha_value = float(swe.get_ayanamsa_ut(ingress_jd))
            sidereal_longitude = (360.0 - ayanamsha_value) % 360.0
            index = int(sidereal_longitude // 30.0) % len(ZODIAC_SIGNS)
            sign = ZODIAC_SIGNS[index]
            samples.append(
                AgeSample(
                    year=year,
                    zodiac_sign=sign,
                    ingress_ts=ingress_ts,
                    ingress_jd=ingress_jd,
                    ayanamsha_degrees=ayanamsha_value,
                    sidereal_longitude=sidereal_longitude,
                    ayanamsha_name=normalized,
                )
            )

    return AgeSeries(ayanamsha_name=normalized, samples=tuple(samples))


def derive_age_boundaries(series: AgeSeries) -> Sequence[AgeBoundary]:
    """Return astrological age boundaries from ``series``."""

    boundaries: list[AgeBoundary] = []
    current_sign: str | None = None
    for sample in series.samples:
        if sample.zodiac_sign != current_sign:
            boundaries.append(
                AgeBoundary(
                    zodiac_sign=sample.zodiac_sign,
                    start_year=sample.year,
                    ingress_ts=sample.ingress_ts,
                    ingress_jd=sample.ingress_jd,
                    sidereal_longitude=sample.sidereal_longitude,
                    ayanamsha_name=series.ayanamsha_name,
                )
            )
            current_sign = sample.zodiac_sign
    return tuple(boundaries)

