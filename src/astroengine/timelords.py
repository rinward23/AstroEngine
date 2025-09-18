from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, Iterable, List

import pandas as pd


@dataclass
class ZodiacalPeriod:
    level: str
    sign: str
    start: date
    end: date
    duration_years: float


class ZodiacalReleasingCalculator:
    """Simplified zodiacal releasing calculator following Valens-style periods."""

    def __init__(self, base_periods: Dict[str, float]):
        if not base_periods:
            raise ValueError("Zodiacal releasing requires at least one base period")
        self.base_periods = base_periods

    def compute(self, start_sign: str, start_date: date, spans: int = 4) -> pd.DataFrame:
        if start_sign not in self.base_periods:
            raise KeyError(f"Start sign '{start_sign}' missing from base period table")

        periods: List[ZodiacalPeriod] = []
        ordered_signs = list(self.base_periods.keys())
        index = ordered_signs.index(start_sign)
        current_start = start_date
        for i in range(spans):
            sign = ordered_signs[(index + i) % len(ordered_signs)]
            duration_years = float(self.base_periods[sign])
            delta_days = int(duration_years * 365.25)
            current_end = current_start + timedelta(days=delta_days)
            periods.append(
                ZodiacalPeriod(
                    level="L1",
                    sign=sign,
                    start=current_start,
                    end=current_end,
                    duration_years=duration_years,
                )
            )
            current_start = current_end
        return pd.DataFrame([p.__dict__ for p in periods])


class ProfectionCalculator:
    """Annual profection calculator using a repeating zodiac sequence."""

    def __init__(self, zodiac_sequence: Iterable[str]):
        sequence = list(zodiac_sequence)
        if len(sequence) != 12:
            raise ValueError("Profection sequence must contain exactly 12 signs")
        self.sequence = sequence

    def active_sign(self, ascendant_sign: str, age: int) -> str:
        try:
            start_index = self.sequence.index(ascendant_sign)
        except ValueError as exc:  # pragma: no cover - defensive branch
            raise KeyError(f"Ascendant sign '{ascendant_sign}' not found in zodiac sequence") from exc
        return self.sequence[(start_index + age) % len(self.sequence)]

    def tabulate(self, ascendant_sign: str, years: int) -> pd.DataFrame:
        records = []
        for year in range(years + 1):
            records.append({"age": year, "sign": self.active_sign(ascendant_sign, year)})
        return pd.DataFrame.from_records(records)


__all__ = [
    "ZodiacalReleasingCalculator",
    "ProfectionCalculator",
]
