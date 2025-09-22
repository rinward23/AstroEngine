from __future__ import annotations

import math

import pytest

from astroengine.plugins import DetectorContext, PluginRuntime, set_plugin_manager
from astroengine.plugins.examples import fixed_star_hits
from astroengine.scoring import ScoreInputs, compute_score


class DummyProvider:
    def positions_ecliptic(self, iso_utc: str, bodies):
        return {body: {"lon": 150.0, "speed_lon": 0.2} for body in bodies}

    def position(self, body: str, ts_utc: str):  # pragma: no cover - unused in tests
        from astroengine.canonical import BodyPosition

        return BodyPosition(lon=150.0, lat=0.0, dec=0.0, speed_lon=0.2)


@pytest.fixture(autouse=True)
def reset_plugins():
    set_plugin_manager(None)
    yield
    set_plugin_manager(None)


def _score_inputs() -> ScoreInputs:
    return ScoreInputs(
        kind="decl_parallel",
        orb_abs_deg=0.1,
        orb_allow_deg=1.0,
        moving="sun",
        target="moon",
        applying_or_separating="applying",
    )


def test_fixed_star_plugin_registers_detector_and_scoring():
    runtime = PluginRuntime(autoload_entrypoints=False)
    runtime.register_plugin(fixed_star_hits)
    set_plugin_manager(runtime)

    registry = runtime.detectors()
    assert "fixed_star_hits" in registry.names()

    context = DetectorContext(
        provider=DummyProvider(),
        provider_name="dummy",
        start_iso="2020-01-01T00:00:00Z",
        end_iso="2020-01-01T01:00:00Z",
        ticks=("2020-01-01T00:00:00Z",),
        moving="sun",
        target="moon",
        options={},
        existing_events=(),
    )
    events = runtime.run_detectors(context)
    assert events, "plugin detector should emit events"
    event = events[0]
    assert event.kind == "fixed_star_hit"
    assert event.metadata["fixed_star"] == "regulus"

    score = compute_score(_score_inputs())
    assert math.isclose(score.components["fixed_star.bonus"], 0.1)


def test_plugin_isolation_between_runtimes():
    runtime_with_plugin = PluginRuntime(autoload_entrypoints=False)
    runtime_with_plugin.register_plugin(fixed_star_hits)
    set_plugin_manager(runtime_with_plugin)
    score_with = compute_score(_score_inputs())
    assert "fixed_star.bonus" in score_with.components

    runtime_without_plugin = PluginRuntime(autoload_entrypoints=False)
    set_plugin_manager(runtime_without_plugin)
    score_without = compute_score(_score_inputs())
    assert "fixed_star.bonus" not in score_without.components
