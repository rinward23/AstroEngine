"""Add chart library metadata columns."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20241130_0006"
down_revision = "20241122_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("charts", sa.Column("name", sa.String(length=120), nullable=True))
    op.add_column(
        "charts",
        sa.Column(
            "tags",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.add_column("charts", sa.Column("memo", sa.Text(), nullable=True))
    op.add_column("charts", sa.Column("gender", sa.String(length=32), nullable=True))
    op.add_column(
        "charts",
        sa.Column(
            "settings_snapshot",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.add_column(
        "charts",
        sa.Column("narrative_profile", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "charts",
        sa.Column("bodies", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "charts",
        sa.Column("houses", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "charts",
        sa.Column("aspects", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "charts",
        sa.Column("patterns", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.create_index("ix_charts_kind_name", "charts", ["kind", "name"])

    # Drop server defaults to avoid future inserts inheriting stringified JSON.
    op.execute("UPDATE charts SET tags = '[]' WHERE tags IS NULL")
    with op.batch_alter_table("charts") as batch:
        batch.alter_column("tags", server_default=None)
        batch.alter_column("settings_snapshot", server_default=None)
        batch.alter_column("bodies", server_default=None)
        batch.alter_column("houses", server_default=None)
        batch.alter_column("aspects", server_default=None)
        batch.alter_column("patterns", server_default=None)


def downgrade() -> None:
    op.alter_column("charts", "patterns", server_default=sa.text("'[]'"))
    op.alter_column("charts", "aspects", server_default=sa.text("'[]'"))
    op.alter_column("charts", "houses", server_default=sa.text("'{}'"))
    op.alter_column("charts", "bodies", server_default=sa.text("'{}'"))
    op.alter_column("charts", "settings_snapshot", server_default=sa.text("'{}'"))
    op.drop_index("ix_charts_kind_name", table_name="charts")
    op.drop_column("charts", "patterns")
    op.drop_column("charts", "aspects")
    op.drop_column("charts", "houses")
    op.drop_column("charts", "bodies")
    op.drop_column("charts", "narrative_profile")
    op.drop_column("charts", "settings_snapshot")
    op.drop_column("charts", "gender")
    op.drop_column("charts", "memo")
    op.drop_column("charts", "tags")
    op.drop_column("charts", "name")
