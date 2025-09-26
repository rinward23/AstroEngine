"""Tests for runtime entry point discovery of AstroEngine plugins and providers."""

from __future__ import annotations

import subprocess
import sys
from importlib import metadata
from pathlib import Path

from astroengine.plugins.runtime import Registry, load_plugins, load_providers

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _ensure_editable_install(dist_name: str, relative_path: str, module_name: str) -> None:
    """Install the local sample package in editable mode if it is missing."""

    needs_install = False

    try:
        metadata.distribution(dist_name)
    except metadata.PackageNotFoundError:
        needs_install = True
    else:
        try:
            __import__(module_name)
        except ModuleNotFoundError:
            needs_install = True

    if needs_install:
        package_dir = _REPO_ROOT / relative_path
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-e", str(package_dir)],
            cwd=_REPO_ROOT,
        )


def test_entry_points_discovery() -> None:
    _ensure_editable_install(
        "astroengine-sample-plugin", "plugins/sample_plugin", "astroengine_plugins"
    )
    _ensure_editable_install(
        "astroengine-sample-provider", "plugins/sample_provider", "astroengine_providers"
    )

    registry = Registry()
    plugin_names = load_plugins(registry)
    provider_names = load_providers(registry)

    assert "example_vca" in plugin_names
    assert "swiss_ephemeris" in provider_names
    assert "vca.basic" in registry.rulesets
    assert "swiss_ephemeris" in registry.providers
