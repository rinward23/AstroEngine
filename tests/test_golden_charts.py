from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from astroengine.core.angles import signed_delta
from astroengine.core.time import ensure_utc
from astroengine.ephemeris import EphemerisAdapter

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "golden_charts"


def _load_fixture(path: Path) -> dict:
    return json.loads(path.read_text())


@pytest.mark.parametrize("fixture", sorted(FIXTURE_DIR.glob("*.json")))
def test_golden_chart_longitudes_within_arcminute(fixture: Path) -> None:
    data = _load_fixture(fixture)
    adapter = EphemerisAdapter()
    moment = ensure_utc(datetime.fromisoformat(data["datetime"].replace("Z", "+00:00")))
    for body_name, expected in data["bodies"].items():
        sample = adapter.sample(_body_code(body_name), moment)
        delta = abs(signed_delta(sample.longitude - expected["longitude"]))
        assert delta <= 1.0 / 60.0


def _body_code(name: str) -> int:
    mapping = {"sun": 0, "moon": 1, "mercury": 2, "venus": 3, "mars": 4}
    return mapping[name]
