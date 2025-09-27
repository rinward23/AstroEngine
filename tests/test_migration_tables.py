"""Smoke test verifying Alembic migrations for AstroEngine Plus models."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

EXPECTED_TABLES = {
    "orb_policies",
    "severity_profiles",
    "charts",
    "ruleset_versions",
    "events",
    "asteroid_meta",
    "export_jobs",
}


def _make_config(database_url: str) -> Config:
    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "migrations"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    cfg.attributes["configure_logger"] = False
    return cfg


def _introspect_tables(database_url: str) -> set[str]:
    engine = create_engine(database_url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_tables_exist_after_upgrade(tmp_path) -> None:
    db_path = tmp_path / "plus.db"
    database_url = f"sqlite:///{db_path}"
    cfg = _make_config(database_url)

    command.upgrade(cfg, "head")
    tables_after_upgrade = _introspect_tables(database_url)
    assert EXPECTED_TABLES.issubset(tables_after_upgrade)

    command.downgrade(cfg, "-1")
    tables_after_downgrade = _introspect_tables(database_url)
    assert EXPECTED_TABLES.isdisjoint(tables_after_downgrade)
