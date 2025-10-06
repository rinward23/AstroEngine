"""Alembic helpers for SQLite-backed exports."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - imported for static type checking only.
    from alembic.config import Config


def _absolute_sqlite_url(db_path: str | Path) -> str:
    path = Path(db_path).expanduser().resolve()
    return f"sqlite:///{path}"


def get_sqlite_config(db_path: str | Path) -> Config:
    """Build an in-memory Alembic config targeting ``db_path``."""

    from alembic.config import Config

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
        """Apply migrations up to ``revision`` using Alembic's upgrade command."""

        from alembic import command

        command.upgrade(self._config(), revision)

    def downgrade(self, revision: str = "base") -> None:
        """Revert migrations down to ``revision`` using Alembic's downgrade command."""

        from alembic import command

        command.downgrade(self._config(), revision)

    def current(self) -> str | None:
        """Return the current Alembic revision recorded in the SQLite database."""

        from alembic.runtime.migration import MigrationContext
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
