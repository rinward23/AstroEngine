from __future__ import annotations

from datetime import datetime, timezone

import pytest

pytest.importorskip(
    "swisseph",
    reason="pyswisseph not installed; install extras with `pip install -e .[ephem,providers]`.",
)

from astroengine.engine.returns import AttachOptions, GeoLoc, NatalCtx, ScanOptions, scan_returns
from astroengine.engine.returns._codes import resolve_body_code
from astroengine.ephemeris import EphemerisAdapter
from astroengine.core.time import to_tt


def _wrap(delta: float) -> float:
    return ((delta + 180.0) % 360.0) - 180.0


def test_lunar_return_scan_counts() -> None:
    adapter = EphemerisAdapter()
    natal_dt = datetime(1995, 3, 20, 8, 15, tzinfo=timezone.utc)
    moon_code = resolve_body_code("Moon").code
    natal_conv = to_tt(natal_dt)
    natal_moon = adapter.sample(moon_code, natal_conv).longitude % 360.0

    location = GeoLoc(latitude_deg=51.5074, longitude_deg=-0.1278, elevation_m=35.0)
    natal_ctx = NatalCtx(
        moment=natal_dt,
        longitudes={"moon": natal_moon},
        location=location,
    )

    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2025, 1, 1, tzinfo=timezone.utc)

    options = ScanOptions(location=location, attach=AttachOptions(transiting_aspects=False))
    hits = scan_returns(adapter, ["Moon"], start, end, natal_ctx, options)

    assert 9 <= len(hits) <= 14
    assert hits == sorted(hits, key=lambda h: h.instant.exact_time)

    first = hits[0]
    moon_snap = first.positions["Moon"]
    delta = abs(_wrap(moon_snap.longitude - natal_moon))
    assert delta * 3600.0 < 1.5
