"""Tests for desktop packaging affordances."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from astroengine.ux.desktop.app import StreamlitController, _load_embedded_asset
from astroengine.ux.desktop.config import DesktopConfigModel


@pytest.fixture()
def desktop_config() -> DesktopConfigModel:
    """Return a config model with defaults suitable for tests."""

    return DesktopConfigModel(database_url="sqlite:///test.db")


def test_load_embedded_asset_falls_back(tmp_path: Path) -> None:
    missing = tmp_path / "missing.html"
    result = _load_embedded_asset(missing, "fallback")
    assert result == "fallback"


def test_load_embedded_asset_reads_file(tmp_path: Path) -> None:
    asset = tmp_path / "asset.html"
    asset.write_text("<html>hi</html>", encoding="utf-8")
    result = _load_embedded_asset(asset, "fallback")
    assert result == "<html>hi</html>"


def test_streamlit_prefers_meipass_main_portal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, desktop_config: DesktopConfigModel
) -> None:
    bundle = tmp_path / "bundle"
    entry = bundle / "ui" / "streamlit" / "main_portal.py"
    entry.parent.mkdir(parents=True, exist_ok=True)
    entry.write_text("# main portal", encoding="utf-8")
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)

    controller = StreamlitController(desktop_config, tmp_path)

    assert controller._entry == entry
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)


def test_streamlit_falls_back_to_vedic_app(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, desktop_config: DesktopConfigModel
) -> None:
    bundle = tmp_path / "bundle"
    entry = bundle / "ui" / "streamlit" / "vedic_app.py"
    entry.parent.mkdir(parents=True, exist_ok=True)
    entry.write_text("# vedic", encoding="utf-8")
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)

    controller = StreamlitController(desktop_config, tmp_path)

    assert controller._entry == entry
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)


def test_streamlit_falls_back_to_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, desktop_config: DesktopConfigModel
) -> None:
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    controller = StreamlitController(desktop_config, tmp_path)

    repo_entry = Path(__file__).resolve().parents[2] / "ui" / "streamlit" / "main_portal.py"
    assert controller._entry == repo_entry
