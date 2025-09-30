# >>> AUTO-GEN BEGIN: tests-stations v1.0
from __future__ import annotations

import os

import pytest

from astroengine.detectors.common import iso_to_jd
from astroengine.detectors.stations import find_shadow_periods, find_stations

try:  # pragma: no cover - optional dependency guard
    import swisseph as swe  # type: ignore

    HAVE_SWISS = True
except Exception:  # pragma: no cover - defensive fallback
    HAVE_SWISS = False

SE_OK = bool(os.environ.get("SE_EPHE_PATH") or os.environ.get("SWE_EPH_PATH"))

pytestmark = pytest.mark.skipif(
    not (HAVE_SWISS and SE_OK), reason="Swiss ephemeris not available"
)



def _find_station(events, iso_ts: str, body: str, *, tolerance_minutes: float = 15.0):
    target = iso_to_jd(iso_ts)
    tol = tolerance_minutes / (24 * 60)
    for event in events:
        if event.body.lower() == body.lower() and abs(event.jd - target) <= tol:
            return event
    raise AssertionError(f"no station for {body} near {iso_ts}")


def test_station_refines_speed():
    start = iso_to_jd("2025-01-01T00:00:00Z")
    end = iso_to_jd("2025-12-31T23:59:59Z")
    events = find_stations(start, end)
    assert events

    mercury = _find_station(events, "2025-03-15T06:46:11Z", "mercury")
    values, _ = swe.calc_ut(mercury.jd, swe.MERCURY, swe.FLG_SWIEPH | swe.FLG_SPEED)
    assert abs(values[3]) < 5e-6

    offsets = (0.5 / 24.0, 1.0 / 24.0, 2.0 / 24.0)
    expected_station = None
    for delta in offsets:
        before_values, _ = swe.calc_ut(
            mercury.jd - delta, swe.MERCURY, swe.FLG_SWIEPH | swe.FLG_SPEED
        )
        after_values, _ = swe.calc_ut(
            mercury.jd + delta, swe.MERCURY, swe.FLG_SWIEPH | swe.FLG_SPEED
        )
        before = before_values[3]
        after = after_values[3]
        if before > 0 and after < 0:
            expected_station = "retrograde"
            break
        if before < 0 and after > 0:
            expected_station = "direct"
            break

    assert mercury.station_type == expected_station

    jds = [event.jd for event in events]
    assert jds == sorted(jds)


def test_shadow_periods_bracket_stations():
    start = iso_to_jd("2025-01-01T00:00:00Z")
    end = iso_to_jd("2025-12-31T23:59:59Z")

    stations = find_stations(start, end, bodies=("mercury",))
    assert stations

    periods = find_shadow_periods(start, end, bodies=("mercury",))
    assert periods
    assert periods == sorted(periods, key=lambda period: period.jd)

    reference_stations = find_stations(start - 60.0, end + 60.0, bodies=("mercury",))
    station_keys = {
        int(round(event.jd * 86400)): event for event in reference_stations
    }

    for period in periods:
        retro_key = int(round(period.retrograde_station_jd * 86400))
        direct_key = int(round(period.direct_station_jd * 86400))
        assert retro_key in station_keys
        assert direct_key in station_keys

        assert period.direct_station_jd >= period.retrograde_station_jd

        if period.kind == "pre":
            assert period.jd <= period.retrograde_station_jd
            assert abs(period.start_longitude - period.direct_longitude) < 1e-3
            assert abs(period.end_longitude - period.retrograde_longitude) < 1e-3
        else:
            assert period.jd == pytest.approx(period.direct_station_jd, rel=0, abs=1e-9)
            assert period.end_jd >= period.direct_station_jd
            assert abs(period.start_longitude - period.direct_longitude) < 1e-3
            assert abs(period.end_longitude - period.retrograde_longitude) < 1e-3

# >>> AUTO-GEN END: tests-stations v1.0
