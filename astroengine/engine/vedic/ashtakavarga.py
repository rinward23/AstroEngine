"""Ashtakavarga bindu calculations for classical Jyotiṣa analysis."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from ...detectors.ingresses import sign_index
from .chart import VedicChartContext

__all__ = [
    "Bhinnashtakavarga",
    "AshtakavargaSet",
    "compute_bhinnashtakavarga",
    "compute_sarvashtakavarga",
]


PLANETS: tuple[str, ...] = (
    "Sun",
    "Moon",
    "Mars",
    "Mercury",
    "Jupiter",
    "Venus",
    "Saturn",
)


CONTRIBUTORS: tuple[str, ...] = (
    "Sun",
    "Moon",
    "Mars",
    "Mercury",
    "Jupiter",
    "Venus",
    "Saturn",
    "Ascendant",
)


# Relative house numbers counted from the base planet for which a contributor
# yields a bindu in the Bhinnashtakavarga grid.  The rules follow the classical
# Parāśari schema.
ASHTAKAVARGA_RULES: Mapping[str, Mapping[str, tuple[int, ...]]] = {
    "Sun": {
        "Sun": (1, 2, 4, 7, 8, 9, 10, 11),
        "Moon": (3, 6, 10, 11),
        "Mars": (1, 2, 4, 7, 8, 10, 11),
        "Mercury": (3, 6, 8, 11),
        "Jupiter": (5, 6, 9, 11),
        "Venus": (6, 7, 12),
        "Saturn": (3, 5, 6, 10, 11),
        "Ascendant": (1, 2, 4, 7, 8, 10, 11),
    },
    "Moon": {
        "Sun": (3, 6, 7, 10, 11),
        "Moon": (1, 3, 6, 7, 10, 11),
        "Mars": (3, 6, 11),
        "Mercury": (3, 5, 6, 9, 11),
        "Jupiter": (1, 4, 7, 8, 10, 11),
        "Venus": (2, 3, 4, 5, 7, 9, 11),
        "Saturn": (3, 6, 10, 11),
        "Ascendant": (3, 6, 7, 10, 11),
    },
    "Mars": {
        "Sun": (1, 3, 6, 10, 11),
        "Moon": (1, 3, 6, 7, 10, 11),
        "Mars": (1, 3, 6, 7, 10, 11),
        "Mercury": (3, 6, 10, 11),
        "Jupiter": (1, 3, 6, 8, 10, 11),
        "Venus": (1, 2, 4, 5, 7, 9, 10, 11),
        "Saturn": (3, 5, 6, 10, 11),
        "Ascendant": (1, 3, 6, 10, 11),
    },
    "Mercury": {
        "Sun": (3, 4, 6, 8, 11),
        "Moon": (3, 5, 6, 7, 9, 11),
        "Mars": (1, 3, 6, 10, 11),
        "Mercury": (1, 3, 4, 5, 7, 8, 10, 11),
        "Jupiter": (1, 2, 4, 5, 7, 8, 10, 11),
        "Venus": (1, 2, 3, 4, 5, 7, 8, 9, 11),
        "Saturn": (3, 4, 6, 10, 11),
        "Ascendant": (1, 3, 5, 7, 9, 11),
    },
    "Jupiter": {
        "Sun": (1, 2, 4, 5, 7, 9, 10, 11),
        "Moon": (2, 3, 5, 6, 9, 11),
        "Mars": (1, 3, 5, 6, 8, 10, 11),
        "Mercury": (1, 2, 4, 5, 7, 8, 10, 11),
        "Jupiter": (1, 2, 4, 5, 7, 9, 10, 11),
        "Venus": (1, 2, 3, 4, 5, 7, 9, 10, 11),
        "Saturn": (1, 2, 4, 5, 7, 9, 10, 11),
        "Ascendant": (1, 2, 4, 5, 7, 9, 10, 11),
    },
    "Venus": {
        "Sun": (1, 2, 3, 4, 5, 8, 9, 11),
        "Moon": (1, 3, 5, 6, 7, 9, 11),
        "Mars": (1, 2, 3, 4, 5, 7, 8, 9, 11),
        "Mercury": (1, 2, 3, 4, 5, 7, 8, 9, 11),
        "Jupiter": (1, 2, 4, 5, 7, 8, 9, 11),
        "Venus": (1, 2, 3, 4, 5, 8, 9, 11, 12),
        "Saturn": (1, 2, 4, 5, 7, 9, 10, 11),
        "Ascendant": (1, 2, 3, 4, 5, 7, 9, 11),
    },
    "Saturn": {
        "Sun": (3, 4, 6, 10, 11),
        "Moon": (3, 5, 6, 9, 11),
        "Mars": (3, 4, 6, 10, 11),
        "Mercury": (3, 4, 6, 10, 11),
        "Jupiter": (1, 2, 4, 5, 7, 9, 10, 11),
        "Venus": (3, 4, 6, 10, 11),
        "Saturn": (3, 4, 6, 10, 11),
        "Ascendant": (3, 5, 6, 9, 11),
    },
}


@dataclass(frozen=True)
class Bhinnashtakavarga:
    """Per-planet bindu distribution across the zodiac."""

    planet: str
    bindus: tuple[int, ...]

    @property
    def total(self) -> int:
        return sum(self.bindus)


@dataclass(frozen=True)
class AshtakavargaSet:
    """Aggregate Sarvashtakavarga values for each sign."""

    sarva: Mapping[int, int]
    bhinna: Mapping[str, Bhinnashtakavarga]

    def bindu_for_sign(self, sign_index: int) -> int:
        return self.sarva.get(sign_index, 0)


def _ascendant_index(context: VedicChartContext) -> int:
    return sign_index(context.chart.houses.ascendant)


def _compute_bindu_array(
    planet: str,
    context: VedicChartContext,
    positions: Mapping[str, object],
) -> tuple[int, ...]:
    rules = ASHTAKAVARGA_RULES[planet]
    base_sign = sign_index(positions[planet].longitude)
    asc_index = _ascendant_index(context)

    contributions = {name: 0 for name in range(12)}

    for contributor in CONTRIBUTORS:
        if contributor == "Ascendant":
            contributor_sign = asc_index
        else:
            position = positions.get(contributor)
            if position is None:
                continue
            contributor_sign = sign_index(position.longitude)
        relative = ((contributor_sign - base_sign) % 12) + 1
        allowed = rules.get(contributor)
        if allowed is None:
            continue
        if relative in allowed:
            contributions[contributor_sign] = contributions.get(contributor_sign, 0) + 1

    return tuple(contributions[idx] for idx in range(12))


def compute_bhinnashtakavarga(
    context: VedicChartContext,
    *,
    planets: Iterable[str] | None = None,
) -> Mapping[str, Bhinnashtakavarga]:
    """Return Bhinnashtakavarga bindus for the requested planets."""

    requested = tuple(planets) if planets is not None else PLANETS
    positions = context.chart.positions

    results: dict[str, Bhinnashtakavarga] = {}
    for planet in requested:
        if planet not in ASHTAKAVARGA_RULES:
            continue
        if planet not in positions:
            continue
        bindus = _compute_bindu_array(planet, context, positions)
        results[planet] = Bhinnashtakavarga(planet=planet, bindus=bindus)
    return results


def compute_sarvashtakavarga(
    bhinna: Mapping[str, Bhinnashtakavarga],
) -> Mapping[int, int]:
    """Aggregate the Sarvashtakavarga (total bindus per sign)."""

    totals = {idx: 0 for idx in range(12)}
    for entry in bhinna.values():
        for idx, value in enumerate(entry.bindus):
            totals[idx] += value
    return totals
