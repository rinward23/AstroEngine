from dataclasses import asdict
from types import SimpleNamespace

import astroengine.diagnostics as diagnostics


def make_check(name, status, detail):
    return diagnostics.Check(name=name, status=status, detail=detail, data=None)


def test_collect_diagnostics_summarizes(monkeypatch):
    monkeypatch.setattr(diagnostics, "check_python", lambda: make_check("python", "PASS", "ok"))
    monkeypatch.setattr(
        diagnostics,
        "check_core_imports",
        lambda: [make_check("core", "PASS", "ok"), make_check("core2", "PASS", "ok")],
    )
    monkeypatch.setattr(
        diagnostics,
        "check_optional_deps",
        lambda: [make_check("opt", "WARN", "missing")],
    )
    monkeypatch.setattr(
        diagnostics,
        "check_timezone_libs",
        lambda: [make_check("tz", "PASS", "ok")],
    )
    monkeypatch.setattr(diagnostics, "check_swisseph", lambda: [make_check("swe", "PASS", "ok")])
    monkeypatch.setattr(diagnostics, "check_ephemeris_path_sanity", lambda: make_check("path", "PASS", "ok"))
    monkeypatch.setattr(diagnostics, "check_ephemeris_config", lambda: make_check("cfg", "PASS", "ok"))
    monkeypatch.setattr(diagnostics, "check_database_ping", lambda: make_check("db", "PASS", "ok"))
    monkeypatch.setattr(diagnostics, "check_migrations_current", lambda: make_check("migr", "PASS", "ok"))
    monkeypatch.setattr(diagnostics, "check_cache_sizes", lambda: make_check("cache", "PASS", "ok"))
    monkeypatch.setattr(diagnostics, "check_disk_free", lambda: make_check("disk", "PASS", "ok"))
    monkeypatch.setattr(diagnostics, "check_swiss_probes", lambda: make_check("probe", "PASS", "ok"))
    monkeypatch.setattr(diagnostics, "check_profiles_presence", lambda: make_check("profiles", "PASS", "ok"))

    payload = diagnostics.collect_diagnostics(strict=False)
    summary = payload["summary"]
    assert summary["pass"] == 13
    assert summary["warn"] == 1
    assert summary["fail"] == 0
    assert summary["exit_code"] == 0
    assert any(check["name"] == "opt" for check in payload["checks"])


def test_collect_diagnostics_strict_flags_warn(monkeypatch):
    monkeypatch.setattr(diagnostics, "check_python", lambda: make_check("python", "PASS", "ok"))
    monkeypatch.setattr(diagnostics, "check_core_imports", lambda: [])
    monkeypatch.setattr(diagnostics, "check_optional_deps", lambda: [make_check("opt", "WARN", "missing")])
    monkeypatch.setattr(diagnostics, "check_timezone_libs", lambda: [])
    monkeypatch.setattr(diagnostics, "check_swisseph", lambda: [])
    monkeypatch.setattr(diagnostics, "check_ephemeris_path_sanity", lambda: make_check("path", "WARN", "missing"))
    monkeypatch.setattr(diagnostics, "check_ephemeris_config", lambda: make_check("cfg", "PASS", "ok"))
    monkeypatch.setattr(diagnostics, "check_database_ping", lambda: make_check("db", "PASS", "ok"))
    monkeypatch.setattr(diagnostics, "check_migrations_current", lambda: make_check("migr", "PASS", "ok"))
    monkeypatch.setattr(diagnostics, "check_cache_sizes", lambda: make_check("cache", "PASS", "ok"))
    monkeypatch.setattr(diagnostics, "check_disk_free", lambda: make_check("disk", "PASS", "ok"))
    monkeypatch.setattr(diagnostics, "check_swiss_probes", lambda: make_check("probe", "PASS", "ok"))
    monkeypatch.setattr(diagnostics, "check_profiles_presence", lambda: make_check("profiles", "PASS", "ok"))

    payload = diagnostics.collect_diagnostics(strict=True)
    assert payload["summary"]["exit_code"] == 1
    assert payload["summary"]["warn"] == 2


