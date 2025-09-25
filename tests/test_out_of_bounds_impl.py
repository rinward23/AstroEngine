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
from astroengine.detectors.out_of_bounds import find_out_of_bounds


def _match_event(
    events,
    iso_ts: str,
    *,
    body: str,
    state: str,
    hemisphere: str,
    tolerance_minutes: float = 10.0,
):
    target = iso_to_jd(iso_ts)
    tol = tolerance_minutes / (24 * 60)
    for event in events:
        if (
            event.body.lower() == body.lower()
            and event.state == state
            and event.hemisphere == hemisphere
            and abs(event.jd - target) <= tol
        ):
            return event
    raise AssertionError(f"no {body} {state} event near {iso_ts}")


def test_out_of_bounds_crossings():
    start = iso_to_jd("2024-01-01T00:00:00Z")
    end = iso_to_jd("2025-12-31T23:59:59Z")
    events = find_out_of_bounds(start, end)

    moon_event = _match_event(
        events,
        "2024-01-07T22:20:11Z",
        body="moon",
        state="enter",
        hemisphere="south",
    )
    assert abs(abs(moon_event.declination) - moon_event.limit) < 5e-5

    mars_event = _match_event(
        events,
        "2024-01-23T13:36:01Z",
        body="mars",
        state="exit",
        hemisphere="south",
    )
    assert abs(abs(mars_event.declination) - mars_event.limit) < 5e-5
