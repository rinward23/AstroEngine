from __future__ import annotations

import math
import sys
import textwrap
from pathlib import Path

import pytest

from astroengine.plugins import (
    DetectorContext,
    PluginRuntime,
    hookimpl,
    set_plugin_manager,
)
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


@pytest.fixture()
def user_plugin_workspace(tmp_path, monkeypatch):
    from astroengine.plugins import registry as plugin_registry

    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()
    monkeypatch.setenv("ASTROENGINE_PLUGIN_DIR", str(plugin_dir))
    original_directory = plugin_registry.PLUGIN_DIRECTORY
    plugin_registry.PLUGIN_DIRECTORY = plugin_dir
    plugin_registry._USER_PLUGINS_IMPORTED = False
    plugin_registry._USER_PLUGIN_MODULES[:] = []
    plugin_registry._USER_PLUGIN_ERRORS[:] = []
    yield plugin_dir

    for name in list(sys.modules):
        if name.startswith(plugin_registry._USER_PLUGIN_NAMESPACE):
            sys.modules.pop(name, None)
    plugin_registry._USER_PLUGINS_IMPORTED = False
    plugin_registry._USER_PLUGIN_MODULES[:] = []
    plugin_registry._USER_PLUGIN_ERRORS[:] = []
    plugin_registry.PLUGIN_DIRECTORY = original_directory


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
    assert event.metadata["fixed_star_name"] == "Regulus"
    assert event.metadata["magnitude"] <= 4.5

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


def test_user_plugin_allowlist_blocks_disallowed_imports(user_plugin_workspace):
    from astroengine.plugins import registry as plugin_registry

    good_path = user_plugin_workspace / "good.py"
    good_path.write_text(
        textwrap.dedent(
            """
            import math

            VALUE = math.pi
            """
        )
    )
    bad_path = user_plugin_workspace / "bad.py"
    bad_path.write_text("import requests\n")

    modules = plugin_registry.load_user_plugins(force=True)
    assert f"{plugin_registry._USER_PLUGIN_NAMESPACE}.good" in modules
    assert all("bad" not in name for name in modules)

    errors = plugin_registry.get_user_plugin_errors()
    assert errors, "bad plugin should record an error"
    error_paths = [Path(path) for path, _ in errors]
    assert bad_path in error_paths
    assert any("requests" in message for _, message in errors)


def test_user_plugin_errors_reset(user_plugin_workspace):
    from astroengine.plugins import registry as plugin_registry

    bad_path = user_plugin_workspace / "bad.py"
    bad_path.write_text("import requests\n")
    plugin_registry.load_user_plugins(force=True)
    assert plugin_registry.get_user_plugin_errors()

    bad_path.write_text(
        textwrap.dedent(
            """
            import math

            VALUE = 42
            """
        )
    )
    modules = plugin_registry.load_user_plugins(force=True)
    assert plugin_registry.get_user_plugin_errors() == ()
    assert f"{plugin_registry._USER_PLUGIN_NAMESPACE}.bad" in modules


def test_score_extension_exceptions_are_isolated():
    runtime = PluginRuntime(autoload_entrypoints=False)

    class _BadScorePlugin:
        ASTROENGINE_PLUGIN_API = "1.0"

        @hookimpl
        def extend_scoring(self, registry):
            def _boom(inputs, result):
                raise RuntimeError("boom")

            registry.register("bad_bonus", _boom)

    runtime.register_plugin(_BadScorePlugin())
    set_plugin_manager(runtime)

    score = compute_score(_score_inputs())
    assert "bad_bonus.bonus" not in score.components
