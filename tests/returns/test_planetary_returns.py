from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

pytest.importorskip(
    "swisseph",
    reason="pyswisseph not installed; install extras with `pip install -e .[ephem,providers]`.",
)

from astroengine.core.time import to_tt
from astroengine.engine.returns import AttachOptions, GeoLoc, NatalCtx, ScanOptions, scan_returns
from astroengine.engine.returns._codes import resolve_body_code
from astroengine.ephemeris import EphemerisAdapter


def test_mars_returns_are_ordered() -> None:
    adapter = EphemerisAdapter()
    natal_dt = datetime(1988, 7, 12, 5, 0, tzinfo=UTC)
    mars_code = resolve_body_code("Mars").code
    natal_conv = to_tt(natal_dt)
    natal_mars = adapter.sample(mars_code, natal_conv).longitude % 360.0

    location = GeoLoc(latitude_deg=34.0522, longitude_deg=-118.2437, elevation_m=89.0)
    natal_ctx = NatalCtx(
        moment=natal_dt,
        longitudes={"mars": natal_mars},
        location=location,
    )

    start = datetime(1995, 1, 1, tzinfo=UTC)
    end = start + timedelta(days=365 * 9)

    options = ScanOptions(location=location, attach=AttachOptions(transiting_aspects=False))
    hits = scan_returns(adapter, ["Mars"], start, end, natal_ctx, options)

    assert len(hits) >= 3
    times = [hit.instant.exact_time for hit in hits]
    assert times == sorted(times)
    for prev, current in zip(times, times[1:], strict=False):
        assert (current - prev).days > 500
