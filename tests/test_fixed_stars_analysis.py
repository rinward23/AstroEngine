from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import pytest

from astroengine.analysis.fixed_stars import (
    load_catalog,
    star_declination_aspects,
    star_hits,
    star_parans,
)

EXPECTED_STARS = {
    "Regulus",
    "Spica",
    "Aldebaran",
    "Antares",
    "Fomalhaut",
    "Sirius",
    "Betelgeuse",
    "Rigel",
    "Canopus",
    "Arcturus",
    "Vega",
    "Altair",
    "Procyon",
}

FK6_SAMPLE = (
    "Sirius",
    "Canopus",
    "Arcturus",
    "Regulus",
    "Spica",
)


def test_load_catalog_contains_seed_entries() -> None:
    stars = load_catalog()
    names = {star.name for star in stars}
    assert EXPECTED_STARS.issubset(names)
    assert len(stars) >= 280
    regulus = next(star for star in stars if star.name == "Regulus")
    assert math.isclose(regulus.lon_deg, 149.8292, rel_tol=1e-6)
    assert math.isclose(regulus.lat_deg, 0.4648, rel_tol=1e-6)
    assert math.isclose(regulus.declination_deg, 11.9659, rel_tol=1e-4)


def test_star_hits_match_fk6_longitudes() -> None:
    stars = {star.name: star for star in load_catalog()}
    for name in FK6_SAMPLE:
        star = stars[name]
        hits = star_hits(star.lon_deg, orbis=0.01)
        assert any(hit_name == name and abs(delta) <= 1e-6 for hit_name, delta in hits)


def test_star_hits_matches_regulus_within_orb() -> None:
    hits = star_hits(150.0, orbis=1.0)
    match = {name: delta for name, delta in hits}
    assert "Regulus" in match
    assert abs(match["Regulus"]) < 1.0


def test_star_hits_rejects_negative_orb() -> None:
    with pytest.raises(ValueError):
        star_hits(120.0, orbis=-0.5)


def test_star_declination_aspects_detects_parallel() -> None:
    stars = load_catalog()
    regulus = next(star for star in stars if star.name == "Regulus")
    aspects = star_declination_aspects({"Sun": regulus.dec_deg + 0.05}, 0.2)
    assert aspects
    assert any(a.star == "Regulus" and a.kind == "parallel" for a in aspects)


def test_star_declination_aspects_detects_contraparallel() -> None:
    stars = load_catalog()
    spica = next(star for star in stars if star.name == "Spica")
    aspects = star_declination_aspects({"Venus": -spica.dec_deg + 0.05}, 0.2)
    assert aspects
    assert any(a.star == "Spica" and a.kind == "contraparallel" for a in aspects)


def test_star_parans_returns_events_when_ra_matches() -> None:
    catalog = load_catalog()
    sirius = next(star for star in catalog if star.name == "Sirius")

    def provider_radec(moment: datetime, body: str) -> tuple[float, float]:
        assert body == "Sun"
        return sirius.ra_deg, sirius.dec_deg

    start = datetime(2024, 1, 1, tzinfo=UTC)
    events = star_parans(
        start,
        start + timedelta(days=1),
        (0.0, 0.0),
        ["Sun"],
        provider_radec,
        event_pairs=[("culminate", "culminate")],
        magnitude_limit=2.0,
        tolerance_minutes=5.0,
    )
    assert events
    first = events[0]
    assert first["star"] == "Sirius"
    assert first["planet"] == "Sun"
    assert first["star_event"] == "culminate"
    assert first["planet_event"] == "culminate"
    assert first["dt_diff_min"] <= 5.0
