from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest

pytest.importorskip(
    "PIL",
    reason="Pillow not installed; install extras with `pip install -e .[ui,reports]`.",
)

from astroengine.engine.observational import (
    MetConditions,
    VisibilityConstraints,
    horizontal_from_equatorial,
    topocentric_equatorial,
    visibility_windows,
)
from astroengine.ephemeris import EphemerisAdapter, EphemerisConfig, ObserverLocation

swe = pytest.importorskip("swisseph")


def _separation(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    ra1_rad = math.radians(ra1)
    ra2_rad = math.radians(ra2)
    dec1_rad = math.radians(dec1)
    dec2_rad = math.radians(dec2)
    cos_sep = (
        math.sin(dec1_rad) * math.sin(dec2_rad)
        + math.cos(dec1_rad) * math.cos(dec2_rad) * math.cos(ra1_rad - ra2_rad)
    )
    cos_sep = max(-1.0, min(1.0, cos_sep))
    return math.degrees(math.acos(cos_sep))


def test_visibility_windows_constraints() -> None:
    adapter = EphemerisAdapter(EphemerisConfig())
    observer = ObserverLocation(latitude_deg=34.0522, longitude_deg=-118.2437, elevation_m=71.0)
    start = datetime(2024, 5, 1, 3, 0, tzinfo=UTC)
    end = datetime(2024, 5, 2, 3, 0, tzinfo=UTC)

    constraints = VisibilityConstraints(
        min_altitude_deg=5.0,
        sun_altitude_max_deg=-6.0,
        sun_separation_min_deg=5.0,
        moon_altitude_max_deg=60.0,
        refraction=True,
        met=MetConditions(temperature_c=12.0, pressure_hpa=1010.0),
        step_seconds=600,
    )
    windows = visibility_windows(adapter, swe().MARS, start, end, observer, constraints)
    assert windows, "Expected at least one visibility window"

    for window in windows:
        midpoint = window.start + (window.end - window.start) / 2
        equ = topocentric_equatorial(adapter, swe().MARS, midpoint, observer)
        horiz = horizontal_from_equatorial(
            equ.right_ascension_deg,
            equ.declination_deg,
            midpoint,
            observer,
            refraction=True,
            met=constraints.met,
        )
        assert horiz.altitude_deg >= constraints.min_altitude_deg - 0.5
        if constraints.sun_separation_min_deg is not None:
            sun_equ = topocentric_equatorial(adapter, swe().SUN, midpoint, observer)
            sun_sep = _separation(
                equ.right_ascension_deg,
                equ.declination_deg,
                sun_equ.right_ascension_deg,
                sun_equ.declination_deg,
            )
            assert sun_sep >= constraints.sun_separation_min_deg - 0.5

        assert all(
            value is None or not math.isnan(value)
            for value in window.details.values()
        ), "window.details must not contain NaN values"
