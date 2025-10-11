import math
from datetime import UTC, datetime

import pytest

from astroengine.chart.natal import ChartLocation
from astroengine.detectors.ingress import find_ingresses
from astroengine.detectors.ingresses import find_sign_ingresses
from astroengine.ephemeris import SwissEphemerisAdapter
from astroengine.mundane import compute_cardinal_ingress_charts


def test_find_ingresses_detects_solar_aries() -> None:
    adapter = SwissEphemerisAdapter()
    start_jd = adapter.julian_day(datetime(2024, 3, 15, tzinfo=UTC))
    end_jd = adapter.julian_day(datetime(2024, 3, 25, tzinfo=UTC))
    events = find_ingresses(start_jd, end_jd, ["Sun"])
    assert any(event.sign == "Aries" for event in events)


def test_compute_cardinal_ingress_charts_returns_natal_charts() -> None:
    location = ChartLocation(latitude=0.0, longitude=0.0)
    charts = compute_cardinal_ingress_charts(2024, location)
    assert "aries" in charts
    aries = charts["aries"]
    assert aries.event.sign == "Aries"
    sun_lon = aries.chart.positions["Sun"].longitude
    wrapped = sun_lon % 360.0
    assert min(abs(wrapped), abs(wrapped - 360.0)) < 0.5


def test_find_sign_ingresses_requires_swe(monkeypatch: pytest.MonkeyPatch) -> None:
    import astroengine.detectors.ingresses as ingress_module

    original_has_swe = ingress_module._HAS_SWE
    monkeypatch.setattr(ingress_module, "_HAS_SWE", False, raising=False)

    try:
        with pytest.raises(RuntimeError, match="Swiss ephemeris not available"):
            find_sign_ingresses(2451545.0, 2451545.01, bodies=("sun",), step_hours=1.0)
    finally:
        monkeypatch.setattr(ingress_module, "_HAS_SWE", original_has_swe, raising=False)
