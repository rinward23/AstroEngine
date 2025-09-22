"""Create transits_events schema."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20240921_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transits_events",
        sa.Column("ts", sa.String(), nullable=False),
        sa.Column("moving", sa.String(), nullable=False),
        sa.Column("target", sa.String(), nullable=False),
        sa.Column("aspect", sa.String(), nullable=False),
        sa.Column("orb", sa.Float(), nullable=False),
        sa.Column("orb_abs", sa.Float(), nullable=False),
        sa.Column("applying", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("profile_id", sa.String(), nullable=True),
        sa.Column("natal_id", sa.String(), nullable=True),
        sa.Column("event_year", sa.Integer(), nullable=False),
        sa.Column("meta_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index(
        "ix_transits_events_profile_ts",
        "transits_events",
        ["profile_id", "ts"],
    )
    op.create_index(
        "ix_transits_events_natal_year",
        "transits_events",
        ["natal_id", "event_year"],
    )
    op.create_index("ix_transits_events_score", "transits_events", ["score"])


def downgrade() -> None:
    op.drop_index("ix_transits_events_score", table_name="transits_events")
    op.drop_index("ix_transits_events_natal_year", table_name="transits_events")
    op.drop_index("ix_transits_events_profile_ts", table_name="transits_events")
    op.drop_table("transits_events")
