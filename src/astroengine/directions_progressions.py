from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import pandas as pd


@dataclass
class DirectionEvent:
    aspect: str
    significator: str
    promissor: str
    orb: float
    exact_degrees: float
    event_age: float


class PrimaryDirectionCalculator:
    """Compute simplified Ptolemaic primary directions."""

    def __init__(self, aspects: Dict[str, float], orb: float, rate_degrees_per_year: float):
        self.aspects = aspects
        self.orb = orb
        self.rate = rate_degrees_per_year

    def compute(self, positions: Dict[str, float], pairs: Iterable[Dict[str, str]]) -> pd.DataFrame:
        events: List[DirectionEvent] = []
        for pair in pairs:
            significator = pair["significator"]
            promissor = pair["promissor"]
            sig_pos = positions[significator]
            prom_pos = positions[promissor]
            separation = (prom_pos - sig_pos) % 360
            for aspect_name, aspect_degrees in self.aspects.items():
                delta = self._angular_delta(separation, aspect_degrees)
                if abs(delta) <= self.orb:
                    age = (aspect_degrees - separation) / self.rate
                    age = age % (360 / self.rate)
                    events.append(
                        DirectionEvent(
                            aspect=aspect_name,
                            significator=significator,
                            promissor=promissor,
                            orb=abs(delta),
                            exact_degrees=aspect_degrees,
                            event_age=age,
                        )
                    )
        return pd.DataFrame([e.__dict__ for e in events])

    @staticmethod
    def _angular_delta(actual: float, target: float) -> float:
        delta = (actual - target + 180) % 360 - 180
        return delta


class SecondaryProgressionCalculator:
    """Linear secondary progression model (one degree per year by default)."""

    def __init__(self, motion_rate_degrees_per_year: float):
        self.motion_rate = motion_rate_degrees_per_year

    def progress(self, positions: Dict[str, float], years: float) -> Dict[str, float]:
        progressed = {}
        for body, degree in positions.items():
            progressed[body] = (degree + years * self.motion_rate) % 360
        return progressed

    def tabulate(self, positions: Dict[str, float], years: Iterable[int]) -> pd.DataFrame:
        records = []
        for year in years:
            progressed = self.progress(positions, year)
            for body, degree in progressed.items():
                records.append({"year": year, "body": body, "degree": degree})
        return pd.DataFrame.from_records(records)


__all__ = [
    "PrimaryDirectionCalculator",
    "SecondaryProgressionCalculator",
]
