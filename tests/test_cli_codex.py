"""Smoke tests for the ``astroengine codex`` CLI command."""

from __future__ import annotations

import json

from astroengine import cli


def test_codex_tree_lists_developer_platform(capsys) -> None:
    exit_code = cli.main(["codex", "tree"])
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "developer_platform" in output
    assert "codex" in output


def test_codex_show_json_emits_payload(capsys) -> None:
    exit_code = cli.main([
        "codex",
        "show",
        "developer_platform",
        "codex",
        "access",
        "cli",
        "--json",
    ])
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "astroengine codex" in output


def test_codex_files_returns_documentation_path(capsys) -> None:
    exit_code = cli.main([
        "codex",
        "files",
        "developer_platform",
        "codex",
        "access",
        "python",
    ])
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "codex.md" in output


def test_codex_mcp_command_emits_manifest(capsys) -> None:
    exit_code = cli.main(["codex", "mcp"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["server"]["name"] == "astroengine-codex"
    assert payload["commonServers"], "Expected codex mcp command to include common servers"
