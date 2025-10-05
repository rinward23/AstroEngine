"""Add scope and timestamp indexes for high-cardinality filters."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine.reflection import Inspector


def _events_time_column(inspector: Inspector) -> str:
    columns = {column["name"] for column in inspector.get_columns("events")}
    return "event_time" if "event_time" in columns else "start_ts"


def _index_exists(inspector: Inspector, table: str, name: str) -> bool:
    return any(index["name"] == name for index in inspector.get_indexes(table))


def _unique_constraint_exists(inspector: Inspector, table: str, name: str) -> bool:
    return any(constraint["name"] == name for constraint in inspector.get_unique_constraints(table))


revision = "20241115_0003"
down_revision = "20241108_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    op.create_index(
        "ix_orb_policies_scope_full",
        "orb_policies",
        ["module", "submodule", "channel", "subchannel"],
    )
    op.create_index("ix_orb_policies_created_at", "orb_policies", ["created_at"])
    with op.batch_alter_table("orb_policies", schema=None) as batch:
        batch.create_unique_constraint(
            "uq_orb_policies_scope_name",
            ["module", "submodule", "channel", "subchannel", "name"],
        )

    op.create_index(
        "ix_severity_profiles_scope_full",
        "severity_profiles",
        ["module", "submodule", "channel", "subchannel"],
    )
    op.create_index(
        "ix_severity_profiles_created_at",
        "severity_profiles",
        ["created_at"],
    )

    op.create_index(
        "ix_traditional_runs_scope_full",
        "traditional_runs",
        ["module", "submodule", "channel", "subchannel"],
    )
    op.create_index(
        "ix_traditional_runs_created_at",
        "traditional_runs",
        ["created_at"],
    )
    with op.batch_alter_table("traditional_runs", schema=None) as batch:
        batch.create_unique_constraint(
            "uq_traditional_runs_scope_run_id",
            ["module", "submodule", "channel", "subchannel", "run_id"],
        )

    op.create_index(
        "ix_charts_scope_full",
        "charts",
        ["module", "submodule", "channel", "subchannel"],
    )
    op.create_index("ix_charts_dt_utc", "charts", ["dt_utc"])
    op.create_index("ix_charts_created_at", "charts", ["created_at"])
    with op.batch_alter_table("charts", schema=None) as batch:
        batch.create_unique_constraint(
            "uq_charts_scope_key",
            ["module", "submodule", "channel", "subchannel", "chart_key"],
        )

    op.create_index(
        "ix_ruleset_versions_scope_full",
        "ruleset_versions",
        ["module", "submodule", "channel", "subchannel"],
    )
    op.create_index(
        "ix_ruleset_versions_created_at",
        "ruleset_versions",
        ["created_at"],
    )
    with op.batch_alter_table("ruleset_versions", schema=None) as batch:
        batch.create_unique_constraint(
            "uq_ruleset_versions_scope_key_version",
            ["module", "submodule", "channel", "subchannel", "ruleset_key", "version"],
        )

    event_time_column = _events_time_column(inspector)
    op.create_index(
        "ix_events_scope_full",
        "events",
        ["module", "submodule", "channel", "subchannel"],
    )
    op.create_index(
        "ix_events_event_time_scope",
        "events",
        [event_time_column, "module", "channel"],
    )
    op.create_index("ix_events_created_at", "events", ["created_at"])
    with op.batch_alter_table("events", schema=None) as batch:
        batch.create_unique_constraint(
            "uq_events_scope_key",
            ["module", "submodule", "channel", "subchannel", "event_key"],
        )

    op.create_index(
        "ix_asteroid_meta_scope_full",
        "asteroid_meta",
        ["module", "submodule", "channel", "subchannel"],
    )
    op.create_index(
        "ix_asteroid_meta_created_at",
        "asteroid_meta",
        ["created_at"],
    )
    with op.batch_alter_table("asteroid_meta", schema=None) as batch:
        batch.create_unique_constraint(
            "uq_asteroid_meta_scope_designation",
            ["module", "submodule", "channel", "subchannel", "designation"],
        )

    op.create_index(
        "ix_export_jobs_scope_full",
        "export_jobs",
        ["module", "submodule", "channel", "subchannel"],
    )
    op.create_index(
        "ix_export_jobs_requested_at",
        "export_jobs",
        ["requested_at"],
    )
    op.create_index(
        "ix_export_jobs_completed_at",
        "export_jobs",
        ["completed_at"],
    )
    with op.batch_alter_table("export_jobs", schema=None) as batch:
        batch.create_unique_constraint(
            "uq_export_jobs_scope_key",
            ["module", "submodule", "channel", "subchannel", "job_key"],
        )


def downgrade() -> None:
    with op.batch_alter_table("export_jobs", schema=None) as batch:
        batch.drop_constraint("uq_export_jobs_scope_key", type_="unique")
    op.drop_index("ix_export_jobs_completed_at", table_name="export_jobs")
    op.drop_index("ix_export_jobs_requested_at", table_name="export_jobs")
    op.drop_index("ix_export_jobs_scope_full", table_name="export_jobs")

    with op.batch_alter_table("asteroid_meta", schema=None) as batch:
        batch.drop_constraint("uq_asteroid_meta_scope_designation", type_="unique")
    op.drop_index("ix_asteroid_meta_created_at", table_name="asteroid_meta")
    op.drop_index("ix_asteroid_meta_scope_full", table_name="asteroid_meta")

    with op.batch_alter_table("events", schema=None) as batch:
        batch.drop_constraint("uq_events_scope_key", type_="unique")
    op.drop_index("ix_events_created_at", table_name="events")
    op.drop_index("ix_events_event_time_scope", table_name="events")
    op.drop_index("ix_events_scope_full", table_name="events")

    with op.batch_alter_table("ruleset_versions", schema=None) as batch:
        batch.drop_constraint(
            "uq_ruleset_versions_scope_key_version",
            type_="unique",
        )
    op.drop_index("ix_ruleset_versions_created_at", table_name="ruleset_versions")
    op.drop_index("ix_ruleset_versions_scope_full", table_name="ruleset_versions")

    with op.batch_alter_table("charts", schema=None) as batch:
        batch.drop_constraint("uq_charts_scope_key", type_="unique")
    op.drop_index("ix_charts_created_at", table_name="charts")
    op.drop_index("ix_charts_dt_utc", table_name="charts")
    op.drop_index("ix_charts_scope_full", table_name="charts")

    with op.batch_alter_table("traditional_runs", schema=None) as batch:
        batch.drop_constraint(
            "uq_traditional_runs_scope_run_id",
            type_="unique",
        )
    op.drop_index("ix_traditional_runs_created_at", table_name="traditional_runs")
    op.drop_index("ix_traditional_runs_scope_full", table_name="traditional_runs")

    op.drop_index("ix_severity_profiles_created_at", table_name="severity_profiles")
    op.drop_index("ix_severity_profiles_scope_full", table_name="severity_profiles")

    with op.batch_alter_table("orb_policies", schema=None) as batch:
        batch.drop_constraint("uq_orb_policies_scope_name", type_="unique")
    op.drop_index("ix_orb_policies_created_at", table_name="orb_policies")
    op.drop_index("ix_orb_policies_scope_full", table_name="orb_policies")
