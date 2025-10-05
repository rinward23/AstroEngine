"""Smoke tests for the ``astroengine codex`` CLI command."""

from __future__ import annotations

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
