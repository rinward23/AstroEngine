# >>> AUTO-GEN BEGIN: tests-stations v1.0
from __future__ import annotations

import os

import pytest

from astroengine.detectors.common import iso_to_jd
from astroengine.detectors.stations import find_stations

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

    jds = [event.jd for event in events]
    assert jds == sorted(jds)


# >>> AUTO-GEN END: tests-stations v1.0
