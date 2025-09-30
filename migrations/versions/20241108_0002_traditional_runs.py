from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20241108_0002"
down_revision = "20241006_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    timestamp_default = sa.text("CURRENT_TIMESTAMP")
    op.create_table(
        "traditional_runs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("run_id", sa.String(length=40), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("module", sa.String(length=64), nullable=False, server_default=sa.text("'traditional'")),
        sa.Column("submodule", sa.String(length=64), nullable=True),
        sa.Column("channel", sa.String(length=64), nullable=False, server_default=sa.text("'timelords'")),
        sa.Column("subchannel", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=timestamp_default, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=timestamp_default,
            server_onupdate=timestamp_default,
            nullable=False,
        ),
        sa.UniqueConstraint("run_id", name="uq_traditional_runs_run_id"),
    )
    op.create_index(
        "ix_traditional_runs_kind",
        "traditional_runs",
        ["kind"],
    )


def downgrade() -> None:
    op.drop_index("ix_traditional_runs_kind", table_name="traditional_runs")
    op.drop_table("traditional_runs")
