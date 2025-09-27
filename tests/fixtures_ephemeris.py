from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict


@dataclass
class LinearEphemeris:
    """Simple linear motion in deg/day per body."""

    t0: datetime
    base: Dict[str, float]
    rates_deg_per_day: Dict[str, float]

    def __call__(self, ts: datetime) -> Dict[str, float]:
        dt_days = (ts - self.t0).total_seconds() / 86400.0
        out: Dict[str, float] = {}
        for name, lon0 in self.base.items():
            out[name] = (
                lon0 + self.rates_deg_per_day.get(name, 0.0) * dt_days
            ) % 360.0
        return out


@dataclass
class LoopRetrogradeEphemeris:
    """One body performs a single retrograde loop: forward before t_mid, backward after.

    Useful to test root bracketing around direction changes.
    """

    t0: datetime
    base: Dict[str, float]
    prograde_rates: Dict[str, float]  # deg/day before t_mid
    retrograde_rates: Dict[str, float]  # deg/day after t_mid
    t_mid: datetime

    def __call__(self, ts: datetime) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for name, lon0 in self.base.items():
            if ts <= self.t_mid:
                dt_days = (ts - self.t0).total_seconds() / 86400.0
                rate = self.prograde_rates.get(name, 0.0)
                out[name] = (lon0 + rate * dt_days) % 360.0
            else:
                # position at t_mid
                dt_mid = (self.t_mid - self.t0).total_seconds() / 86400.0
                lon_mid = (
                    lon0 + self.prograde_rates.get(name, 0.0) * dt_mid
                ) % 360.0
                # retrograde phase after t_mid
                dt_after = (ts - self.t_mid).total_seconds() / 86400.0
                rate_r = self.retrograde_rates.get(name, 0.0)
                out[name] = (lon_mid + rate_r * dt_after) % 360.0
        return out


@dataclass
class ConvergingConjunctionEphemeris:
    """Planet approaches the Sun; separation decreases linearly to near 0°.

    Creates a near-cazimi condition (< 0.2°) somewhere in the window.
    """

    t0: datetime
    sun_lon: float = 0.0
    planet_start_sep: float = 2.0  # deg ahead of Sun at t0
    planet_rate_minus_sun: float = -0.05  # deg/day; negative means closing in

    def __call__(self, ts: datetime) -> Dict[str, float]:
        dt_days = (ts - self.t0).total_seconds() / 86400.0
        sun = self.sun_lon % 360.0
        planet = (
            self.sun_lon
            + self.planet_start_sep
            + self.planet_rate_minus_sun * dt_days
        ) % 360.0
        return {"Sun": sun, "Mercury": planet}

