from __future__ import annotations

from datetime import UTC, datetime

from astroengine.chart.natal import ChartLocation, NatalChart
from astroengine.engine.horary import judgement as judgement_module
from astroengine.engine.horary.judgement import score_testimonies
from astroengine.engine.horary.models import (
    DignityStatus,
    JudgementContribution,
    RadicalityCheck,
    Significator,
    SignificatorSet,
)
from astroengine.engine.horary.profiles import HoraryProfile
from astroengine.engine.traditional.models import ChartCtx, SectInfo
from astroengine.ephemeris.swisseph_adapter import BodyPosition, HousePositions


_DEF_ORBS = {
    "by_aspect": {
        "conjunction": 8.0,
        "sextile": 6.0,
        "square": 6.0,
        "trine": 6.0,
        "opposition": 8.0,
    },
    "by_body_mult": {
        "Moon": 1.5,
    },
}


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


def _profile(name: str = "Unit") -> HoraryProfile:
    return HoraryProfile(
        name=name,
        orbs=_DEF_ORBS,
        dignities={
            "domicile": 5.0,
            "exaltation": 4.0,
            "triplicity": 3.0,
            "term": 2.0,
            "face": 1.0,
            "detriment": -5.0,
            "fall": -4.0,
        },
        radicality={},
        testimony_weights={
            "applying_with_reception": 18.0,
            "applying_no_reception": 12.0,
            "translation": 9.0,
            "collection": 7.0,
            "prohibition": -11.0,
            "moon_next_good": 5.0,
            "malefic_on_angle": -8.0,
        },
        classification_thresholds={
            "yes": 40.0,
            "qualified": 20.0,
            "weak": 10.0,
        },
    )


def _chart_ctx() -> ChartCtx:
    positions = {
        "Venus": _body("Venus", 20.0, 1.1),
        "Mars": _body("Mars", 76.0, 0.6),
        "Moon": _body("Moon", 28.0, 12.5),
        "Jupiter": _body("Jupiter", 88.0, 0.3),
        "Saturn": _body("Saturn", 92.0, 0.05),
        "Sun": _body("Sun", 5.0, 1.0),
    }
    houses = HousePositions(
        system="P",
        cusps=tuple(float(i * 30) for i in range(12)),
        ascendant=0.0,
        midheaven=90.0,
    )
    natal = NatalChart(
        moment=datetime(2024, 3, 21, 12, tzinfo=UTC),
        location=ChartLocation(latitude=0.0, longitude=0.0),
        julian_day=0.0,
        positions=positions,
        houses=houses,
        aspects=(),
    )
    sect = SectInfo(
        is_day=True,
        luminary_of_sect="Sun",
        malefic_of_sect="Saturn",
        benefic_of_sect="Jupiter",
        sun_altitude_deg=30.0,
    )
    return ChartCtx(natal=natal, sect=sect, lots={})


def _sigset_positive() -> SignificatorSet:
    querent = Significator(
        body="Venus",
        role="querent",
        longitude=20.0,
        latitude=0.0,
        speed=1.1,
        house=1,
        dignities=DignityStatus(score=6.0),
        receptions={"Mars": ("domicile",)},
    )
    quesited = Significator(
        body="Mars",
        role="quesited",
        longitude=76.0,
        latitude=0.0,
        speed=0.6,
        house=10,
        dignities=DignityStatus(score=2.0),
        receptions={"Venus": ("domicile",)},
    )
    moon = Significator(
        body="Moon",
        role="moon",
        longitude=28.0,
        latitude=0.0,
        speed=12.5,
        house=3,
        dignities=DignityStatus(score=0.0),
        receptions={},
    )
    return SignificatorSet(
        querent=querent,
        quesited=quesited,
        moon=moon,
        co_significators=(),
        is_day_chart=True,
    )


def _sigset_negative() -> SignificatorSet:
    querent = Significator(
        body="Venus",
        role="querent",
        longitude=15.0,
        latitude=0.0,
        speed=0.9,
        house=1,
        dignities=DignityStatus(score=-3.0),
        receptions={},
    )
    quesited = Significator(
        body="Mars",
        role="quesited",
        longitude=160.0,
        latitude=0.0,
        speed=0.5,
        house=7,
        dignities=DignityStatus(score=-2.0),
        receptions={},
    )
    moon = Significator(
        body="Moon",
        role="moon",
        longitude=11.0,
        latitude=0.0,
        speed=12.0,
        house=3,
        dignities=DignityStatus(score=0.0),
        receptions={},
    )
    return SignificatorSet(
        querent=querent,
        quesited=quesited,
        moon=moon,
        co_significators=(),
        is_day_chart=True,
    )


def test_score_testimonies_aggregates_contributions(monkeypatch) -> None:
    monkeypatch.setattr(
        judgement_module,
        "_moon_next_aspect",
        lambda *args, **kwargs: ("Jupiter", 0.25),
    )
    ctx = _chart_ctx()
    profile = _profile()
    sigset = _sigset_positive()

    checks = [
        RadicalityCheck(
            code="hour_agreement",
            flag=False,
            reason="Hour ruler agrees",
            caution_weight=2.5,
            data={},
        )
    ]

    result = score_testimonies(ctx.natal, sigset, checks, profile)

    assert result.score == sum(entry.score for entry in result.contributions)
    codes = {entry.code for entry in result.contributions}
    assert {"applying_with_reception", "querent_dignity", "quesited_dignity"}.issubset(codes)
    assert "moon_next_good" in codes and "malefic_on_angle" in codes
    dignities = {
        entry.code: entry for entry in result.contributions if entry.code.endswith("_dignity")
    }
    assert dignities["querent_dignity"].value == sigset.querent.dignities.score
    assert dignities["quesited_dignity"].value == sigset.quesited.dignities.score
    ordered = list(result.contributions)
    for first, second in zip(ordered, ordered[1:]):
        assert first.score >= second.score


def test_negative_totals_classify_no(monkeypatch) -> None:
    monkeypatch.setattr(
        judgement_module,
        "_moon_next_aspect",
        lambda *args, **kwargs: ("Saturn", 0.5),
    )
    ctx = _chart_ctx()
    profile = _profile("NegativeCase")
    sigset = _sigset_negative()

    negative_positions = dict(ctx.natal.positions)
    negative_positions.update(
        {
            "Mars": _body("Mars", 160.0, 0.5),
            "Saturn": _body("Saturn", 100.0, 0.05),
            "Jupiter": _body("Jupiter", 250.0, 0.2),
            "Moon": _body("Moon", 11.0, 12.0),
        }
    )
    negative_chart = NatalChart(
        moment=ctx.natal.moment,
        location=ctx.natal.location,
        julian_day=ctx.natal.julian_day,
        positions=negative_positions,
        houses=ctx.natal.houses,
        aspects=ctx.natal.aspects,
    )

    penalties = [
        RadicalityCheck(
            code="moon_voc",
            flag=True,
            reason="Void of course",
            caution_weight=-5.0,
            data={},
        )
    ]

    result = score_testimonies(negative_chart, sigset, penalties, profile)

    assert result.classification == "No"
    codes = {entry.code for entry in result.contributions}
    assert "malefic_on_angle" in codes
    moon_entry = next(entry for entry in result.contributions if entry.code == "moon_next_good")
    assert moon_entry.value == -1.0
