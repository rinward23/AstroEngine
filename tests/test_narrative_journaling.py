from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def _reload_journaling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ASTROENGINE_HOME", str(tmp_path))
    import astroengine.narrative.journaling as journaling

    return importlib.reload(journaling)


def test_log_and_load_entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    journaling = _reload_journaling(tmp_path, monkeypatch)
    entry = journaling.log_entry(
        prompt="hello",
        response="world",
        model="local:stub",
        tags=["evening", "test"],
        metadata={"foo": "bar"},
    )
    loaded = journaling.load_entry(entry.entry_id)
    assert loaded.prompt == "hello"
    assert loaded.response == "world"
    assert "evening" in loaded.tags
    assert loaded.metadata["foo"] == "bar"


def test_latest_entries_and_prompt_lines(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    journaling = _reload_journaling(tmp_path, monkeypatch)
    journaling.log_entry(prompt="first", response="alpha", model="m1")
    journaling.log_entry(prompt="second", response="beta", model="m2", tags=["focus"])
    entries = journaling.latest_entries(2)
    assert len(entries) == 2
    lines = journaling.journal_prompt_lines(entries)
    assert lines[0].startswith("Recent")
    assert "beta" in " ".join(lines)


def test_journal_context_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    journaling = _reload_journaling(tmp_path, monkeypatch)
    journaling.log_entry(prompt="context", response="details", model="m")
    entries = journaling.latest_entries(1)
    payload = journaling.journal_context_payload(entries)
    assert payload["journal_count"] == 1
    assert payload["journal_header"].startswith("Recent")
    assert isinstance(payload["journal_excerpt_lines"], list)
