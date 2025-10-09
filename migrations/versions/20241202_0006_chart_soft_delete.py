"""Add soft delete metadata to charts."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20241202_0006_chart_soft_delete"
down_revision = "20241130_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not any(col["name"] == "deleted_at" for col in inspector.get_columns("charts")):
        with op.batch_alter_table("charts") as batch:
            batch.add_column(
                sa.Column(
                    "deleted_at",
                    sa.DateTime(timezone=True),
                    nullable=True,
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if any(col["name"] == "deleted_at" for col in inspector.get_columns("charts")):
        with op.batch_alter_table("charts") as batch:
            batch.drop_column("deleted_at")
