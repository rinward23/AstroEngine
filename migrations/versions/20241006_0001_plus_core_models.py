"""Create AstroEngine Plus core tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20241006_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    timestamp_default = sa.text("CURRENT_TIMESTAMP")

    op.create_table(
        "orb_policies",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("per_object", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("per_aspect", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("adaptive_rules", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("module", sa.String(length=64), nullable=False, server_default=sa.text("'plus'")),
        sa.Column("submodule", sa.String(length=64), nullable=True),
        sa.Column("channel", sa.String(length=64), nullable=False, server_default=sa.text("'transits'")),
        sa.Column("subchannel", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=timestamp_default, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=timestamp_default,
            server_onupdate=timestamp_default,
            nullable=False,
        ),
        sa.UniqueConstraint("name", name="uq_orb_policy_name"),
    )
    op.create_index(
        "ix_orb_policies_module_channel",
        "orb_policies",
        ["module", "channel"],
    )

    op.create_table(
        "severity_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("module", sa.String(length=64), nullable=False, server_default=sa.text("'plus'")),
        sa.Column("submodule", sa.String(length=64), nullable=True),
        sa.Column("channel", sa.String(length=64), nullable=False, server_default=sa.text("'transits'")),
        sa.Column("subchannel", sa.String(length=64), nullable=True),
        sa.Column("weights", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("modifiers", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=timestamp_default, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=timestamp_default,
            server_onupdate=timestamp_default,
            nullable=False,
        ),
        sa.UniqueConstraint("name", name="uq_severity_profile_name"),
    )
    op.create_index(
        "ix_severity_profiles_module_channel",
        "severity_profiles",
        ["module", "channel"],
    )

    op.create_table(
        "charts",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("chart_key", sa.String(length=64), nullable=False),
        sa.Column("profile_key", sa.String(length=64), nullable=False, server_default=sa.text("'default'")),
        sa.Column(
            "kind",
            sa.Enum(
                "natal",
                "progressed",
                "solar_arc",
                "solar_return",
                "lunar_return",
                "transit",
                "custom",
                name="chart_kind_enum",
            ),
            nullable=False,
        ),
        sa.Column("dt_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("location_name", sa.String(length=128), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=128), nullable=True),
        sa.Column("module", sa.String(length=64), nullable=False, server_default=sa.text("'plus'")),
        sa.Column("submodule", sa.String(length=64), nullable=True),
        sa.Column("channel", sa.String(length=64), nullable=False, server_default=sa.text("'transits'")),
        sa.Column("subchannel", sa.String(length=64), nullable=True),
        sa.Column("data", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=timestamp_default, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=timestamp_default,
            server_onupdate=timestamp_default,
            nullable=False,
        ),
        sa.UniqueConstraint("chart_key", name="uq_charts_chart_key"),
    )
    op.create_index(
        "ix_charts_kind_module",
        "charts",
        ["kind", "module", "channel"],
    )

    op.create_table(
        "ruleset_versions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("definition_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("module", sa.String(length=64), nullable=False, server_default=sa.text("'plus'")),
        sa.Column("submodule", sa.String(length=64), nullable=True),
        sa.Column("channel", sa.String(length=64), nullable=False, server_default=sa.text("'transits'")),
        sa.Column("subchannel", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=timestamp_default, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=timestamp_default,
            server_onupdate=timestamp_default,
            nullable=False,
        ),
        sa.UniqueConstraint("key", "version", name="uq_ruleset_version"),
    )
    op.create_index(
        "ix_ruleset_versions_module_channel",
        "ruleset_versions",
        ["module", "channel"],
    )

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("event_key", sa.String(length=64), nullable=False),
        sa.Column("chart_id", sa.Integer(), nullable=False),
        sa.Column("ruleset_version_id", sa.Integer(), nullable=True),
        sa.Column("severity_profile_id", sa.Integer(), nullable=True),
        sa.Column("module", sa.String(length=64), nullable=False, server_default=sa.text("'plus'")),
        sa.Column("submodule", sa.String(length=64), nullable=True),
        sa.Column("channel", sa.String(length=64), nullable=False, server_default=sa.text("'transits'")),
        sa.Column("subchannel", sa.String(length=64), nullable=True),
        sa.Column("start_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
                "transit",
                "progression",
                "return",
                "solar_arc",
                "custom",
                name="event_type_enum",
            ),
            nullable=False,
        ),
        sa.Column("objects", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("source", sa.String(length=128), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=timestamp_default, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=timestamp_default,
            server_onupdate=timestamp_default,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["chart_id"], ["charts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ruleset_version_id"], ["ruleset_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["severity_profile_id"], ["severity_profiles.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("event_key", name="uq_events_event_key"),
    )
    op.create_index("ix_events_start_ts", "events", ["start_ts"])
    op.create_index("ix_events_chart", "events", ["chart_id"])
    op.create_index("ix_events_module_channel", "events", ["module", "channel"])

    op.create_table(
        "asteroid_meta",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("designation", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("module", sa.String(length=64), nullable=False, server_default=sa.text("'plus'")),
        sa.Column("submodule", sa.String(length=64), nullable=True),
        sa.Column("channel", sa.String(length=64), nullable=False, server_default=sa.text("'transits'")),
        sa.Column("subchannel", sa.String(length=64), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("orbit_class", sa.String(length=64), nullable=True),
        sa.Column("source_catalog", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=timestamp_default, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=timestamp_default,
            server_onupdate=timestamp_default,
            nullable=False,
        ),
        sa.UniqueConstraint("designation", name="uq_asteroid_designation"),
    )
    op.create_index(
        "ix_asteroid_meta_module_channel",
        "asteroid_meta",
        ["module", "channel"],
    )

    op.create_table(
        "export_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("job_key", sa.String(length=64), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=True),
        sa.Column("module", sa.String(length=64), nullable=False, server_default=sa.text("'plus'")),
        sa.Column("submodule", sa.String(length=64), nullable=True),
        sa.Column("channel", sa.String(length=64), nullable=False, server_default=sa.text("'transits'")),
        sa.Column("subchannel", sa.String(length=64), nullable=True),
        sa.Column(
            "export_type",
            sa.Enum("ics", "json", "csv", "webhook", name="export_type_enum"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'queued'")),
        sa.Column("params", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("result_uri", sa.String(length=255), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=timestamp_default, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=timestamp_default, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=timestamp_default,
            server_onupdate=timestamp_default,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("job_key", name="uq_export_job_key"),
    )
    op.create_index(
        "ix_export_jobs_status_requested",
        "export_jobs",
        ["status", "requested_at"],
    )
    op.create_index(
        "ix_export_jobs_module_channel",
        "export_jobs",
        ["module", "channel"],
    )


def downgrade() -> None:
    op.drop_index("ix_export_jobs_module_channel", table_name="export_jobs")
    op.drop_index("ix_export_jobs_status_requested", table_name="export_jobs")
    op.drop_table("export_jobs")

    op.drop_index("ix_asteroid_meta_module_channel", table_name="asteroid_meta")
    op.drop_table("asteroid_meta")

    op.drop_index("ix_events_module_channel", table_name="events")
    op.drop_index("ix_events_chart", table_name="events")
    op.drop_index("ix_events_start_ts", table_name="events")
    op.drop_table("events")

    op.drop_index("ix_ruleset_versions_module_channel", table_name="ruleset_versions")
    op.drop_table("ruleset_versions")

    op.drop_index("ix_charts_kind_module", table_name="charts")
    op.drop_table("charts")

    op.drop_index("ix_severity_profiles_module_channel", table_name="severity_profiles")
    op.drop_table("severity_profiles")

    op.drop_index("ix_orb_policies_module_channel", table_name="orb_policies")
    op.drop_table("orb_policies")
