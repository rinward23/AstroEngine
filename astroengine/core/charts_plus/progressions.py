"""Progression utilities for secondary and solar arc techniques.

These helpers are intentionally ephemeris-agnostic: callers provide a
``PositionProvider`` callable that returns ecliptic longitudes for requested
timestamps.  This keeps the core logic focused on the temporal mapping while
allowing production code to inject high-precision ephemerides (e.g., Swiss
Ephemeris, Skyfield) or tests to substitute synthetic data sources.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, Iterable, Tuple

# Provider signature: provider(ts) -> {name: ecliptic_longitude_deg [0..360)}
PositionProvider = Callable[[datetime], Dict[str, float]]


def _norm360(x: float) -> float:
    """Normalize ``x`` to the [0, 360) range."""

    v = x % 360.0
    return v + 360.0 if v < 0 else v


def secondary_progressed_datetime(
    natal_dt: datetime,
    target_dt: datetime,
    year_days: float = 365.2422,
) -> datetime:
    """Compute the secondary progressed datetime.

    The secondary progression model maps one civil day to one year of life. The
    returned datetime is calculated in UTC and corresponds to the elapsed
    ``target_dt - natal_dt`` scaled by ``1 / year_days``.
    """

    n = natal_dt.astimezone(timezone.utc)
    t = target_dt.astimezone(timezone.utc)
    elapsed_days = (t - n).total_seconds() / 86400.0
    elapsed_years = elapsed_days / float(year_days)
    return n + timedelta(days=elapsed_years)


def secondary_progressed_positions(
    objects: Iterable[str],
    natal_dt: datetime,
    target_dt: datetime,
    provider: PositionProvider,
    year_days: float = 365.2422,
) -> Tuple[datetime, Dict[str, float]]:
    """Return secondary progressed positions for the requested objects."""

    prog_dt = secondary_progressed_datetime(natal_dt, target_dt, year_days=year_days)
    pos = provider(prog_dt)
    return prog_dt, {name: _norm360(float(pos[name])) for name in objects if name in pos}


def solar_arc_positions(
    objects: Iterable[str],
    natal_dt: datetime,
    target_dt: datetime,
    provider: PositionProvider,
    year_days: float = 365.2422,
    sun_name: str = "Sun",
) -> Tuple[float, Dict[str, float]]:
    """Compute Solar Arc positions via the Sun's secondary arc.

    Steps:
      1. Obtain natal longitudes at ``natal_dt``.
      2. Compute the secondary progressed datetime for ``target_dt`` and obtain
         the Sun's position at that progressed time.
      3. Determine the arc by subtracting the natal Sun longitude and normalise
         to [0, 360).
      4. Apply the arc to each natal body and normalise the result.

    Returns a tuple containing the solar arc in degrees and the mapping of
    object names to their Solar Arc progressed longitudes.
    """

    n_dt = natal_dt.astimezone(timezone.utc)
    natal_pos = provider(n_dt)

    prog_dt = secondary_progressed_datetime(natal_dt, target_dt, year_days=year_days)
    prog_pos = provider(prog_dt)

    if sun_name not in natal_pos or sun_name not in prog_pos:
        raise KeyError(f"Sun longitude missing in provider output for {sun_name}")

    arc = _norm360(float(prog_pos[sun_name]) - float(natal_pos[sun_name]))

    out: Dict[str, float] = {}
    for name in objects:
        if name in natal_pos:
            out[name] = _norm360(float(natal_pos[name]) + arc)
    return arc, out
