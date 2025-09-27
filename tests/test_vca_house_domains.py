from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest

from astroengine.chart import ChartLocation, compute_natal_chart
from astroengine.detectors_aspects import detect_aspects
from astroengine.engine import TargetFrameResolver, scan_contacts
from astroengine.vca.houses import (
    HouseSystem,
    domain_for_house,
    house_of,
    load_house_profile,
)


pytest.importorskip("swisseph")


def test_load_house_profile_complete() -> None:
    profile, _ = load_house_profile(None)
    for house in range(1, 13):
        assert house in profile
        weights = profile[house]
        total = weights.Mind + weights.Body + weights.Spirit
        assert math.isclose(total, 1.0, rel_tol=1e-6, abs_tol=1e-3)


def test_domain_for_house_applies_boosts() -> None:
    profile, meta = load_house_profile(None)
    base_angular = profile[1]
    boosted_angular = domain_for_house(1, profile, meta)
    assert boosted_angular.Body > base_angular.Body

    base_cadent = profile[3]
    boosted_cadent = domain_for_house(3, profile, meta)
    assert boosted_cadent.Mind < base_cadent.Mind


def test_house_of_returns_valid_range() -> None:
    moment = datetime(1990, 2, 16, 13, 30, tzinfo=UTC)
    location = ChartLocation(latitude=40.7128, longitude=-74.0060)
    chart = compute_natal_chart(moment, location)
    for system in (HouseSystem.PLACIDUS, HouseSystem.WHOLE_SIGN, HouseSystem.EQUAL):
        house = house_of(chart, "Sun", system)
        assert 1 <= house <= 12


def test_detect_aspects_emits_domain_weights() -> None:
    moment = datetime(1990, 2, 16, 13, 30, tzinfo=UTC)
    location = ChartLocation(latitude=40.7128, longitude=-74.0060)
    natal_chart = compute_natal_chart(moment, location)

    class StubProvider:
        def positions_ecliptic(self, iso: str, bodies):
            base = {
                "Sun": {"lon": 0.0, "speed_lon": 1.0},
                "Mars": {"lon": 120.0, "speed_lon": 0.0},
            }
            return {body: dict(base[body]) for body in bodies}

    hits = detect_aspects(
        StubProvider(),
        ["2024-01-01T00:00:00Z"],
        "Sun",
        "Mars",
        natal_chart=natal_chart,
        house_system=HouseSystem.PLACIDUS,
    )
    assert hits
    weights = hits[0].domain_weights
    assert weights is not None
    assert 0.0 <= weights.Mind <= 1.0
    assert 0.0 <= weights.Body <= 1.0
    assert 0.0 <= weights.Spirit <= 1.0
    assert math.isclose(weights.Mind + weights.Body + weights.Spirit, 1.0, rel_tol=1e-6, abs_tol=1e-3)


def test_scan_contacts_attaches_domain_weights() -> None:
    moment = datetime(1990, 2, 16, 13, 30, tzinfo=UTC)
    location = ChartLocation(latitude=40.7128, longitude=-74.0060)
    natal_chart = compute_natal_chart(moment, location)

    class StubProvider:
        def positions_ecliptic(self, _iso: str, bodies):
            base = {
                "sun": {"lon": 0.0, "speed_lon": 0.0},
                "mars": {"lon": 0.0, "speed_lon": 0.0},
            }
            return {body: dict(base[body.lower()]) for body in bodies}

    resolver = TargetFrameResolver("transit", natal_chart=natal_chart)
    events = scan_contacts(
        start_iso="2024-01-01T00:00:00Z",
        end_iso="2024-01-01T00:00:00Z",
        moving="Sun",
        target="Mars",
        provider_name="stub",
        provider=StubProvider(),
        step_minutes=60,
        include_declination=False,
        include_mirrors=False,
        include_aspects=True,
        target_resolver=resolver,
    )
    assert events
    payload = events[0].metadata.get("domain_weights")
    assert payload is not None
    total = float(payload["mind"]) + float(payload["body"]) + float(payload["spirit"])
    assert math.isclose(total, 1.0, rel_tol=1e-6, abs_tol=1e-3)
