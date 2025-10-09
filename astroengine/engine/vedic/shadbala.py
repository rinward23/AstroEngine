"""Classical Śaḍbala strength metrics for Jyotiṣa workflows.

The implementation focuses on reproducible, data-backed calculations.  Only
components that can be derived directly from the available Swiss Ephemeris
positions are evaluated – chiefly Uccha Bala, Kendra Bala, Dig Bala,
Naisargika Bala, and a velocity-based Cheshta Bala.  Additional factors such as
Saptavargaja, Kala, and Drik balas require divisional charts, sunrise timings,
and nuanced aspect modelling; those hooks are represented in the public API as
missing components so that downstream callers can detect the gap without
receiving fabricated values.

The formulas and constants follow the conventions outlined in standard
Jyotiṣa texts (e.g. *Bṛhat Parāśara Horā Śāstra* and *Saravali*).  Each score is
bounded by the canonical sixty-point maximum used in classical tables.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from math import isnan

from ...detectors.common import delta_deg, norm360
from .chart import VedicChartContext

__all__ = [
    "ShadbalaFactor",
    "ShadbalaScore",
    "ShadbalaReport",
    "compute_shadbala",
]


SUPPORTED_PLANETS: tuple[str, ...] = (
    "Sun",
    "Moon",
    "Mars",
    "Mercury",
    "Jupiter",
    "Venus",
    "Saturn",
)


# Exaltation degrees measured from 0° Aries.
EXALTATION_DEGREES: Mapping[str, float] = {
    "Sun": 10.0,
    "Moon": 33.0,
    "Mars": 298.0,
    "Mercury": 165.0,
    "Jupiter": 95.0,
    "Venus": 357.0,
    "Saturn": 200.0,
}


NAISARGIKA_BALA: Mapping[str, float] = {
    "Sun": 60.0,
    "Moon": 51.0,
    "Venus": 43.0,
    "Jupiter": 34.0,
    "Mercury": 26.0,
    "Mars": 17.0,
    "Saturn": 9.0,
}


DIG_BALA_IDEAL_HOUSE: Mapping[str, int] = {
    "Sun": 10,
    "Mars": 10,
    "Moon": 4,
    "Venus": 4,
    "Mercury": 1,
    "Jupiter": 1,
    "Saturn": 7,
}


CHESHTA_SPEED_BOUNDS: Mapping[str, tuple[float, float]] = {
    "Sun": (0.956, 1.017),
    "Moon": (11.0, 15.5),
    "Mars": (-0.82, 0.82),
    "Mercury": (-1.6, 1.6),
    "Jupiter": (-0.1, 0.17),
    "Venus": (-1.2, 1.3),
    "Saturn": (-0.09, 0.1),
}


MISSING_COMPONENTS: tuple[str, ...] = (
    "saptavargaja_bala",
    "kalabala",
    "drik_bala",
)


@dataclass(frozen=True)
class ShadbalaFactor:
    """Individual strength contribution for a single factor."""

    name: str
    value: float
    maximum: float
    description: str

    def __post_init__(self) -> None:
        if self.value < 0.0:
            object.__setattr__(self, "value", 0.0)
        if self.value > self.maximum:
            object.__setattr__(self, "value", float(self.maximum))


@dataclass(frozen=True)
class ShadbalaScore:
    """Aggregated Śaḍbala strength for a planet."""

    planet: str
    factors: Mapping[str, ShadbalaFactor]
    missing: tuple[str, ...]

    @property
    def total(self) -> float:
        return sum(factor.value for factor in self.factors.values())


@dataclass(frozen=True)
class ShadbalaReport:
    """Container for per-planet Śaḍbala results."""

    scores: Mapping[str, ShadbalaScore]

    def score_for(self, planet: str) -> ShadbalaScore | None:
        return self.scores.get(planet)


def _house_index(longitude: float, cusps: Iterable[float]) -> int:
    values = [norm360(value) for value in cusps]
    lon = norm360(longitude)
    for idx in range(12):
        start = values[idx]
        end = values[(idx + 1) % 12]
        if start <= end:
            if start <= lon < end:
                return idx + 1
        else:
            if lon >= start or lon < end:
                return idx + 1
    return 12


def _uccha_bala(planet: str, longitude: float) -> float:
    exaltation = EXALTATION_DEGREES.get(planet)
    if exaltation is None:
        return 0.0
    delta = abs(delta_deg(longitude, exaltation))
    normalized = max(0.0, 1.0 - (delta / 180.0))
    return 60.0 * normalized


def _kendra_bala(house_index: int) -> float:
    if house_index in {1, 4, 7, 10}:
        return 60.0
    if house_index in {2, 5, 8, 11}:
        return 45.0
    return 30.0


def _dig_bala(planet: str, longitude: float, cusps: Iterable[float]) -> float:
    ideal_house = DIG_BALA_IDEAL_HOUSE.get(planet)
    if ideal_house is None:
        return 0.0
    cusp_values = [norm360(value) for value in cusps]
    target = cusp_values[(ideal_house - 1) % 12]
    delta = abs(delta_deg(longitude, target))
    normalized = max(0.0, 1.0 - (delta / 180.0))
    return 60.0 * normalized


def _naisargika_bala(planet: str) -> float:
    return NAISARGIKA_BALA.get(planet, 0.0)


def _cheshta_bala(planet: str, speed_longitude: float) -> float:
    bounds = CHESHTA_SPEED_BOUNDS.get(planet)
    if bounds is None:
        return 0.0
    minimum, maximum = bounds
    if isnan(speed_longitude) or maximum <= minimum:
        return 0.0
    ratio = (speed_longitude - minimum) / (maximum - minimum)
    value = max(0.0, min(1.0, ratio))
    return value * 60.0


def _build_score(
    planet: str,
    longitude: float,
    house_idx: int,
    cusps: Iterable[float],
    speed_longitude: float,
) -> ShadbalaScore:
    factors = {
        "uccha_bala": ShadbalaFactor(
            name="Uccha Bala",
            value=_uccha_bala(planet, longitude),
            maximum=60.0,
            description="Strength derived from proximity to the planet's exaltation point.",
        ),
        "kendra_bala": ShadbalaFactor(
            name="Kendra Bala",
            value=_kendra_bala(house_idx),
            maximum=60.0,
            description="Angular strength determined by the house placement relative to the ascendant.",
        ),
        "dig_bala": ShadbalaFactor(
            name="Dig Bala",
            value=_dig_bala(planet, longitude, cusps),
            maximum=60.0,
            description="Directional strength from the ideal house orientation for the planet.",
        ),
        "naisargika_bala": ShadbalaFactor(
            name="Naisargika Bala",
            value=_naisargika_bala(planet),
            maximum=60.0,
            description="Inherent luminous strength calibrated from classical scales.",
        ),
        "cheshta_bala": ShadbalaFactor(
            name="Cheshta Bala",
            value=_cheshta_bala(planet, speed_longitude),
            maximum=60.0,
            description="Dynamic strength from current apparent motion speed (retrograde emphasis).",
        ),
    }
    return ShadbalaScore(planet=planet, factors=factors, missing=MISSING_COMPONENTS)


def compute_shadbala(
    context: VedicChartContext,
    *,
    planets: Iterable[str] | None = None,
) -> ShadbalaReport:
    """Compute Śaḍbala factors for the requested planets.

    Only classical grahas supported by the Śaḍbala system are evaluated.
    ``planets`` defaults to the seven visible planets.  The returned report
    exposes per-planet totals alongside individual component values and a list
    of not-yet-computed auxiliary factors.
    """

    chart = context.chart
    requested = tuple(planets) if planets is not None else SUPPORTED_PLANETS
    available_positions = chart.positions
    cusps = chart.houses.cusps

    scores: dict[str, ShadbalaScore] = {}
    for planet in requested:
        position = available_positions.get(planet)
        if position is None:
            continue
        house_idx = _house_index(position.longitude, cusps)
        score = _build_score(
            planet,
            position.longitude,
            house_idx,
            cusps,
            position.speed_longitude,
        )
        scores[planet] = score

    return ShadbalaReport(scores=scores)
