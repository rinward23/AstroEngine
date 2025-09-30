"""Time mapping helpers for symbolic progressions and directions."""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Final, Literal

from ...core.time import SECONDS_PER_DAY

__all__ = [
    "ProgressionMapping",
    "progressed_instant_secondary",
    "progressed_instant_variant",
]

_SECONDS_PER_HOUR: Final[float] = 3600.0


@dataclass(frozen=True)
class ProgressionMapping:
    """Describe the link between an observation instant and ephemeris time."""

    natal: _dt.datetime
    observation: _dt.datetime
    progressed: _dt.datetime
    scale: str


def _delta_days(moment: _dt.datetime, target: _dt.datetime) -> float:
    delta = target - moment
    return delta.total_seconds() / SECONDS_PER_DAY


def _scaled_offset(
    natal: _dt.datetime,
    observation: _dt.datetime,
    *,
    factor_days: float,
) -> _dt.datetime:
    days = _delta_days(natal, observation)
    offset = _dt.timedelta(days=days * factor_days)
    return natal + offset


def progressed_instant_secondary(
    t0_utc: _dt.datetime,
    T_utc: _dt.datetime,
    *,
    year_days: float = 365.242189,
) -> _dt.datetime:
    """Return the secondary progressed instant for ``T_utc``."""

    scale = 1.0 / year_days
    progressed = _scaled_offset(t0_utc, T_utc, factor_days=scale)
    return progressed


def progressed_instant_variant(
    t0_utc: _dt.datetime,
    T_utc: _dt.datetime,
    *,
    variant: Literal["day_for_month", "lunar_month_for_year", "hour_for_year"],
    year_days: float = 365.242189,
    synodic_days: float = 29.530588,
) -> _dt.datetime:
    """Return progressed instant for the requested variant mapping."""

    if variant == "day_for_month":
        factor_days = 1.0 / synodic_days
    elif variant == "lunar_month_for_year":
        factor_days = synodic_days / year_days
    elif variant == "hour_for_year":
        factor_days = _SECONDS_PER_HOUR / SECONDS_PER_DAY / year_days
    else:  # pragma: no cover - defensive guard
        raise ValueError(f"unsupported progression variant: {variant}")

    return _scaled_offset(t0_utc, T_utc, factor_days=factor_days)
