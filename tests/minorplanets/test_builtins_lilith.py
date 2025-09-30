from __future__ import annotations

from datetime import datetime, timezone

import pytest

from astroengine.engine.minorplanets import builtins


def test_lilith_variants_diverge() -> None:
    moment = datetime(2024, 1, 1, tzinfo=timezone.utc)
    mean = builtins.lilith_mean(moment)
    true = builtins.lilith_true(moment)
    assert 0.0 <= mean < 360.0
    assert 0.0 <= true < 360.0
    assert abs(mean - true) > 0.1


def test_lilith_progression_monotonic() -> None:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    first = builtins.lilith_mean(base)
    second = builtins.lilith_mean(base.replace(day=2))
    assert first != second


def test_curated_minor_planets_cover_core_set() -> None:
    designations = {body.designation for body in builtins.CURATED_MINOR_PLANETS}
    expected = {
        "2060 Chiron",
        "136199 Eris",
        "90377 Sedna",
        "136108 Haumea",
        "136472 Makemake",
        "1 Ceres",
        "2 Pallas",
        "3 Juno",
        "4 Vesta",
        "mean_lilith",
        "true_lilith",
    }
    assert expected.issubset(designations)


def test_default_minor_body_orbs_include_overrides() -> None:
    assert pytest.approx(builtins.DEFAULT_MINOR_BODY_ORBS["large_numbered"]) == 1.5
    assert pytest.approx(builtins.DEFAULT_MINOR_BODY_ORBS["default"]) == 1.0
