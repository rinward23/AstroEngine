"""Regression coverage for dynamic Swiss Ephemeris availability."""

from __future__ import annotations

import pytest

from astroengine.ephemeris import adapter as adapter_module
from astroengine.ephemeris import swe as swe_module


class DummySweModule:
    """Minimal Swiss Ephemeris implementation for adapter tests."""

    FLG_SPEED = 0x01
    FLG_TOPOCTR = 0x02
    FLG_SIDEREAL = 0x04
    SIDM_LAHIRI = 0x10

    def __init__(self) -> None:
        self.topo_calls: list[tuple[float, float, float]] = []
        self.sidereal_calls: list[tuple[int, float, float]] = []

    def set_topo(self, lon: float, lat: float, elev: float) -> None:
        self.topo_calls.append((lon, lat, elev))

    def set_sid_mode(self, mode: int, arg0: float, arg1: float) -> None:
        self.sidereal_calls.append((mode, arg0, arg1))


def test_adapter_reconfigures_when_swisseph_appears(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Start with Swiss Ephemeris unavailable at import time.
    monkeypatch.setattr(swe_module, "has_swe", lambda: False)

    def missing_swe() -> None:
        raise RuntimeError("Swiss Ephemeris missing")

    monkeypatch.setattr(swe_module, "swe", missing_swe)
    adapter_module._SIDEREAL_MODE_MAP.clear()

    adapter = adapter_module.EphemerisAdapter()

    assert adapter._resolve_flags(None) == 0
    assert adapter._base_calc_flags == 0

    # Swiss Ephemeris becomes available while the process is running.
    dummy = DummySweModule()
    monkeypatch.setattr(swe_module, "has_swe", lambda: True)
    monkeypatch.setattr(swe_module, "swe", lambda: dummy)

    init_calls: list[tuple[str | None, bool, bool]] = []

    def fake_init_ephe(
        path: str | None = None, *, force: bool = False, prefer_moshier: bool = False
    ) -> int:
        init_calls.append((path, force, prefer_moshier))
        return 0x200

    monkeypatch.setattr(adapter_module, "init_ephe", fake_init_ephe)

    config = adapter_module.EphemerisConfig(
        topocentric=True,
        observer=adapter_module.ObserverLocation(
            latitude_deg=1.0, longitude_deg=2.0, elevation_m=3.0
        ),
        sidereal=True,
        sidereal_mode="lahiri",
    )

    adapter.reconfigure(config)

    assert init_calls, "init_ephe should be invoked when Swiss Ephemeris is available"
    init_path, init_force, init_prefer = init_calls[0]
    assert init_force is True
    assert init_prefer is False
    expected_flags = 0x200 | dummy.FLG_SPEED | dummy.FLG_TOPOCTR | dummy.FLG_SIDEREAL
    assert adapter._resolve_flags(None) == expected_flags
    assert dummy.topo_calls == [(2.0, 1.0, 3.0)]
    assert dummy.sidereal_calls == [(dummy.SIDM_LAHIRI, 0.0, 0.0)]
    assert adapter._sidereal_mode_key == "lahiri"
    assert adapter_module._SIDEREAL_MODE_MAP["lahiri"] == dummy.SIDM_LAHIRI
