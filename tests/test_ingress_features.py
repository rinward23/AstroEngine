import math
from datetime import UTC, datetime

from astroengine.chart.natal import ChartLocation
from astroengine.detectors.ingress import find_ingresses
from astroengine.detectors import ingresses as ingress_module
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


def test_refine_ingress_falls_back_to_linear_interpolation(monkeypatch) -> None:
    with monkeypatch.context() as m:
        def _raise_value_error(*args, **kwargs):
            raise ValueError("no analytic root")

        m.setattr(ingress_module, "solve_zero_crossing", _raise_value_error)

        left = ingress_module._Sample(jd=2451545.0, longitude=29.5)
        right = ingress_module._Sample(jd=2451545.25, longitude=31.0)
        boundary = 30.0
        expected = left.jd + ((boundary - left.longitude) / (right.longitude - left.longitude)) * (
            right.jd - left.jd
        )

        refined = ingress_module._refine_ingress("sun", left, right, boundary)
        assert math.isclose(refined, expected, rel_tol=0.0, abs_tol=1e-12)

        adapter = SwissEphemerisAdapter()
        start_jd = adapter.julian_day(datetime(2024, 3, 15, tzinfo=UTC))
        end_jd = adapter.julian_day(datetime(2024, 3, 25, tzinfo=UTC))
        events = ingress_module.find_sign_ingresses(start_jd, end_jd, bodies=["Sun"])
        assert any(event.body.lower() == "sun" and event.to_sign == "Aries" for event in events)
