from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from typer.testing import CliRunner


def _reload_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ASTROENGINE_HOME", str(tmp_path))
    import astroengine.narrative.journaling as journaling

    importlib.reload(journaling)
    import astroengine.cli.app as cli_app

    return importlib.reload(cli_app)


def test_chatbot_local_backend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cli_app = _reload_cli(tmp_path, monkeypatch)
    runner = CliRunner()
    captured: dict[str, object] = {}

    def factory(_options: dict[str, object]):
        def adapter(prompt: str, *, temperature: float = 0.2, **kwargs: object) -> str:
            captured["prompt"] = prompt
            captured["temperature"] = temperature
            captured["kwargs"] = kwargs
            return "local-response"

        return adapter

    from astroengine.narrative.local_model import register_backend, unregister_backend

    register_backend("stub", factory, replace=True)
    try:
        result = runner.invoke(
            cli_app.app,
            [
                "chatbot",
                "hello local",
                "--local-backend",
                "stub",
                "--temperature",
                "0.4",
                "--no-journal",
            ],
        )
    finally:
        unregister_backend("stub")

    assert result.exit_code == 0, result.stdout
    assert "local-response" in result.stdout
    assert captured["prompt"] == "hello local"
    assert captured["temperature"] == 0.4


def test_chatbot_remote_journal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cli_app = _reload_cli(tmp_path, monkeypatch)
    runner = CliRunner()
    prompts: dict[str, object] = {}

    class DummyClient:
        def __init__(self) -> None:
            self.available = True
            self.model = "dummy"

        def summarize(self, prompt: str, *, temperature: float = 0.2) -> str:
            prompts["prompt"] = prompt
            prompts["temperature"] = temperature
            return "remote-response"

    monkeypatch.setattr(
        cli_app.GPTNarrativeClient,
        "from_env",
        classmethod(lambda cls, **_: DummyClient()),
    )

    result = runner.invoke(
        cli_app.app,
        ["chatbot", "hello remote"],
    )

    assert result.exit_code == 0, result.stdout
    assert "remote-response" in result.stdout
    assert prompts["prompt"].endswith("hello remote")
    journal_dir = Path(tmp_path) / "journal"
    saved = list(journal_dir.glob("*.json"))
    assert saved, "expected journal entry"


def test_chatbot_includes_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cli_app = _reload_cli(tmp_path, monkeypatch)
    from astroengine.narrative.journaling import log_entry

    log_entry(prompt="p", response="previous entry", model="local:test")

    runner = CliRunner()
    captured: dict[str, object] = {}

    def factory(_options: dict[str, object]):
        def adapter(prompt: str, *, temperature: float = 0.2, **kwargs: object) -> str:
            captured["prompt"] = prompt
            return "context-response"

        return adapter

    from astroengine.narrative.local_model import register_backend, unregister_backend

    register_backend("ctx", factory, replace=True)
    try:
        result = runner.invoke(
            cli_app.app,
            [
                "chatbot",
                "follow up",
                "--local-backend",
                "ctx",
                "--include-journal",
                "1",
                "--no-journal",
            ],
        )
    finally:
        unregister_backend("ctx")

    assert result.exit_code == 0
    assert "context-response" in result.stdout
    assert "previous entry" in captured["prompt"]
