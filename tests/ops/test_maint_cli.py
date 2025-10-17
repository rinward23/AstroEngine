from __future__ import annotations

import click
from click.testing import CliRunner

import astroengine.maint as maint


def maint_command():
    @click.command(context_settings={"ignore_unknown_options": True})
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    def command(args: tuple[str, ...]):
        code = maint.main(list(args))
        raise SystemExit(code)

    return command


def test_cli_auto_install_requires_confirmation(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(maint, "sh", lambda *args, **kwargs: (0, ""))
    monkeypatch.setattr(maint, "parse_requirements", lambda path: ["pkgA"])

    pip_calls: list[list[str]] = []

    def fake_pip_install(pkgs):
        pip_calls.append(list(pkgs))
        return 0

    monkeypatch.setattr(maint, "pip_install", fake_pip_install)
    monkeypatch.setattr(maint, "gate_diagnostics", lambda strict: True)
    monkeypatch.setattr(maint, "gate_format_lint", lambda apply_fixes: True)
    monkeypatch.setattr(maint, "gate_tests", lambda: True)
    monkeypatch.setattr(maint, "gate_build", lambda ensure_build_tool: True)

    cmd = maint_command()
    result = runner.invoke(cmd, ["--auto-install", "dev"])
    assert result.exit_code == 1
    assert "Auto-install may modify your environment" in result.output
    assert "❌ auto-install" in result.output
    assert pip_calls == []


def test_cli_success_with_yes_and_full(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(maint, "sh", lambda *args, **kwargs: (0, ""))
    monkeypatch.setattr(maint, "parse_requirements", lambda path: ["pkgA", "pkgB"])

    pip_calls: list[list[str]] = []

    def fake_pip_install(pkgs):
        pip_calls.append(list(pkgs))
        return 0

    monkeypatch.setattr(maint, "pip_install", fake_pip_install)

    gate_calls: list[tuple[str, tuple, dict]] = []

    def record(name, result=True):
        def inner(*args, **kwargs):
            gate_calls.append((name, args, kwargs))
            return result

        return inner

    monkeypatch.setattr(maint, "gate_diagnostics", record("diagnostics"))
    monkeypatch.setattr(maint, "gate_format_lint", record("format", True))
    monkeypatch.setattr(maint, "gate_tests", record("tests"))
    monkeypatch.setattr(maint, "gate_build", record("build"))

    cmd = maint_command()
    result = runner.invoke(
        cmd,
        [
            "--full",
            "--strict",
            "--auto-install",
            "dev",
            "--yes",
            "--with-build",
        ],
    )
    assert result.exit_code == 0
    assert pip_calls == [["pkgA", "pkgB"]]
    names = [name for name, *_ in gate_calls]
    assert names == ["diagnostics", "format", "tests", "build"]
    assert "✅ diagnostics" in result.output
    assert "✅ tests" in result.output


def test_gate_auto_install_invokes_pip_when_allowed(monkeypatch):
    monkeypatch.setattr(maint, "parse_requirements", lambda path: ["pkgA"])

    called: list[list[str]] = []

    def fake_pip_install(pkgs):
        called.append(list(pkgs))
        return 0

    monkeypatch.setattr(maint, "pip_install", fake_pip_install)
    assert maint.gate_auto_install("dev", True) is True
    assert called == [["pkgA"]]


def test_gate_diagnostics_handles_failure(monkeypatch):
    payload = {
        "summary": {"exit_code": 1},
        "checks": [],
    }

    def fake_collect(strict):
        assert strict is True
        return payload

    monkeypatch.setitem(maint.gate_diagnostics.__globals__, "collect_diagnostics", fake_collect)

    assert maint.gate_diagnostics(True) is False


def test_gate_build_installs_when_missing(monkeypatch):
    monkeypatch.setattr(maint, "sh", lambda *args, **kwargs: (0, ""))

    states = iter([False, True])

    def fake_have_module(name):
        return next(states)

    monkeypatch.setattr(maint, "have_module", fake_have_module)

    installed: list[list[str]] = []

    def fake_pip_install(pkgs):
        installed.append(list(pkgs))
        return 0

    monkeypatch.setattr(maint, "pip_install", fake_pip_install)

    assert maint.gate_build(True) is True
    assert installed == [["build>=1"]]


def test_gate_build_skips_when_unavailable_and_not_required(monkeypatch):
    monkeypatch.setattr(maint, "have_module", lambda name: False)
    assert maint.gate_build(False) is True


