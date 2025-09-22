"""SQLite schema helpers used by canonical exports.

This module prefers the bundled SQL definitions so the canonical event
pipeline can operate without optional dependencies.  When Alembic and
SQLAlchemy are installed we delegate to them; otherwise a lightweight
SQLite-only implementation is used.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources, util
from pathlib import Path
from typing import Any, Dict, Optional

import sqlite3

_SQLALCHEMY_AVAILABLE = util.find_spec("sqlalchemy") is not None
_ALEMBIC_AVAILABLE = util.find_spec("alembic") is not None and _SQLALCHEMY_AVAILABLE

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS transits_events (
    ts TEXT NOT NULL,
    moving TEXT NOT NULL,
    target TEXT NOT NULL,
    aspect TEXT NOT NULL,
    orb REAL NOT NULL,
    orb_abs REAL NOT NULL,
    applying INTEGER NOT NULL,
    score REAL,
    profile_id TEXT,
    natal_id TEXT,
    event_year INTEGER NOT NULL,
    meta_json TEXT NOT NULL DEFAULT '{}'
)
"""

_CREATE_INDEXES = (
    """
    CREATE INDEX IF NOT EXISTS ix_transits_events_profile_ts
    ON transits_events(profile_id, ts)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_transits_events_natal_year
    ON transits_events(natal_id, event_year)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_transits_events_score
    ON transits_events(score)
    """,
)

_DROP_INDEXES = (
    "DROP INDEX IF EXISTS ix_transits_events_score",
    "DROP INDEX IF EXISTS ix_transits_events_natal_year",
    "DROP INDEX IF EXISTS ix_transits_events_profile_ts",
)


def _absolute_sqlite_path(db_path: str | Path) -> Path:
    return Path(db_path).expanduser().resolve()


def _absolute_sqlite_url(db_path: str | Path) -> str:
    return f"sqlite:///{_absolute_sqlite_path(db_path)}"


if _ALEMBIC_AVAILABLE:  # pragma: no branch - import covered by tests when available
    from alembic import command
    from alembic.config import Config
    from alembic.runtime.migration import MigrationContext
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import NullPool

    def _run_schema_create(db_path: str | Path) -> None:
        engine = create_engine(
            _absolute_sqlite_url(db_path), future=True, poolclass=NullPool
        )
        try:
            with engine.begin() as conn:
                conn.exec_driver_sql(_CREATE_TABLE_SQL)
                for stmt in _CREATE_INDEXES:
                    conn.exec_driver_sql(stmt)
        finally:
            engine.dispose()

    def _run_schema_drop(db_path: str | Path) -> None:
        engine = create_engine(
            _absolute_sqlite_url(db_path), future=True, poolclass=NullPool
        )
        try:
            with engine.begin() as conn:
                for stmt in _DROP_INDEXES:
                    conn.exec_driver_sql(stmt)
                conn.exec_driver_sql("DROP TABLE IF EXISTS transits_events")
        finally:
            engine.dispose()

    def _table_exists(db_path: str | Path, table: str) -> bool:
        engine = create_engine(
            _absolute_sqlite_url(db_path), future=True, poolclass=NullPool
        )
        try:
            with engine.begin() as conn:
                result = conn.execute(
                    text(
                        "SELECT name FROM sqlite_master "
                        "WHERE type='table' AND name=:table_name"
                    ),
                    {"table_name": table},
                )
                return result.scalar() is not None
        finally:
            engine.dispose()

    def _alembic_current_revision(db_path: str | Path) -> str | None:
        engine = create_engine(
            _absolute_sqlite_url(db_path), future=True, poolclass=NullPool
        )
        try:
            with engine.begin() as conn:
                context = MigrationContext.configure(conn)
                return context.get_current_revision()
        finally:
            engine.dispose()

