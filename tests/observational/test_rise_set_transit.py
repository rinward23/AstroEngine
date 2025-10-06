from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

pytest.importorskip(
    "PIL",
    reason="Pillow not installed; install extras with `pip install -e .[ui,reports]`.",
)

from astroengine.engine.observational import (
    EventOptions,
    MetConditions,
    horizontal_from_equatorial,
    rise_set_times,
    topocentric_equatorial,
    transit_time,
)
from astroengine.ephemeris import EphemerisAdapter, EphemerisConfig, ObserverLocation

swe = pytest.importorskip("swisseph")


def test_sun_events_greenwich() -> None:
    adapter = EphemerisAdapter(EphemerisConfig())
    observer = ObserverLocation(latitude_deg=51.4779, longitude_deg=-0.0015, elevation_m=46.0)
    moment = datetime(2024, 6, 21, 0, 0, tzinfo=UTC)
    options = EventOptions(refraction=True, met=MetConditions(temperature_c=10.0, pressure_hpa=1010.0))

    rise, set_ = rise_set_times(adapter, swe().SUN, moment, observer, options=options)
    transit = transit_time(adapter, swe().SUN, moment, observer)

    assert rise is not None and set_ is not None and transit is not None

    # Verify altitude at rise/set is close to threshold
    equ_rise = topocentric_equatorial(adapter, swe().SUN, rise, observer)
    horiz_rise = horizontal_from_equatorial(
        equ_rise.right_ascension_deg,
        equ_rise.declination_deg,
        rise,
        observer,
        refraction=True,
        met=options.met,
    )
    assert abs(horiz_rise.altitude_deg - (-0.5667)) < 0.3

    equ_transit = topocentric_equatorial(adapter, swe().SUN, transit, observer)
    horiz_transit = horizontal_from_equatorial(
        equ_transit.right_ascension_deg,
        equ_transit.declination_deg,
        transit,
        observer,
        refraction=True,
        met=options.met,
    )
    later = transit + timedelta(minutes=10)
    equ_later = topocentric_equatorial(adapter, swe().SUN, later, observer)
    horiz_later = horizontal_from_equatorial(
        equ_later.right_ascension_deg,
        equ_later.declination_deg,
        later,
        observer,
        refraction=True,
        met=options.met,
    )
    assert horiz_transit.altitude_deg > horiz_later.altitude_deg
