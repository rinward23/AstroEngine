from __future__ import annotations

import sys
import types
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

import astroengine.observability.doctor as doctor


class DummyAdapter:
    def __init__(self, longitude=123.4, declination=5.6):
        self.longitude = longitude
        self.declination = declination


def make_settings(min_year=1900, max_year=2100, qcache_size=10, qcache_sec=5.0, max_scan_days=30):
    swiss_caps = SimpleNamespace(min_year=min_year, max_year=max_year)
    perf = SimpleNamespace(qcache_size=qcache_size, qcache_sec=qcache_sec, max_scan_days=max_scan_days)
    observability = SimpleNamespace(otel_enabled=True, sampling_ratio=0.5, metrics_histogram_buckets=[0.1, 1.0])
    return SimpleNamespace(swiss_caps=swiss_caps, perf=perf, observability=observability)


def install_module(monkeypatch, name, module):
    monkeypatch.setitem(sys.modules, name, module)
    return module


def test_doctor_check_as_dict_includes_data():
    check = doctor.DoctorCheck("demo", "ok", "all good", {"value": 1})
    payload = check.as_dict()
    assert payload == {"name": "demo", "status": "ok", "detail": "all good", "data": {"value": 1}}


def test_check_swisseph_success(monkeypatch, tmp_path):
    class SweModule:
        __version__ = "1.0"
        SUN = 1

        def __call__(self):
            return self

        def julday(self, y, m, d, ut):
            return 2451545.0

    monkeypatch.setattr(doctor, "import_module", lambda name: SweModule())
    monkeypatch.setattr(doctor, "get_se_ephe_path", lambda: str(tmp_path))

    def fake_default_adapter():
        class _Adapter:
            def body_position(self, jd, code, label):
                return DummyAdapter()

        return _Adapter()

    monkeypatch.setattr(doctor, "_get_default_adapter", fake_default_adapter)

    check = doctor._check_swisseph(make_settings())
    assert check.status == "ok"
    assert check.data["ephemeris_path"]["exists"] is True


def test_check_swisseph_missing_module(monkeypatch):
    monkeypatch.setattr(doctor, "import_module", lambda name: (_ for _ in ()).throw(ModuleNotFoundError("swisseph")))
    check = doctor._check_swisseph(make_settings())
    assert check.status == "error"
    assert "not installed" in check.detail


def test_check_database_success(monkeypatch):
    executed = []

    def text(sql):
        executed.append(sql)
        return sql

    sqlalchemy = types.ModuleType("sqlalchemy")
    sqlalchemy.text = text
    install_module(monkeypatch, "sqlalchemy", sqlalchemy)

    app_module = types.ModuleType("app")
    app_module.__path__ = []
    install_module(monkeypatch, "app", app_module)

    db_module = types.ModuleType("app.db")
    db_module.__path__ = []
    install_module(monkeypatch, "app.db", db_module)

    session_module = types.ModuleType("app.db.session")

    class DummySession:
        def execute(self, sql):
            executed.append(sql)

    @contextmanager
    def session_scope():
        yield DummySession()

    engine = SimpleNamespace(
        url=SimpleNamespace(get_backend_name=lambda: "sqlite", database=":memory:"),
    )

    @contextmanager
    def connect():
        yield SimpleNamespace()

    engine.connect = connect

    session_module.engine = engine
    session_module.session_scope = session_scope
    install_module(monkeypatch, "app.db.session", session_module)

    check = doctor._check_database()
    assert check.status == "ok"
    assert executed[0] == "SELECT 1"


