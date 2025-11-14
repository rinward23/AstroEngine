from __future__ import annotations

import io
import json
import sqlite3
from pathlib import Path

import pytest

from astroengine.config import load_settings
from astroengine.ux.desktop.config import DesktopConfigManager, DesktopConfigModel
from astroengine.ux.desktop.copilot import DesktopCopilot
from astroengine.ux.desktop.wizard import run_first_run_wizard, should_run_wizard


class DummyResponse:
    def __init__(self, data: dict[str, object]) -> None:
        self._data = data

    def raise_for_status(self) -> None:  # pragma: no cover - no failure in tests
        return None

    def json(self) -> dict[str, object]:
        return self._data


class DummyHttpClient:
    def __init__(self, payload: dict[str, object] | None = None) -> None:
        self.payload = payload or {"status": "ok"}
        self.requests: list[str] = []

    def get(self, url: str) -> DummyResponse:
        self.requests.append(url)
        return DummyResponse(self.payload)


@pytest.fixture()
def manager(tmp_path: Path) -> DesktopConfigManager:
    return DesktopConfigManager(base_dir=tmp_path)


def test_load_defaults(manager: DesktopConfigManager) -> None:
    config = manager.load()
    assert config.schema_version == DesktopConfigManager.CURRENT_SCHEMA_VERSION
    assert config.database_url.endswith("astroengine-desktop.db")
    assert manager.redact(config)["openai_api_key"] == ""


def test_save_roundtrip(manager: DesktopConfigManager, tmp_path: Path) -> None:
    config = manager.load()
    updated = manager.update(database_url="sqlite:///{}".format((tmp_path / "db.sqlite").as_posix()))
    assert updated.database_url.endswith("db.sqlite")
    reloaded = manager.load()
    assert reloaded.database_url.endswith("db.sqlite")


def test_save_uses_context_manager(
    manager: DesktopConfigManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = manager.load()
    handles: list[io.StringIO] = []

    def fake_open(self: Path, mode: str = "r", encoding: str | None = None):
        assert mode == "w"
        handle = io.StringIO()
        handles.append(handle)
        return handle

    monkeypatch.setattr(Path, "open", fake_open, raising=False)

    manager.save(config)

    assert handles, "expected configuration file to be opened for writing"
    assert handles[0].closed


def test_probe_database_failure(manager: DesktopConfigManager) -> None:
    error = manager.probe_database("sqlite:///nonexistent/dir/foo.db")
    assert error is not None


def test_check_ephemeris(manager: DesktopConfigManager, tmp_path: Path) -> None:
    assert manager.check_ephemeris_path("")
    assert not manager.check_ephemeris_path(str(tmp_path / "missing"))
    existing = tmp_path / "ephe"
    existing.mkdir()
    assert manager.check_ephemeris_path(str(existing))


def test_copilot_diagnostics(tmp_path: Path) -> None:
    manager = DesktopConfigManager(base_dir=tmp_path)
    config = manager.load()
    manager.save(config)
    http_client = DummyHttpClient({"status": "pass"})
    copilot = DesktopCopilot(manager, http_client=http_client)
    log_path = manager.log_path
    log_path.write_text("INFO ready\nERROR failed\n", encoding="utf-8")

    result = copilot.send("please run diagnostics and tail logs")
    assert "AstroEngine diagnostics" in result.response
    assert "ERROR failed" in copilot.invoke_tool("summarize_errors")
    bundle_path = copilot.create_issue_bundle()
    assert bundle_path.exists()
    with bundle_path.open("rb") as fh:
        header = fh.read(2)
    assert header == b"PK"  # zip header


def test_copilot_token_guardrail(tmp_path: Path) -> None:
    manager = DesktopConfigManager(base_dir=tmp_path)
    config = manager.load()
    manager.save(config)
    http_client = DummyHttpClient()
    copilot = DesktopCopilot(manager, http_client=http_client)
    copilot.config = DesktopConfigModel.model_validate({
        **config.model_dump(),
        "copilot_daily_limit": 1,
    })
    result = copilot.send("hello")
    assert "OpenAI client" in result.response
    blocked = copilot.send("hello again")
    assert "daily copilot token budget" in blocked.response


def test_run_first_run_wizard_creates_settings(tmp_path: Path) -> None:
    ephe_dir = tmp_path / "ephe"
    ephe_dir.mkdir()
    atlas_path = tmp_path / "atlas.sqlite"
    (ephe_dir / "sepl_18.se1").write_text("", encoding="utf-8")
    with sqlite3.connect(atlas_path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS cities(id INTEGER PRIMARY KEY)")

    responses = iter([
        str(ephe_dir),
        "y",
        str(atlas_path),
        "vedic",
    ])
    prompts: list[str] = []
    output: list[str] = []

    def fake_input(prompt: str) -> str:
        prompts.append(prompt)
        return next(responses)

    settings_path = tmp_path / "settings.yaml"
    result = run_first_run_wizard(
        settings_path=settings_path,
        input_func=fake_input,
        print_func=output.append,
    )

    assert settings_path.exists()
    assert result.ephemeris.path == str(ephe_dir)
    assert result.atlas.offline_enabled is True
    assert result.atlas.data_path == str(atlas_path)
    assert result.preset == "vedic"

    persisted = load_settings(settings_path)
    assert persisted.preset == "vedic"
    assert persisted.atlas.offline_enabled is True
    assert persisted.atlas.data_path == str(atlas_path)

    summary_lines = "\n".join(output)
    assert "Swiss Ephemeris" in summary_lines
    assert "Offline Atlas" in summary_lines
    meta_path = settings_path.with_suffix(".first_run.json")
    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    assert payload["ephemeris"]["files"] == 1
    assert payload["atlas"]["tables"] >= 1


def test_run_first_run_wizard_reprompts_until_valid_paths(tmp_path: Path) -> None:
    ephe_dir = tmp_path / "ephe"
    ephe_dir.mkdir()
    valid_ephe = ephe_dir / "semo_20.se1"
    atlas_path = tmp_path / "atlas.sqlite"
    with sqlite3.connect(atlas_path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS meta(id INTEGER PRIMARY KEY)")

    responses = iter([
        str(ephe_dir),  # missing data triggers retry
        str(ephe_dir),
        "n",
        "modern_western",
    ])
    output: list[str] = []

    def fake_input(prompt: str) -> str:
        value = next(responses)
        if "ephe" in value and not any(ephe_dir.glob("*.se*")):
            # populate after the first failure
            valid_ephe.write_text("", encoding="utf-8")
        return value

    settings_path = tmp_path / "settings.yaml"
    run_first_run_wizard(
        settings_path=settings_path,
        input_func=fake_input,
        print_func=output.append,
    )

    assert any("Swiss ephemeris directory must include" in line for line in output)
    assert settings_path.exists()


def test_should_run_wizard_flags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings_file = tmp_path / "settings.yaml"
    monkeypatch.setenv("ASTROENGINE_FORCE_WIZARD", "1")
    assert should_run_wizard(settings_file=settings_file)
    monkeypatch.delenv("ASTROENGINE_FORCE_WIZARD", raising=False)
    monkeypatch.setenv("ASTROENGINE_SKIP_WIZARD", "1")
    assert not should_run_wizard(settings_file=settings_file)