else:  # Alembic/SQLAlchemy unavailable; fall back to sqlite3 helpers.
    command = None

    @dataclass
    class Config:
        """Minimal stand-in mirroring the Alembic ``Config`` API used in tests."""

        script_location: Optional[str] = None
        sqlalchemy_url: Optional[str] = None
        timezone: Optional[str] = None
        attributes: Dict[str, Any] = field(default_factory=dict)

        def set_main_option(self, key: str, value: str) -> None:
            if key == "script_location":
                self.script_location = value
            elif key == "sqlalchemy.url":
                self.sqlalchemy_url = value
            elif key == "timezone":
                self.timezone = value
            else:
                self.attributes[key] = value

    MigrationContext = None

    def _run_schema_create(db_path: str | Path) -> None:
        con = sqlite3.connect(_absolute_sqlite_path(db_path))
        try:
            cur = con.cursor()
            cur.execute(_CREATE_TABLE_SQL)
            for stmt in _CREATE_INDEXES:
                cur.execute(stmt)
            con.commit()
        finally:
            con.close()

    def _run_schema_drop(db_path: str | Path) -> None:
        con = sqlite3.connect(_absolute_sqlite_path(db_path))
        try:
            cur = con.cursor()
            for stmt in _DROP_INDEXES:
                cur.execute(stmt)
            cur.execute("DROP TABLE IF EXISTS transits_events")
            con.commit()
        finally:
            con.close()

    def _table_exists(db_path: str | Path, table: str) -> bool:
        con = sqlite3.connect(_absolute_sqlite_path(db_path))
        try:
            cur = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            )
            return cur.fetchone() is not None
        finally:
            con.close()

    def _alembic_current_revision(db_path: str | Path) -> str | None:  # pragma: no cover
        return "head" if _table_exists(db_path, "transits_events") else None


def get_sqlite_config(db_path: str | Path) -> Config:
    """Build an Alembic ``Config`` or a stub when Alembic is absent."""

    cfg = Config()
    migrations_root = resources.files(__package__) / "migrations"
    cfg.set_main_option("script_location", str(migrations_root))
    cfg.set_main_option("sqlalchemy.url", _absolute_sqlite_url(db_path))
    cfg.set_main_option("timezone", "UTC")
    cfg.attributes.setdefault("configure_logger", False)
    return cfg


@dataclass(slots=True)
class SQLiteMigrator:
    """Apply canonical schema migrations for SQLite exports."""

    db_path: str | Path

    def _config(self) -> Config:
        return get_sqlite_config(self.db_path)

    def upgrade(self, revision: str = "head") -> None:
        if revision not in ("head", "base"):
            raise ValueError(
                "Only 'head' and 'base' revisions are supported for SQLite migrations"
            )
        if _ALEMBIC_AVAILABLE:
            command.upgrade(self._config(), revision)
            return
        if revision == "head":
            _run_schema_create(self.db_path)
        else:
            _run_schema_drop(self.db_path)

    def downgrade(self, revision: str = "base") -> None:
        if revision not in ("base", "head"):
            raise ValueError(
                "Only 'base' and 'head' revisions are supported for SQLite migrations"
            )
        if _ALEMBIC_AVAILABLE:
            command.downgrade(self._config(), revision)
            return
        if revision == "base":
            _run_schema_drop(self.db_path)
        else:
            _run_schema_create(self.db_path)

    def current(self) -> str | None:
        if _ALEMBIC_AVAILABLE:
            return _alembic_current_revision(self.db_path)
        return "head" if _table_exists(self.db_path, "transits_events") else None


def ensure_sqlite_schema(db_path: str | Path) -> None:
    """Ensure the canonical SQLite schema is available."""

    if _table_exists(db_path, "transits_events"):
        return
    SQLiteMigrator(db_path).upgrade("head")


def upgrade_sqlite(db_path: str | Path, revision: str = "head") -> None:
    SQLiteMigrator(db_path).upgrade(revision)


def downgrade_sqlite(db_path: str | Path, revision: str = "base") -> None:
    SQLiteMigrator(db_path).downgrade(revision)


__all__ = [
    "SQLiteMigrator",
    "downgrade_sqlite",
    "ensure_sqlite_schema",
    "get_sqlite_config",
    "upgrade_sqlite",
]
