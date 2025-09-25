# >>> AUTO-GEN BEGIN: tests-eclipses v1.0
from __future__ import annotations

import os

import pytest

try:
    HAVE_SWISS = True
except Exception:
    HAVE_SWISS = False

SE_OK = bool(os.environ.get("SE_EPHE_PATH") or os.environ.get("SWE_EPH_PATH"))
pytestmark = pytest.mark.skipif(
    not (HAVE_SWISS and SE_OK), reason="Swiss ephemeris not available"
)

from astroengine.detectors.common import iso_to_jd
from astroengine.detectors.eclipses import find_eclipses


def _find_event(events, iso_ts: str, *, tolerance_minutes: float = 2.0):
    target = iso_to_jd(iso_ts)
    tol = tolerance_minutes / (24 * 60)
    for event in events:
        if abs(event.jd - target) <= tol:
            return event
    raise AssertionError(f"no event within {tolerance_minutes} minutes of {iso_ts}")


def test_eclipses_known_events():
    start = iso_to_jd("2024-01-01T00:00:00Z")
    end = iso_to_jd("2028-12-31T23:59:59Z")
    events = find_eclipses(start, end)

    solar = _find_event(events, "2024-04-08T18:17:23Z")
    assert solar.eclipse_type == "solar"
    assert solar.phase == "new_moon"
    assert solar.is_visible is None

    lunar = _find_event(events, "2025-03-14T06:58:47Z")
    assert lunar.eclipse_type == "lunar"
    assert lunar.phase == "full_moon"


def test_eclipse_visibility_flag():
    start = iso_to_jd("2024-01-01T00:00:00Z")
    end = iso_to_jd("2024-12-31T23:59:59Z")

    texas_events = find_eclipses(start, end, location=(-96.8, 32.8, 0))
    texas = _find_event(texas_events, "2024-04-08T18:17:23Z", tolerance_minutes=5.0)
    assert texas.is_visible is True

    london_events = find_eclipses(start, end, location=(0.0, 51.5, 0))
    london = _find_event(london_events, "2024-04-08T18:17:23Z", tolerance_minutes=5.0)
    assert london.is_visible is False


# >>> AUTO-GEN END: tests-eclipses v1.0
