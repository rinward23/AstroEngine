from datetime import UTC, datetime

import pytest

swe = pytest.importorskip(
    "swisseph",
    reason="pyswisseph not installed; install extras with `.[providers]`",
)

from astroengine.engine.vedic import (
    PRIMARY_AYANAMSAS,
    SIDEREAL_PRESETS,
    ayanamsa_value,
    available_ayanamsas,
    swe_ayanamsa,
)


def _jd(moment: datetime) -> float:
    return swe().julday(moment.year, moment.month, moment.day, moment.hour + moment.minute / 60.0)


def test_ayanamsa_matches_swisseph():
    moments = [
        datetime(1990, 5, 4, 12, 30, tzinfo=UTC),
        datetime(2005, 1, 1, 0, 0, tzinfo=UTC),
        datetime(2024, 6, 21, 18, 0, tzinfo=UTC),
    ]
    for moment in moments:
        jd = _jd(moment)
        for preset, info in SIDEREAL_PRESETS.items():
            _flags, expected = swe().get_ayanamsa_ex_ut(jd, info.swe_mode)
            result = ayanamsa_value(preset, moment)
            assert abs(result - expected) < 1e-4


def test_primary_presets_and_helper_metadata():
    presets = set(available_ayanamsas())
    for preset in PRIMARY_AYANAMSAS:
        assert preset in presets

    moment = datetime(2024, 1, 15, 6, 45, tzinfo=UTC)
    for preset in PRIMARY_AYANAMSAS:
        payload = swe_ayanamsa(moment, preset)
        assert payload["ayanamsa"] == preset.value
        assert payload["preset"] == preset
        assert payload["swe_mode"] == SIDEREAL_PRESETS[preset].swe_mode
        expected = ayanamsa_value(preset, moment)
        assert abs(payload["ayanamsa_degrees"] - expected) < 1e-6
