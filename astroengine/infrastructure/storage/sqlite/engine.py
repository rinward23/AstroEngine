"""Alembic helpers for SQLite-backed exports."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext


def _absolute_sqlite_url(db_path: str | Path) -> str:
    path = Path(db_path).expanduser().resolve()
    return f"sqlite:///{path}"


def get_sqlite_config(db_path: str | Path) -> Config:
    """Build an in-memory Alembic config targeting ``db_path``."""

    cfg = Config()
    migrations_root = resources.files(__package__) / "migrations"
    cfg.set_main_option("script_location", str(migrations_root))
    cfg.set_main_option("sqlalchemy.url", _absolute_sqlite_url(db_path))
    cfg.set_main_option("timezone", "UTC")
    cfg.attributes.setdefault("configure_logger", False)
    return cfg


@dataclass(slots=True)
class SQLiteMigrator:
    """Convenience wrapper for applying SQLite migrations."""

    db_path: str | Path

    def _config(self) -> Config:
        return get_sqlite_config(self.db_path)

    def upgrade(self, revision: str = "head") -> None:
        command.upgrade(self._config(), revision)

    def downgrade(self, revision: str = "base") -> None:
        command.downgrade(self._config(), revision)

    def current(self) -> str | None:
        from sqlalchemy import create_engine
        from sqlalchemy.pool import NullPool

        engine = create_engine(
            _absolute_sqlite_url(self.db_path), future=True, poolclass=NullPool
        )
        try:
            with engine.begin() as conn:
                context = MigrationContext.configure(conn)
                return context.get_current_revision()
        finally:
            engine.dispose()


def ensure_sqlite_schema(db_path: str | Path) -> None:
    """Ensure the schema is migrated to the latest revision."""

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
