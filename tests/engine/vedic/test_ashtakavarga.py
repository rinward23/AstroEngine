from __future__ import annotations

from datetime import UTC, datetime

import pytest

pytest.importorskip(
    "swisseph",
    reason="pyswisseph not installed; install extras with `pip install -e .[ephem,providers]`.",
)

from astroengine.engine.vedic import (
    AshtakavargaSet,
    Bhinnashtakavarga,
    build_context,
    compute_bhinnashtakavarga,
    compute_sarvashtakavarga,
)


def _sample_context():
    moment = datetime(2024, 3, 20, 12, 0, tzinfo=UTC)
    return build_context(moment, latitude=28.6139, longitude=77.2090, ayanamsa="lahiri")


def test_bhinnashtakavarga_distribution():
    context = _sample_context()
    bav = compute_bhinnashtakavarga(context)

    assert set(bav) == {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"}
    for planet, sheet in bav.items():
        assert isinstance(sheet, Bhinnashtakavarga)
        assert sheet.planet == planet
        assert len(sheet.bindus) == 12
        assert sheet.total == sum(sheet.bindus)
        assert all(0 <= value <= 8 for value in sheet.bindus)


def test_sarvashtakavarga_matches_sum_of_bhinnashtakavarga():
    context = _sample_context()
    bav = compute_bhinnashtakavarga(context)
    sarva = compute_sarvashtakavarga(bav)

    assert isinstance(sarva, dict)
    assert len(sarva) == 12
    total_bindus = sum(entry.total for entry in bav.values())
    assert sum(sarva.values()) == total_bindus

    aggregate = AshtakavargaSet(sarva=sarva, bhinna=bav)
    # Aries index (0) should match value in aggregate helper.
    assert aggregate.bindu_for_sign(0) == sarva[0]
