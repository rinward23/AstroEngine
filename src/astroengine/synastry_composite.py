from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import pandas as pd


@dataclass
class CompositePoint:
    name: str
    degree: float


@dataclass
class CompositeTransitHit:
    transit_body: str
    composite_point: str
    orb: float
    exact: float


@dataclass
class CompositeTransitResult:
    composite_points: List[CompositePoint]
    hits: List[CompositeTransitHit]


class CompositeChartCalculator:
    """Derive midpoint composite points between two natal charts."""

    def compute(self, chart_a: Dict[str, float], chart_b: Dict[str, float], tracked_points: Iterable[str]) -> List[CompositePoint]:
        points: List[CompositePoint] = []
        for point in tracked_points:
            if point not in chart_a or point not in chart_b:
                raise KeyError(f"Point '{point}' missing from natal charts")
            degree = (chart_a[point] + chart_b[point]) / 2.0
            points.append(CompositePoint(point, degree % 360))
        return points


class CompositeTransitPipeline:
    """Match transits against composite points within a configurable orb."""

    def __init__(self, orb: float, tracked_points: Iterable[str]):
        self.orb = orb
        self.tracked_points = list(tracked_points)
        self.chart_calculator = CompositeChartCalculator()

    def run(
        self,
        natal_a: Dict[str, float],
        natal_b: Dict[str, float],
        transits: Dict[str, float],
    ) -> CompositeTransitResult:
        composite_points = self.chart_calculator.compute(natal_a, natal_b, self.tracked_points)
        hits: List[CompositeTransitHit] = []
        for transit_body, transit_degree in transits.items():
            for point in composite_points:
                orb = self._orb_difference(transit_degree, point.degree)
                if orb <= self.orb:
                    hits.append(
                        CompositeTransitHit(
                            transit_body=transit_body,
                            composite_point=point.name,
                            orb=orb,
                            exact=point.degree,
                        )
                    )
        return CompositeTransitResult(composite_points, hits)

    @staticmethod
    def _orb_difference(a: float, b: float) -> float:
        diff = abs((a - b + 180) % 360 - 180)
        return diff

    def to_frame(self, result: CompositeTransitResult) -> pd.DataFrame:
        records = [hit.__dict__ for hit in result.hits]
        return pd.DataFrame.from_records(records)


__all__ = [
    "CompositeTransitPipeline",
    "CompositeTransitResult",
]
