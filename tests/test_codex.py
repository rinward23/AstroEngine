"""Tests for the astroengine.codex helper module."""

from __future__ import annotations

from pathlib import Path

from astroengine import codex


def test_describe_root_contains_developer_platform() -> None:
    node = codex.describe_path()
    assert node.kind == "registry"
    assert "developer_platform" in node.children


def test_codex_cli_entry_metadata_and_payload() -> None:
    node = codex.describe_path(["developer_platform", "codex", "access", "cli"])
    assert node.kind == "subchannel"
    assert node.metadata.get("status") == "available"
    assert node.payload and node.payload.get("command") == "astroengine codex"


def test_resolved_files_for_python_helpers_points_to_docs() -> None:
    paths = codex.resolved_files(["developer_platform", "codex", "access", "python"])
    filenames = {Path(p).name for p in paths}
    assert "codex.md" in filenames
    for path in paths:
        assert Path(path).exists()
