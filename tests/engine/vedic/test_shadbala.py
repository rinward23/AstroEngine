from __future__ import annotations

from datetime import UTC, datetime

import pytest

pytest.importorskip(
    "swisseph",
    reason="pyswisseph not installed; install extras with `pip install -e .[ephem,providers]`.",
)

from astroengine.engine.vedic import build_context, compute_shadbala


def _sample_context():
    moment = datetime(2024, 3, 20, 12, 0, tzinfo=UTC)
    return build_context(moment, latitude=28.6139, longitude=77.2090, ayanamsa="lahiri")


def test_shadbala_report_contains_visible_planets():
    context = _sample_context()
    report = compute_shadbala(context)

    for planet in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"):
        score = report.score_for(planet)
        assert score is not None, f"Missing score for {planet}"
        assert set(score.factors) == {
            "uccha_bala",
            "kendra_bala",
            "dig_bala",
            "naisargika_bala",
            "cheshta_bala",
        }
        assert {"saptavargaja_bala", "kalabala", "drik_bala"}.issubset(set(score.missing))
        for factor in score.factors.values():
            assert 0.0 <= factor.value <= factor.maximum <= 60.0
        assert score.total == sum(factor.value for factor in score.factors.values())


def test_shadbala_uccha_bala_matches_expected_value():
    context = _sample_context()
    report = compute_shadbala(context)
    sun = report.score_for("Sun")
    assert sun is not None
    uccha = sun.factors["uccha_bala"].value
    # 20 March 2024 places the Sun close to its exaltation in Aries.
    assert round(uccha, 2) == round(48.72, 2)
