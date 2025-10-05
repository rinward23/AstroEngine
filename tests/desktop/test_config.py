from __future__ import annotations

from pathlib import Path

import pytest

from astroengine.ux.desktop.config import DesktopConfigManager, DesktopConfigModel
from astroengine.ux.desktop.copilot import DesktopCopilot


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
