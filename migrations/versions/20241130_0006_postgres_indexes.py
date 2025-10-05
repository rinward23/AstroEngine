from __future__ import annotations

"""Ensure composite indexes exist for Postgres query paths."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Inspector
from sqlalchemy.exc import SQLAlchemyError

revision = "20241130_0006"
down_revision = "20241122_0005"
branch_labels = None
depends_on = None


def _has_index(inspector: Inspector, table: str, name: str) -> bool:
    try:
        return any(index["name"] == name for index in inspector.get_indexes(table))
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

    if _column_exists(inspector, "traditional_runs", "name") and not _has_index(
        inspector, "traditional_runs", "ix_traditional_runs_kind_name"
    ):
        op.create_index(
            "ix_traditional_runs_kind_name",
            "traditional_runs",
            ["kind", "name"],
            unique=False,
        )

    if _column_exists(inspector, "charts", "dt_utc") and not _has_index(
        inspector, "charts", "ix_charts_dt_utc"
    ):
        op.create_index("ix_charts_dt_utc", "charts", ["dt_utc"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_index(inspector, "traditional_runs", "ix_traditional_runs_kind_name"):
        op.drop_index("ix_traditional_runs_kind_name", table_name="traditional_runs")

    # ``ix_charts_dt_utc`` is created in an earlier migration.  We leave it in
    # place so a downgrade returns the schema to its previous state when the
    # index already existed.
    return None
