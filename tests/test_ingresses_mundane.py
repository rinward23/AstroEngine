"""Regression tests for sign ingress detection and Aries ingress charts."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from astroengine import cli
from astroengine.chart.natal import ChartLocation, compute_natal_chart
from astroengine.detectors.common import body_lon, iso_to_jd, norm360
from astroengine.detectors.ingresses import (
    ZODIAC_SIGNS,
    find_house_ingresses,
    find_sign_ingresses,
    sign_index,
    sign_name,
)
from astroengine.mundane import compute_solar_ingress_chart, compute_solar_quartet


def test_sign_ingresses_outer_planets_precision():
    start = iso_to_jd("2015-01-01T00:00:00Z")
    end = iso_to_jd("2025-01-01T00:00:00Z")
    bodies = ("jupiter", "saturn", "uranus", "neptune", "pluto")
    events = find_sign_ingresses(start, end, bodies=bodies, step_hours=12.0)
    assert events

    for event in events:
        assert event.body in bodies
        lon = norm360(body_lon(event.jd, event.body))
        if event.motion == "retrograde":
            boundary_index = ZODIAC_SIGNS.index(event.from_sign)
        else:
            boundary_index = ZODIAC_SIGNS.index(event.to_sign)
        target = (boundary_index * 30.0) % 360.0
        diff = abs(((lon - target + 180.0) % 360.0) - 180.0)
        assert diff < 1e-3

        before = sign_name(sign_index(body_lon(event.jd - 0.1, event.body)))
        after = sign_name(sign_index(body_lon(event.jd + 0.1, event.body)))
    assert before == event.from_sign
    assert after == event.to_sign


def test_sign_ingresses_respects_profile_moon_toggle():
    start = iso_to_jd("2024-03-20T00:00:00Z")
    end = iso_to_jd("2024-03-27T00:00:00Z")

    default_events = find_sign_ingresses(start, end, step_hours=3.0)
    assert default_events
    assert all(event.body.lower() != "moon" for event in default_events)

    moon_events = find_sign_ingresses(
        start,
        end,
        include_moon=True,
        step_hours=3.0,
    )
    assert any(event.body.lower() == "moon" for event in moon_events)


def test_sign_ingresses_inner_mode_always_includes_mercury():
    start = iso_to_jd("2024-03-08T00:00:00Z")
    end = iso_to_jd("2024-03-12T00:00:00Z")

    restricted = find_sign_ingresses(start, end, step_hours=2.0)
    assert all(event.body.lower() != "mercury" for event in restricted)

    always = find_sign_ingresses(
        start,
        end,
        inner_mode="always",
        step_hours=2.0,
    )
    assert always
    assert any(event.body.lower() == "mercury" for event in always)


def test_house_ingresses_track_cusps():
    location = ChartLocation(latitude=34.0522, longitude=-118.2437)
    natal = compute_natal_chart(
        datetime(1990, 7, 1, 15, 30, tzinfo=UTC),
        location,
    )
    cusps = natal.houses.cusps

    start = iso_to_jd("2024-01-01T00:00:00Z")
    end = iso_to_jd("2024-02-01T00:00:00Z")

    events = find_house_ingresses(start, end, cusps, bodies=("sun",))
    assert events

    for event in events:
        assert event.from_sign.startswith("House")
        assert event.to_sign.startswith("House")

        target_idx = int(event.to_sign.split()[-1])
        cusp_lon = cusps[target_idx - 1] % 360.0
        lon = norm360(body_lon(event.jd, event.body))
        diff = abs(((lon - cusp_lon + 180.0) % 360.0) - 180.0)
        assert diff < 1e-3

def test_aries_ingress_chart_with_location_and_natal():
    location = ChartLocation(latitude=40.7128, longitude=-74.0060)
    natal = compute_natal_chart(
        datetime(1990, 1, 1, 12, 0, tzinfo=UTC),
        location,
    )
    chart = compute_solar_ingress_chart(
        2024, "Aries", location=location, natal_chart=natal
    )

    assert chart.sign == "Aries"
    assert chart.event.to_sign == "Aries"
    sun_lon = chart.positions["Sun"].longitude
    assert min(abs(sun_lon), abs(sun_lon - 360.0)) < 1e-3
    assert chart.houses is not None
    assert chart.aspects
    assert chart.natal_aspects


def test_solar_quartet_contains_expected_signs():
    location = ChartLocation(latitude=51.5074, longitude=-0.1278)
    charts = compute_solar_quartet(2023, location=location)
    assert [chart.sign for chart in charts] == ["Aries", "Cancer", "Libra", "Capricorn"]
    assert all(chart.aspects for chart in charts)


def test_cli_mundane_exports(tmp_path):
    events_path = tmp_path / "ingresses.json"
    args = [
        "--start-utc",
        "2015-01-01T00:00:00Z",
        "--end-utc",
        "2016-01-01T00:00:00Z",
        "--ingresses",
        "--ingress-bodies",
        "jupiter",
        "--mundane-json",
        str(events_path),
    ]
    assert cli.main(args) == 0
    data = json.loads(events_path.read_text(encoding="utf-8"))
    assert "ingresses" in data
    assert data["ingresses"]["events"]

    aries_path = tmp_path / "aries.json"
    args = [
        "--aries-ingress",
        "2024",
        "--lat",
        "40.7128",
        "--lon",
        "-74.0060",
        "--aries-quartet",
        "--mundane-json",
        str(aries_path),
    ]
    assert cli.main(args) == 0
    aries_payload = json.loads(aries_path.read_text(encoding="utf-8"))
    assert "aries_ingress" in aries_payload
    charts = aries_payload["aries_ingress"]["charts"]
    assert len(charts) == 4
    assert charts[0]["sign"] == "Aries"
