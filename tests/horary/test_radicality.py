from __future__ import annotations

from datetime import UTC, datetime

from astroengine.chart.natal import ChartLocation, NatalChart
from astroengine.engine.horary.hour_ruler import PlanetaryHourResult
from astroengine.engine.horary.models import DignityStatus, Significator, SignificatorSet
from astroengine.engine.horary.profiles import HoraryProfile
from astroengine.engine.horary import radicality as radicality_module
from astroengine.engine.horary.radicality import run_checks
from astroengine.ephemeris.swisseph_adapter import BodyPosition, HousePositions


_DEF_ORBS = {
    "by_aspect": {
        "conjunction": 8.0,
        "sextile": 6.0,
        "square": 6.0,
        "trine": 6.0,
        "opposition": 8.0,
    }
}


def _profile() -> HoraryProfile:
    return HoraryProfile(
        name="Radicality",
        orbs=_DEF_ORBS,
        dignities={},
        radicality={
            "asc_early_deg": 3.0,
            "asc_late_deg": 27.0,
            "south_node_on_asc_orb": 3.0,
        },
        testimony_weights={},
        classification_thresholds={},
    )


def _body(name: str, longitude: float, speed: float) -> BodyPosition:
    return BodyPosition(
        body=name,
        julian_day=0.0,
        longitude=longitude,
        latitude=0.0,
        distance_au=1.0,
        speed_longitude=speed,
        speed_latitude=0.0,
        speed_distance=0.0,
        declination=0.0,
        speed_declination=0.0,
    )


def _significator(body: str, longitude: float, house: int) -> Significator:
    return Significator(
        body=body,
        role=f"{body.lower()}_role",
        longitude=longitude,
        latitude=0.0,
        speed=0.5,
        house=house,
        dignities=DignityStatus(score=0.0),
        receptions={},
    )


def _hour(ruler: str) -> PlanetaryHourResult:
    start = datetime(2024, 3, 21, 11, 0, tzinfo=UTC)
    end = datetime(2024, 3, 21, 12, 0, tzinfo=UTC)
    return PlanetaryHourResult(
        ruler=ruler,
        index=3,
        start=start,
        end=end,
        sunrise=datetime(2024, 3, 21, 6, 0, tzinfo=UTC),
        sunset=datetime(2024, 3, 21, 18, 0, tzinfo=UTC),
        next_sunrise=datetime(2024, 3, 22, 6, 0, tzinfo=UTC),
        day_ruler="Sun",
        sequence=(ruler,) * 24,
    )


def _chart_with_positions(positions: dict[str, BodyPosition]) -> NatalChart:
    houses = HousePositions(
        system="P",
        cusps=tuple(float(i * 30) for i in range(12)),
        ascendant=0.0,
        midheaven=90.0,
    )
    return NatalChart(
        moment=datetime(2024, 3, 21, 12, tzinfo=UTC),
        location=ChartLocation(latitude=0.0, longitude=0.0),
        julian_day=0.0,
        positions=positions,
        houses=houses,
        aspects=(),
    )


def test_void_moon_saturn_and_south_node_flags(monkeypatch) -> None:
    original = radicality_module.aspect_between

    def _no_moon_contacts(chart, body_a, body_b, profile):
        if "Moon" in {body_a, body_b}:
            return None
        return original(chart, body_a, body_b, profile)

    monkeypatch.setattr(radicality_module, "aspect_between", _no_moon_contacts)
    profile = _profile()
    positions = {
        "Moon": _body("Moon", 10.0, 12.0),
        "Sun": _body("Sun", 210.0, 0.9),
        "Saturn": _body("Saturn", 185.0, 0.04),
        "True Node": _body("True Node", 180.0, -0.05),
        "Mercury": _body("Mercury", 75.0, 0.5),
    }
    chart = _chart_with_positions(positions)
    sigset = SignificatorSet(
        querent=_significator("Mars", 5.0, 1),
        quesited=_significator("Venus", 200.0, 7),
        moon=_significator("Moon", 10.0, 3),
        co_significators=(),
        is_day_chart=True,
    )
    hour = _hour("Saturn")

    checks = run_checks(chart, profile, sigset, hour)
    flagged = {check.code: check for check in checks if check.flag}

    assert "hour_agreement" in flagged
    assert "asc_early" in flagged
    assert "moon_voc" in flagged and flagged["moon_voc"].caution_weight == -8.0
    assert "saturn_in_7th" in flagged
    assert "south_node_asc" in flagged


def test_combustion_and_missing_node_handling() -> None:
    profile = _profile()
    positions = {
        "Moon": _body("Moon", 28.0, 12.5),
        "Sun": _body("Sun", 22.0, 1.0),
        "Mercury": _body("Mercury", 20.0, 1.5),
        "Venus": _body("Venus", 140.0, 0.8),
    }
    chart = _chart_with_positions(positions)
    sigset = SignificatorSet(
        querent=_significator("Mercury", 20.0, 1),
        quesited=_significator("Jupiter", 210.0, 7),
        moon=_significator("Moon", 28.0, 3),
        co_significators=(),
        is_day_chart=True,
    )
    hour = _hour("Mercury")

    checks = run_checks(chart, profile, sigset, hour)
    codes = {check.code: check for check in checks}

    assert codes["hour_agreement"].flag is False
    assert codes["hour_agreement"].caution_weight == 0.0
    assert "moon_voc" in codes and codes["moon_voc"].flag is False
    assert "south_node_asc" not in codes
    assert codes["querent_combust"].flag is True
    assert codes["querent_combust"].caution_weight == -6.0