def test_check_database_failure(monkeypatch):
    sqlalchemy = types.ModuleType("sqlalchemy")
    sqlalchemy.text = lambda sql: sql
    install_module(monkeypatch, "sqlalchemy", sqlalchemy)

    app_module = types.ModuleType("app")
    app_module.__path__ = []
    install_module(monkeypatch, "app", app_module)
    db_module = types.ModuleType("app.db")
    db_module.__path__ = []
    install_module(monkeypatch, "app.db", db_module)

    session_module = types.ModuleType("app.db.session")

    class DummySession:
        def execute(self, sql):
            raise RuntimeError("db down")

    @contextmanager
    def session_scope():
        yield DummySession()

    engine = SimpleNamespace(url=SimpleNamespace(get_backend_name=lambda: "sqlite", database=":memory:"))

    @contextmanager
    def failing_connect():
        raise RuntimeError("fail")
        yield

    engine.connect = failing_connect

    session_module.engine = engine
    session_module.session_scope = session_scope
    install_module(monkeypatch, "app.db.session", session_module)

    check = doctor._check_database()
    assert check.status == "error"
    assert "database query failed" in check.detail


def test_check_migrations_mismatch(monkeypatch):
    alembic_config = types.ModuleType("alembic.config")

    class Config:
        def __init__(self, path):
            self.path = path
            self.options = {}

        def set_main_option(self, key, value):
            self.options[key] = value

    alembic_config.Config = Config
    install_module(monkeypatch, "alembic.config", alembic_config)

    runtime_module = types.ModuleType("alembic.runtime.migration")

    class MigrationContext:
        @staticmethod
        def configure(connection):
            class Ctx:
                @staticmethod
                def get_current_revision():
                    return "rev_current"

            return Ctx()

    runtime_module.MigrationContext = MigrationContext
    install_module(monkeypatch, "alembic.runtime.migration", runtime_module)

    script_module = types.ModuleType("alembic.script")

    class ScriptDirectory:
        @staticmethod
        def from_config(cfg):
            class Dir:
                @staticmethod
                def get_current_head():
                    return "rev_head"

            return Dir()

    script_module.ScriptDirectory = ScriptDirectory
    install_module(monkeypatch, "alembic.script", script_module)

    engine = SimpleNamespace(
        url=SimpleNamespace(
            render_as_string=lambda hide_password=False: "sqlite://",
            get_backend_name=lambda: "sqlite",
        ),
    )

    @contextmanager
    def connect():
        yield SimpleNamespace()

    engine.connect = connect

    app_module = types.ModuleType("app")
    app_module.__path__ = []
    install_module(monkeypatch, "app", app_module)
    db_module = types.ModuleType("app.db")
    db_module.__path__ = []
    install_module(monkeypatch, "app.db", db_module)

    session_module = install_module(monkeypatch, "app.db.session", types.ModuleType("app.db.session"))
    session_module.engine = engine

    check = doctor._check_migrations()
    assert check.status == "error"
    assert check.data == {"head": "rev_head", "current": "rev_current"}


def test_check_cache_ok(monkeypatch, tmp_path):
    db_path = tmp_path / "cache.db"

    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    finally:
        conn.close()

    class FakePositions:
        DB = db_path

    monkeypatch.setitem(sys.modules, "astroengine.cache", types.ModuleType("astroengine.cache"))
    positions_cache = types.SimpleNamespace(DB=db_path)
    sys.modules["astroengine.cache"].positions_cache = positions_cache

    check = doctor._check_cache()
    assert check.status in {"ok", "warn"}
    assert check.data["path"] == str(db_path)


def test_check_settings_detects_issues():
    settings = make_settings(min_year=2100, max_year=2100, qcache_size=0, qcache_sec=0.0, max_scan_days=0)
    check = doctor._check_settings(settings)
    assert check.status in {"warn", "error"}
    assert "Swiss caps" in check.detail or "qcache" in check.detail


def test_check_disk_free_thresholds(monkeypatch, tmp_path):
    target = tmp_path / "config"
    target.mkdir()

    monkeypatch.setattr(doctor, "get_config_home", lambda: target)

    def fake_disk_usage(path):
        class Usage:
            total = 100
            free = 4

        return Usage()

    monkeypatch.setattr(doctor, "disk_usage", fake_disk_usage)

    check = doctor._check_disk_free(make_settings())
    assert check.status == "error"
    assert "critically low" in check.detail


