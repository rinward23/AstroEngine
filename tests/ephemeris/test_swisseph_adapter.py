"""Swiss Ephemeris adapter behaviour with monkeypatched swe modules."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from astroengine.chart.config import ChartConfig
from astroengine.ephemeris import swisseph_adapter


@dataclass
class DummySweModule:
    """Minimal Swiss Ephemeris shim for adapter tests."""

    FLG_SPEED: int = 0x01
    FLG_MOSEPH: int = 0x02
    FLG_SIDEREAL: int = 0x04
    FLG_SWIEPH: int = 0x08
    MEAN_NODE: int = 42
    TRUE_NODE: int = 43
    MEAN_APOG: int = 52
    OSCU_APOG: int = 53
    SIDM_LAHIRI: int = 99
    SIDM_FAGAN_BRADLEY: int = 100
    SIDM_KRISHNAMURTI: int = 101
    SIDM_RAMAN: int = 102
    SIDM_DELUCE: int = 103
    SIDM_YUKTESHWAR: int = 104
    SIDM_GALCENT_0SAG: int = 105
    SIDM_SASSANIAN: int = 106
    GREG_CAL: int = 1

    def __post_init__(self) -> None:
        self.base_flag = 0x100
        self.sid_mode_calls: list[tuple[int, float, float]] = []

    def set_sid_mode(self, mode: int, arg0: float, arg1: float) -> None:
        self.sid_mode_calls.append((mode, arg0, arg1))

    def set_ephe_path(self, path: str | None) -> None:  # pragma: no cover - used by init_ephe
        self.ephe_path = path

    def julday(self, year: int, month: int, day: int, hour: float) -> float:
        return float(year * 10000 + month * 100 + day) + hour

    def revjul(self, jd_ut: float, calendar: int) -> tuple[int, int, int, float]:
        whole = int(jd_ut)
        year = whole // 10000
        month = (whole // 100) % 100
        day = whole % 100
        hour = jd_ut - whole
        return year, month, day, hour


class DummyProxy:
    def __init__(self, module: DummySweModule):
        self._module = module

    def __call__(self) -> DummySweModule:
        return self._module

    def __getattr__(self, item: str):
        return getattr(self._module, item)


@pytest.fixture
def dummy_swe(monkeypatch: pytest.MonkeyPatch) -> DummySweModule:
    module = DummySweModule()
    proxy = DummyProxy(module)

    def fake_init_ephe(path=None, *, force=False, prefer_moshier=False):
        return module.base_flag

    monkeypatch.setattr(swisseph_adapter, "_swe", lambda: proxy)
    monkeypatch.setattr(swisseph_adapter, "init_ephe", fake_init_ephe)
    monkeypatch.setattr(swisseph_adapter, "get_se_ephe_path", lambda: None)
    monkeypatch.setattr(
        swisseph_adapter.SwissEphemerisAdapter, "_DEFAULT_PATHS", tuple()
    )
    swisseph_adapter._node_variant_codes.cache_clear()
    swisseph_adapter._lilith_variant_codes.cache_clear()
    swisseph_adapter.SwissEphemerisAdapter._AYANAMSHA_MODES = None

    return module


def test_variant_override_handles_nodes_and_lilith(dummy_swe: DummySweModule) -> None:
    mean_adapter = swisseph_adapter.SwissEphemerisAdapter(
        chart_config=ChartConfig(nodes_variant="mean", lilith_variant="mean")
    )
    true_adapter = swisseph_adapter.SwissEphemerisAdapter(
        chart_config=ChartConfig(nodes_variant="true", lilith_variant="true")
    )

    code, derived = mean_adapter._variant_override("South Node")
    assert code == dummy_swe.MEAN_NODE
    assert derived is True

    code, derived = mean_adapter._variant_override("south node (true)")
    assert code == dummy_swe.TRUE_NODE
    assert derived is True

    code, derived = true_adapter._variant_override("South Node")
    assert code == dummy_swe.TRUE_NODE
    assert derived is True

    code, derived = mean_adapter._variant_override("Black Moon Lilith")
    assert code == dummy_swe.MEAN_APOG
    assert derived is False

    code, derived = true_adapter._variant_override("Black Moon Lilith")
    assert code == dummy_swe.OSCU_APOG
    assert derived is False

    assert mean_adapter._variant_override("unknown") == (None, False)


def test_get_swisseph_missing_library(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_swe():
        raise RuntimeError("Swiss Ephemeris not available")

    monkeypatch.setattr(swisseph_adapter, "_swe", missing_swe)

    with pytest.raises(RuntimeError) as excinfo:
        swisseph_adapter.get_swisseph()

    assert "Swiss Ephemeris not available" in str(excinfo.value)


def test_refresh_flags_caches_speed_and_sidereal(dummy_swe: DummySweModule) -> None:
    dummy_swe.base_flag = 0x200
    adapter = swisseph_adapter.SwissEphemerisAdapter(
        chart_config=ChartConfig(zodiac="sidereal", ayanamsha="lahiri")
    )

    expected_calc = dummy_swe.base_flag | dummy_swe.FLG_SPEED | dummy_swe.FLG_SIDEREAL
    expected_fallback = dummy_swe.FLG_MOSEPH | dummy_swe.FLG_SPEED | dummy_swe.FLG_SIDEREAL

    assert adapter._calc_flags == expected_calc
    assert adapter._fallback_flags == expected_fallback
    assert dummy_swe.sid_mode_calls == [(dummy_swe.SIDM_LAHIRI, 0.0, 0.0)]

    dummy_swe.FLG_SPEED = 0x10
    adapter._base_flag = 0x01
    adapter._refresh_flags()
    assert adapter._calc_flags == 0x01 | dummy_swe.FLG_SPEED | dummy_swe.FLG_SIDEREAL
    assert adapter._fallback_flags == dummy_swe.FLG_MOSEPH | dummy_swe.FLG_SPEED | dummy_swe.FLG_SIDEREAL
