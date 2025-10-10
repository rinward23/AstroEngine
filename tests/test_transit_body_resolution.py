from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import astroengine.core.transit_engine as transit_engine
from astroengine.chart.config import ChartConfig
from astroengine.chart.natal import BODY_EXPANSIONS, build_body_map
from astroengine.ephemeris.swisseph_adapter import VariantConfig


class _FakeAdapter:
    def __init__(self, nodes_variant: str = "mean", lilith_variant: str = "mean") -> None:
        self.chart_config = ChartConfig(
            nodes_variant=nodes_variant,
            lilith_variant=lilith_variant,
        )
        self._variant_config = VariantConfig(
            nodes_variant=self.chart_config.nodes_variant,
            lilith_variant=self.chart_config.lilith_variant,
        )

    def julian_day(self, moment: datetime) -> float:
        return 0.0

    def body_position(self, jd: float, code: int, body_name: str | None = None):
        return SimpleNamespace(longitude=float(code % 360))


class _FakeEngine:
    def __init__(self, adapter: _FakeAdapter) -> None:
        self.adapter = adapter
        self.scanned_codes: list[int] = []

    def scan_longitude_crossing(
        self,
        body: int,
        reference_longitude: float,
        aspect_angle_deg: float,
        start: datetime,
        end: datetime,
        **_: object,
    ) -> list[SimpleNamespace]:
        self.scanned_codes.append(int(body))
        return [
            SimpleNamespace(
                timestamp=start,
                metadata={
                    "sample": {
                        "longitude": reference_longitude,
                        "speed_longitude": 0.0,
                    }
                },
                orb=0.0,
            )
        ]


def _patch_engines(monkeypatch, adapter: _FakeAdapter, engine: _FakeEngine) -> None:
    def fake_get_default_adapter(cls):  # pragma: no cover - helper
        return adapter

    def fake_with_default_adapter(cls, config=None, *, engine_config=None):  # pragma: no cover
        return engine

    monkeypatch.setattr(
        transit_engine.SwissEphemerisAdapter,
        "get_default_adapter",
        classmethod(fake_get_default_adapter),
    )
    monkeypatch.setattr(
        transit_engine.TransitEngine,
        "with_default_adapter",
        classmethod(fake_with_default_adapter),
    )


def test_scan_transits_resolves_extended_bodies(monkeypatch) -> None:
    adapter = _FakeAdapter()
    engine = _FakeEngine(adapter)
    _patch_engines(monkeypatch, adapter, engine)

    catalog = build_body_map({key: True for key in BODY_EXPANSIONS})
    expected_ceres_code = int(catalog["Ceres"])
    expected_mean_node_code = int(catalog["Mean Node"])

    hits = transit_engine.scan_transits(
        natal_ts="2000-01-01T00:00:00Z",
        start_ts="2024-01-01T00:00:00Z",
        end_ts="2024-01-02T00:00:00Z",
        bodies=["Ceres", "Mean Node"],
        aspects=["conjunction"],
    )

    assert hits, "expected stub hits to be returned"
    moving_names = {hit.moving for hit in hits}
    assert {"Ceres", "Mean Node"}.issubset(moving_names)

    scanned_codes = set(engine.scanned_codes)
    assert expected_ceres_code in scanned_codes
    assert expected_mean_node_code in scanned_codes


def test_scan_transits_respects_node_variant(monkeypatch) -> None:
    catalog = build_body_map({key: True for key in BODY_EXPANSIONS})

    adapter = _FakeAdapter(nodes_variant="true")
    engine = _FakeEngine(adapter)
    _patch_engines(monkeypatch, adapter, engine)

    hits = transit_engine.scan_transits(
        natal_ts="2000-01-01T00:00:00Z",
        start_ts="2024-01-01T00:00:00Z",
        end_ts="2024-01-02T00:00:00Z",
        bodies=["Node"],
        aspects=["conjunction"],
    )

    assert hits
    moving_names = {hit.moving for hit in hits}
    assert "True Node" in moving_names

    scanned_codes = set(engine.scanned_codes)
    expected_true_code = int(catalog["True Node"])
    assert expected_true_code in scanned_codes
