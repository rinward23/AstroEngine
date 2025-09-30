from __future__ import annotations

from datetime import datetime, timezone

from astroengine.engine.returns import find_return_instant, guess_window
from astroengine.engine.returns._codes import resolve_body_code
from astroengine.ephemeris import EphemerisAdapter
from astroengine.core.time import to_tt


def _wrap(delta: float) -> float:
    return ((delta + 180.0) % 360.0) - 180.0


def test_solar_return_precision() -> None:
    adapter = EphemerisAdapter()
    natal_dt = datetime(1990, 5, 4, 12, 30, tzinfo=timezone.utc)
    code = resolve_body_code("Sun").code
    natal_conv = to_tt(natal_dt)
    natal_lon = adapter.sample(code, natal_conv).longitude % 360.0

    around = datetime(2026, 5, 4, 12, 30, tzinfo=timezone.utc)
    window = guess_window("Sun", None, around)
    instant = find_return_instant(adapter, "Sun", natal_lon, window)

    assert instant.status == "ok"
    conv_exact = to_tt(instant.exact_time)
    lon_exact = adapter.sample(code, conv_exact).longitude % 360.0
    delta = abs(_wrap(lon_exact - natal_lon))
    assert delta * 3600.0 < 0.5
    assert instant.achieved_tolerance_seconds <= 0.3
