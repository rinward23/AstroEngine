"""Create notes table for chart annotations."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20241122_0005"
down_revision = "20241118_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    timestamp_default = sa.text("CURRENT_TIMESTAMP")
    op.create_table(
        "notes",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("chart_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp_default),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.ForeignKeyConstraint(["chart_id"], ["charts.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_notes_chart_id", "notes", ["chart_id"])


def downgrade() -> None:
    op.drop_index("ix_notes_chart_id", table_name="notes")
    op.drop_table("notes")
