"""Add soft delete and tags metadata to charts."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20241202_0006_chart_soft_delete"
down_revision = "20241122_0005_notes_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("charts") as batch:
        batch.add_column(
            sa.Column(
                "tags",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )
        batch.add_column(
            sa.Column(
                "deleted_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
    op.execute("UPDATE charts SET tags = '[]' WHERE tags IS NULL")
    with op.batch_alter_table("charts") as batch:
        batch.alter_column("tags", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("charts") as batch:
        batch.drop_column("deleted_at")
        batch.drop_column("tags")

