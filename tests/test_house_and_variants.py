from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest

swe = pytest.importorskip("swisseph")

from astroengine.chart.config import ChartConfig
from astroengine.ephemeris import SwissEphemerisAdapter


def test_house_fallback_records_whole_sign(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = SwissEphemerisAdapter(chart_config=ChartConfig(house_system="placidus"))
    jd = adapter.julian_day(datetime(2024, 1, 1, tzinfo=UTC))

    original = swe.houses_ex

    def patched_houses_ex(jd_ut: float, lat: float, lon: float, code):
        token = code.decode("ascii") if isinstance(code, (bytes, bytearray)) else str(code)
        if token == "P":
            raise RuntimeError("forced failure for placidus")
        return original(jd_ut, lat, lon, code)

    monkeypatch.setattr(swe, "houses_ex", patched_houses_ex)

    houses = adapter.houses(jd, latitude=0.0, longitude=0.0, system="placidus")

    assert houses.system_name == "whole_sign"
    assert houses.fallback_from == "placidus"
    assert adapter._last_house_metadata is not None  # type: ignore[attr-defined]
    assert adapter._last_house_metadata["fallback"]["from"] == "placidus"  # type: ignore[index]


def test_variant_selection_changes_positions() -> None:
    moment = datetime(2024, 1, 1, tzinfo=UTC)
    mean_adapter = SwissEphemerisAdapter(
        chart_config=ChartConfig(nodes_variant="mean", lilith_variant="mean")
    )
    true_adapter = SwissEphemerisAdapter(
        chart_config=ChartConfig(nodes_variant="true", lilith_variant="true")
    )

    jd = mean_adapter.julian_day(moment)

    mean_node = mean_adapter.body_position(jd, swe.MEAN_NODE, body_name="mean_node")
    true_node = true_adapter.body_position(jd, swe.TRUE_NODE, body_name="true_node")
    south_node = true_adapter.body_position(jd, swe.TRUE_NODE, body_name="south_node")

    assert not math.isclose(mean_node.longitude, true_node.longitude, abs_tol=1e-6)
    assert math.isclose(
        (south_node.longitude - true_node.longitude) % 360.0,
        180.0,
        abs_tol=1e-6,
    )
    assert math.isclose(south_node.latitude, -true_node.latitude, rel_tol=1e-6)

    mean_lilith = mean_adapter.body_position(jd, swe.MEAN_APOG, body_name="mean_lilith")
    true_lilith = true_adapter.body_position(jd, swe.OSCU_APOG, body_name="true_lilith")
    assert not math.isclose(mean_lilith.longitude, true_lilith.longitude, abs_tol=1e-6)
