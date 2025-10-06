"""Unit tests for Vedic yoga detection logic."""

from __future__ import annotations

from datetime import UTC, datetime

from astroengine.chart.config import ChartConfig
from astroengine.chart.natal import ChartLocation, NatalChart
from astroengine.engine.vedic import VedicChartContext, analyze_yogas
from astroengine.ephemeris.swisseph_adapter import (
    BodyPosition,
    HousePositions,
    SwissEphemerisAdapter,
)


def _body_position(name: str, longitude: float, *, retrograde: bool = False) -> BodyPosition:
    speed = -0.1 if retrograde else 0.1
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


def _context(asc_sign_index: int, placements: dict[str, float]) -> VedicChartContext:
    asc_start = (asc_sign_index % 12) * 30.0
    cusps = tuple((asc_start + (i * 30.0)) % 360.0 for i in range(12))
    houses = HousePositions(
        system="whole_sign",
        cusps=cusps,
        ascendant=asc_start + 5.0,
        midheaven=(asc_start + 90.0) % 360.0,
    )
    positions = {name: _body_position(name, longitude) for name, longitude in placements.items()}
    chart = NatalChart(
        moment=datetime(2023, 1, 1, tzinfo=UTC),
        location=ChartLocation(latitude=0.0, longitude=0.0),
        julian_day=0.0,
        positions=positions,
        houses=houses,
        aspects=(),
        zodiac="sidereal",
        ayanamsa="lahiri",
        metadata={},
    )
    config = ChartConfig(zodiac="sidereal", ayanamsha="lahiri", house_system="whole_sign")
    adapter = SwissEphemerisAdapter.from_chart_config(config)
    return VedicChartContext(chart=chart, config=config, adapter=adapter)


def _names(results) -> set[str]:
    return {result.name for result in results}


def test_panch_mahapurusha_detects_bhadra() -> None:
    ctx = _context(
        asc_sign_index=2,  # Gemini ascendant
        placements={
            "Sun": 210.0,
            "Moon": 330.0,
            "Mercury": 155.0,  # Virgo 4th house
            "Venus": 45.0,
            "Mars": 10.0,
            "Jupiter": 80.0,
            "Saturn": 300.0,
        },
    )
    results = analyze_yogas(ctx)
    names = _names(results)
    assert "Bhadra Yoga" in names
    bhadra = next(result for result in results if result.name == "Bhadra Yoga")
    participant = bhadra.participants[0]
    assert participant.name == "Mercury"
    assert participant.sign == "Virgo"
    assert participant.house == 4
    assert bhadra.checks["dignity"]["domicile"]
    assert bhadra.checks["dignity"]["exaltation"]


def test_neech_bhang_detects_cancellation() -> None:
    ctx = _context(
        asc_sign_index=0,  # Aries ascendant
        placements={
            "Sun": 260.0,
            "Moon": 10.0,  # dispositor in lagna (kendra)
            "Mercury": 320.0,
            "Venus": 50.0,
            "Mars": 95.0,  # Cancer debilitation
            "Jupiter": 240.0,
            "Saturn": 300.0,
        },
    )
    results = analyze_yogas(ctx)
    names = _names(results)
    assert "Neech Bhang Raj Yoga" in names
    yoga = next(result for result in results if result.name == "Neech Bhang Raj Yoga")
    involved = {p.name for p in yoga.participants}
    assert {"Mars", "Moon"} <= involved
    assert "Dispositor in kendra from ascendant" in yoga.notes


def test_kemadruma_flags_isolated_moon() -> None:
    ctx = _context(
        asc_sign_index=0,
        placements={
            "Sun": 0.0,
            "Moon": 120.0,
            "Mercury": 250.0,
            "Venus": 210.0,
            "Mars": 310.0,
            "Jupiter": 40.0,
            "Saturn": 300.0,
        },
    )
    results = analyze_yogas(ctx)
    assert "Kemadruma Yoga" in _names(results)
    kemadruma = next(result for result in results if result.name == "Kemadruma Yoga")
    assert kemadruma.checks["absence"]["adjacent_planets"] == ()


def test_daridra_detects_weak_eleventh_lord() -> None:
    ctx = _context(
        asc_sign_index=0,
        placements={
            "Sun": 15.0,
            "Moon": 40.0,
            "Mercury": 80.0,
            "Venus": 130.0,
            "Mars": 170.0,
            "Jupiter": 260.0,
            "Saturn": 210.0,  # 8th house Scorpio
        },
    )
    results = analyze_yogas(ctx)
    assert "Daridra Yoga" in _names(results)
    daridra = next(result for result in results if result.name == "Daridra Yoga")
    participant = daridra.participants[0]
    assert participant.name == "Saturn"
    assert participant.house == 8
    assert not daridra.checks["dignity"]["domicile"]


def test_bhandhan_requires_malefics_and_weak_lagna_lord() -> None:
    ctx = _context(
        asc_sign_index=4,  # Leo ascendant
        placements={
            "Sun": 100.0,  # 12th house Cancer
            "Moon": 40.0,
            "Mercury": 140.0,
            "Venus": 190.0,
            "Mars": 210.0,  # 4th house Scorpio
            "Jupiter": 260.0,
            "Saturn": 310.0,  # 7th house Aquarius
        },
    )
    results = analyze_yogas(ctx)
    assert "Bhandhan Yoga" in _names(results)
    bhandhan = next(result for result in results if result.name == "Bhandhan Yoga")
    malefics = {name for name, _ in bhandhan.checks["strength"]["malefics_in_kendra"]}
    assert {"Mars", "Saturn"} == malefics
    assert bhandhan.checks["strength"]["lagna_lord_house"] == 12
