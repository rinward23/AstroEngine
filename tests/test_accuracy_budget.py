import sys
import types
from types import SimpleNamespace

import pytest

if "swisseph" not in sys.modules:
    class _StubSwiss(types.ModuleType):
        def __getattr__(self, name: str):
            if name == "julday":
                return lambda *args, **kwargs: 0.0
            if name == "revjul":
                return lambda *args, **kwargs: (2000, 1, 1, 0.0)
            if name.startswith("calc"):
                return lambda *args, **kwargs: (0.0, 0.0, 0.0)
            if name.startswith("set_"):
                return lambda *args, **kwargs: None
            if name.isupper():
                return 0
            raise AttributeError(name)

    sys.modules["swisseph"] = _StubSwiss("swisseph")

from astroengine.core.accuracy import ACCURACY_PROFILES
import astroengine.core.transit_engine as transit_engine


@pytest.fixture
def stub_adapter(monkeypatch):
    adapter = SimpleNamespace(
        julian_day=lambda dt: 0.0,
        body_position=lambda jd, body_code, body_name="": SimpleNamespace(longitude=0.0),
    )
    monkeypatch.setattr(
        transit_engine.SwissEphemerisAdapter,
        "get_default_adapter",
        classmethod(lambda cls: adapter),
    )
    return adapter


def test_scan_transits_applies_accuracy_profile(monkeypatch, stub_adapter):
    captured: dict[str, object] = {}

    class FakeTransitEngine:
        def __init__(self, adapter, config):
            self.adapter = adapter
            self._config = config

        @classmethod
        def with_default_adapter(cls, config=None, *, engine_config=None):
            captured["config"] = engine_config
            return cls(stub_adapter, engine_config)

        def scan_longitude_crossing(self, *args, step_hours=None, **kwargs):
            captured.setdefault("step_hours", []).append(step_hours)
            return []

    monkeypatch.setattr(transit_engine, "TransitEngine", FakeTransitEngine)

    result = transit_engine.scan_transits(
        natal_ts="2000-01-01T00:00:00Z",
        start_ts="2000-01-02T00:00:00Z",
        end_ts="2000-01-03T00:00:00Z",
        bodies=["Sun"],
        targets=["Sun"],
        aspects=["conjunction"],
        step_days=1.0,
        accuracy_budget="high",
    )

    assert result == []
    config = captured["config"]
    profile = ACCURACY_PROFILES["high"]
    default_profile = ACCURACY_PROFILES["default"]
    assert config.accurate_iterations == profile.max_iter
    expected_min_step = transit_engine.TransitEngineConfig().accurate_min_step_seconds * (
        profile.tol_arcsec / default_profile.tol_arcsec
    )
    assert pytest.approx(config.accurate_min_step_seconds, rel=1e-6) == expected_min_step
    expected_step_hours = 24.0 * (profile.coarse_step_sec / default_profile.coarse_step_sec)
    assert pytest.approx(captured["step_hours"][0], rel=1e-6) == expected_step_hours


def test_run_scan_or_raise_threads_accuracy(monkeypatch):
    from astroengine import app_api

    called: dict[str, object] = {}

    class FakeModule(types.SimpleNamespace):
        pass

    def fake_import(name):
        module = FakeModule()

        def _scan(*, accuracy_budget=None, **kwargs):
            called.update(kwargs)
            called["accuracy_budget"] = accuracy_budget
            return [kwargs]

        module.scan = _scan
        return module

    monkeypatch.setattr(app_api.importlib, "import_module", fake_import)

    events = app_api.run_scan_or_raise(
        start_utc="2000-01-01T00:00:00Z",
        end_utc="2000-01-02T00:00:00Z",
        moving=["Sun"],
        targets=["Sun"],
        provider=None,
        profile_id=None,
        step_minutes=60,
        entrypoints=[("fake", "scan")],
        accuracy_budget="fast",
    )

    assert events
    assert called["accuracy_budget"] == "fast"
