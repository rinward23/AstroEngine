from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from astroengine.chart import ChartLocation
from astroengine.chart.natal import NatalChart
from astroengine.ephemeris.swisseph_adapter import HousePositions
from astroengine.chart.transits import TransitContact
from astroengine.config.settings import Settings
from astroengine.detectors_aspects import AspectHit
from astroengine.forecast.stack import ForecastChart, ForecastWindow, build_forecast_stack


@pytest.fixture()
def sample_chart() -> ForecastChart:
    moment = datetime(1990, 1, 1, 12, tzinfo=UTC)
    location = ChartLocation(latitude=0.0, longitude=0.0)
    houses = HousePositions(system="placidus", cusps=tuple([0.0] * 12), ascendant=0.0, midheaven=0.0)
    natal_chart = NatalChart(
        moment=moment,
        location=location,
        julian_day=0.0,
        positions={},
        houses=houses,
        aspects=tuple(),
    )
    window = ForecastWindow(start=moment, end=moment + timedelta(days=7))
    return ForecastChart(natal_chart=natal_chart, window=window)


def _make_hit(
    *,
    when: datetime,
    moving: str,
    target: str,
    angle: float,
    orb_abs: float,
    orb_allow: float,
    speed: float | None,
    family: str,
) -> AspectHit:
    when_iso = when.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return AspectHit(
        kind=f"aspect_{moving.lower()}_{target.lower()}",
        when_iso=when_iso,
        moving=moving,
        target=target,
        angle_deg=float(angle),
        lon_moving=0.0,
        lon_target=0.0,
        delta_lambda_deg=float(angle),
        offset_deg=float(orb_abs),
        orb_abs=float(orb_abs),
        orb_allow=float(orb_allow),
        is_partile=False,
        applying_or_separating="applying",
        family=family,
        corridor_width_deg=None,
        corridor_profile=None,
        speed_deg_per_day=speed,
        retrograde=False,
        domain_weights=None,
    )


def test_build_forecast_stack_merges_components(monkeypatch: pytest.MonkeyPatch, sample_chart: ForecastChart) -> None:
    settings = Settings()
    base_time = sample_chart.window.start + timedelta(days=2)

    transit_hits = [
        _make_hit(
            when=base_time,
            moving="Mars",
            target="Sun",
            angle=0,
            orb_abs=0.3,
            orb_allow=1.5,
            speed=None,
            family="major",
        ),
        _make_hit(
            when=base_time,
            moving="Mars",
            target="Sun",
            angle=0,
            orb_abs=0.2,
            orb_allow=1.5,
            speed=None,
            family="major",
        ),
    ]

    prog_hit = _make_hit(
        when=base_time + timedelta(days=1),
        moving="Venus",
        target="Moon",
        angle=60,
        orb_abs=0.4,
        orb_allow=1.5,
        speed=0.8,
        family="progressed-natal",
    )
    solar_arc_hit = _make_hit(
        when=base_time + timedelta(days=3),
        moving="Jupiter",
        target="Asc",
        angle=90,
        orb_abs=0.6,
        orb_allow=1.5,
        speed=1.2,
        family="directed-natal",
    )

    def fake_scan_transits(**_: object) -> list[AspectHit]:
        return transit_hits

    def fake_progressed(**_: object) -> list[AspectHit]:
        return [prog_hit]

    def fake_solar_arc(**_: object) -> list[AspectHit]:
        return [solar_arc_hit]

    ingress = base_time - timedelta(hours=12)
    egress = base_time + timedelta(hours=18)

    contact = TransitContact(
        moment=base_time,
        julian_day=0.0,
        transiting_body="Mars",
        natal_body="Sun",
        angle=0,
        orb=0.2,
        separation=0.2,
        orb_allow=1.5,
        ingress=ingress,
        ingress_jd=0.0,
        egress=egress,
        egress_jd=0.0,
    )

    monkeypatch.setattr("astroengine.forecast.stack.scan_transits", fake_scan_transits)
    monkeypatch.setattr("astroengine.forecast.stack.progressed_natal_aspects", fake_progressed)
    monkeypatch.setattr("astroengine.forecast.stack.solar_arc_natal_aspects", fake_solar_arc)

    class DummyScanner:
        def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            self.adapter = type("Adapter", (), {})()

        def scan(self, natal_chart, moment):  # type: ignore[no-untyped-def]
            return [contact]

    monkeypatch.setattr("astroengine.forecast.stack.TransitScanner", DummyScanner)

    events = build_forecast_stack(settings, sample_chart)

    assert len(events) == 3

    transit_event = next(event for event in events if event["technique"] == "transits")
    assert transit_event["start"] == ingress.astimezone(UTC).isoformat().replace("+00:00", "Z")
    assert transit_event["end"] == egress.astimezone(UTC).isoformat().replace("+00:00", "Z")
    assert pytest.approx(transit_event["exactness"], rel=1e-6) == 0.2

    techniques = {event["technique"] for event in events}
    assert techniques == {"transits", "progressions", "solar_arc"}


def test_forecast_stack_respects_component_settings(monkeypatch: pytest.MonkeyPatch, sample_chart: ForecastChart) -> None:
    settings = Settings()
    settings.forecast_stack.components["transits"] = False
    settings.forecast_stack.components["progressions"] = False

    base_time = sample_chart.window.start + timedelta(days=1)

    solar_arc_hit = _make_hit(
        when=base_time,
        moving="Mars",
        target="MC",
        angle=120,
        orb_abs=0.5,
        orb_allow=1.5,
        speed=1.0,
        family="directed-natal",
    )

    monkeypatch.setattr("astroengine.forecast.stack.scan_transits", lambda **_: [])
    monkeypatch.setattr("astroengine.forecast.stack.progressed_natal_aspects", lambda **_: [])
    monkeypatch.setattr("astroengine.forecast.stack.solar_arc_natal_aspects", lambda **_: [solar_arc_hit])

    events = build_forecast_stack(settings, sample_chart)

    assert len(events) == 1
    assert events[0]["technique"] == "solar_arc"
