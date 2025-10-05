from __future__ import annotations

import math

import pytest

from astroengine.analysis.fixed_stars import load_catalog, star_hits


EXPECTED_STARS = {
    "Regulus",
    "Spica",
    "Aldebaran",
    "Antares",
    "Fomalhaut",
    "Sirius",
    "Betelgeuse",
    "Rigel",
}


def test_load_catalog_contains_seed_entries() -> None:
    stars = load_catalog()
    names = {star.name for star in stars}
    assert EXPECTED_STARS.issubset(names)
    regulus = next(star for star in stars if star.name == "Regulus")
    assert math.isclose(regulus.lon_deg, 149.8292, rel_tol=1e-6)
    assert math.isclose(regulus.lat_deg, 0.4648, rel_tol=1e-6)


def test_star_hits_matches_regulus_within_orb() -> None:
    hits = star_hits(150.0, orbis=1.0)
    match = {name: delta for name, delta in hits}
    assert "Regulus" in match
    assert abs(match["Regulus"]) < 1.0


def test_star_hits_rejects_negative_orb() -> None:
    with pytest.raises(ValueError):
        star_hits(120.0, orbis=-0.5)
