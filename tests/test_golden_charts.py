from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from astroengine.chart.natal import DEFAULT_BODIES, build_body_map
from astroengine.core.angles import signed_delta
from astroengine.core.time import ensure_utc
from astroengine.ephemeris import EphemerisAdapter

pytest.importorskip(
    "swisseph", reason="pyswisseph is required to verify golden chart ephemerides"
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "golden_charts"
TOLERANCE_DEG = 1e-3

_BODY_MAP = build_body_map({"true_node": True})
_BODY_ALIASES = {name.casefold(): name for name in _BODY_MAP}
_BODY_ALIASES.update(
    {
        "true_node": "True Node",
        "mean_node": "Mean Node",
        "north node": "True Node",
        "south node": "True South Node",
    }
)


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
    key = name.casefold()
    canonical = _BODY_ALIASES.get(key)
    if canonical is None and key in DEFAULT_BODIES:
        canonical = key.capitalize()
    if canonical is None:
        raise KeyError(f"Unsupported body in golden chart: {name}")
    if canonical in DEFAULT_BODIES:
        return DEFAULT_BODIES[canonical]
    try:
        return _BODY_MAP[canonical]
    except KeyError as exc:  # pragma: no cover - defensive for fixture drift
        raise KeyError(f"Unsupported body in golden chart: {name}") from exc
