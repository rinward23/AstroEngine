"""Add hot-path indexes for cached lookups."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Inspector
from sqlalchemy.exc import NoSuchTableError, SQLAlchemyError

revision = "20241118_0004"
down_revision = "20241115_0003"
branch_labels = None
depends_on = None


def _has_index(inspector: Inspector, table: str, name: str) -> bool:
    try:
        return any(index["name"] == name for index in inspector.get_indexes(table))
    except NoSuchTableError:
        return False


def _table_exists(inspector: Inspector, name: str) -> bool:
    try:
        return name in inspector.get_table_names()
    except SQLAlchemyError:
        return False


def _column_exists(inspector: Inspector, table: str, column: str) -> bool:
    try:
        return any(col["name"] == column for col in inspector.get_columns(table))
    except SQLAlchemyError:
        return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_index(inspector, "positions", "ix_positions_by_day_body") and _table_exists(
        inspector, "positions"
    ):
        op.create_index(
            "ix_positions_by_day_body",
            "positions",
            ["day_jd", "body"],
            unique=False,
        )

    if not _has_index(inspector, "ruleset_versions", "ix_ruleset_versions_scope_key") and _table_exists(
        inspector, "ruleset_versions"
    ):
        scope_key_column = (
            "ruleset_key"
            if _column_exists(inspector, "ruleset_versions", "ruleset_key")
            else "key"
        )
        op.create_index(
            "ix_ruleset_versions_scope_key",
            "ruleset_versions",
            ["module", "submodule", "channel", "subchannel", scope_key_column],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_index(inspector, "ruleset_versions", "ix_ruleset_versions_scope_key"):
        op.drop_index("ix_ruleset_versions_scope_key", table_name="ruleset_versions")

    if _has_index(inspector, "positions", "ix_positions_by_day_body"):
        op.drop_index("ix_positions_by_day_body", table_name="positions")
