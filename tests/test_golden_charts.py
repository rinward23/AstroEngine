from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from astroengine.chart.natal import DEFAULT_BODIES
from astroengine.core.angles import signed_delta
from astroengine.core.time import ensure_utc
from astroengine.ephemeris import EphemerisAdapter

pytest.importorskip(
    "swisseph", reason="pyswisseph is required to verify golden chart ephemerides"
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "golden_charts"
TOLERANCE_DEG = 1e-3


def _load_fixture(path: Path) -> dict:
    return json.loads(path.read_text())


@pytest.mark.parametrize("fixture", sorted(FIXTURE_DIR.glob("*.json")))
def test_golden_chart_longitudes_within_millidegree(fixture: Path) -> None:
    data = _load_fixture(fixture)
    adapter = EphemerisAdapter()
    moment = ensure_utc(datetime.fromisoformat(data["datetime"].replace("Z", "+00:00")))

    samples: dict[str, float] = {}
    for body_name, expected in data["bodies"].items():
        code = _body_code(body_name)
        sample = adapter.sample(code, moment)
        samples[body_name] = float(sample.longitude)
        delta = abs(signed_delta(sample.longitude - expected["longitude"]))
        assert delta <= TOLERANCE_DEG

    expected_aspects = data.get("aspects", {})
    for key, expected_value in expected_aspects.items():
        name_a, name_b = key.split("-")
        actual = signed_delta(samples[name_a] - samples[name_b])
        assert abs(actual - expected_value) <= TOLERANCE_DEG


def _body_code(name: str) -> int:
    canonical = name.capitalize()
    try:
        return DEFAULT_BODIES[canonical]
    except KeyError as exc:  # pragma: no cover - defensive for fixture drift
        raise KeyError(f"Unsupported body in golden chart: {name}") from exc
