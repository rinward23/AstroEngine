from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from astroengine.ephemeris import EphemerisAdapter

_swe = pytest.importorskip("swisseph")

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ephemeris" / "sun_moon_2024.json"
GOLDEN_FIXTURES: list[dict[str, Any]] = json.loads(FIXTURE_PATH.read_text())

BODY_IDS = {
    "sun": _swe.SUN,
    "moon": _swe.MOON,
}

ADAPTER = EphemerisAdapter()

_FIELD_TOLERANCE = {
    "jd_tt": 5e-10,
    "jd_utc": 5e-10,
    "longitude": 5e-7,
    "latitude": 5e-7,
    "distance": 5e-9,
    "speed_longitude": 5e-7,
    "speed_latitude": 5e-7,
    "speed_distance": 5e-9,
    "right_ascension": 5e-7,
    "declination": 5e-7,
    "speed_right_ascension": 5e-7,
    "speed_declination": 5e-7,
    "delta_t_seconds": 5e-7,
}


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


@pytest.mark.quick
@pytest.mark.parametrize("fixture", GOLDEN_FIXTURES, ids=lambda row: row["timestamp"])
def test_ephemeris_samples_match_golden(fixture: dict[str, Any]) -> None:
    """EphemerisAdapter reproduces recorded Swiss ephemeris samples."""

    moment = _parse_timestamp(fixture["timestamp"])
    for body_name, expected in fixture["bodies"].items():
        body_id = BODY_IDS[body_name]
        sample = ADAPTER.sample(body_id, moment)
        for field, tolerance in _FIELD_TOLERANCE.items():
            observed = getattr(sample, field)
            assert math.isfinite(observed)
            assert math.isclose(observed, expected[field], abs_tol=tolerance)
