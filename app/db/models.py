
"""SQLAlchemy models backing AstroEngine Plus persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func


from .base import Base



class TimestampMixin:
    """Adds audited timestamps used across persisted AstroEngine records."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ModuleScopeMixin:
    """Ensures every record tracks the module/submodule/channel scope."""

    module: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="plus",
        server_default=text("'plus'"),
    )
    submodule: Mapped[str | None] = mapped_column(String(64), nullable=True)
    channel: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="transits",
        server_default=text("'transits'"),
    )
    subchannel: Mapped[str | None] = mapped_column(String(64), nullable=True)


class OrbPolicy(ModuleScopeMixin, TimestampMixin, Base):
    """Normalized orb policy entries keyed by profile, body, and aspect."""

    __tablename__ = "orb_policies"
    __table_args__ = (
        UniqueConstraint(
            "profile_key",
            "module",
            "submodule",
            "channel",
            "subchannel",
            "body",
            "aspect",
            name="uq_orb_policy_scope",
        ),
        Index("ix_orb_policies_profile_module", "profile_key", "module", "channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_key: Mapped[str] = mapped_column(String(64), nullable=False)
    body: Mapped[str] = mapped_column(String(64), nullable=False)
    aspect: Mapped[str] = mapped_column(String(64), nullable=False)
    orb_degrees: Mapped[float] = mapped_column(Float, nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class SeverityProfile(ModuleScopeMixin, TimestampMixin, Base):
    """Severity multipliers and thresholds used during scoring."""

    __tablename__ = "severity_profiles"
    __table_args__ = (
        UniqueConstraint("profile_key", name="uq_severity_profile_key"),
        Index("ix_severity_profiles_module_channel", "module", "channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_key: Mapped[str] = mapped_column(String(64), nullable=False)
    weights: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    modifiers: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    events: Mapped[list["Event"]] = relationship(back_populates="severity_profile")


class Chart(ModuleScopeMixin, TimestampMixin, Base):
    """Natal or derived charts used to contextualize detected events."""

    __tablename__ = "charts"
    __table_args__ = (
        UniqueConstraint("chart_key", name="uq_charts_chart_key"),
        Index("ix_charts_profile_module", "profile_key", "module", "channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chart_key: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_key: Mapped[str] = mapped_column(String(64), nullable=False)
    reference_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    events: Mapped[list["Event"]] = relationship(back_populates="chart", cascade="all, delete-orphan")


class RulesetVersion(ModuleScopeMixin, TimestampMixin, Base):
    """Versioned rulesets linking scans to reproducible logic bundles."""

    __tablename__ = "ruleset_versions"
    __table_args__ = (
        UniqueConstraint("ruleset_key", "version", name="uq_ruleset_version"),
        Index("ix_ruleset_versions_module_channel", "module", "channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ruleset_key: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    definition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )

    events: Mapped[list["Event"]] = relationship(back_populates="ruleset_version")


class Event(ModuleScopeMixin, TimestampMixin, Base):
    """Detected events ready for downstream export and auditing."""

    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("event_key", name="uq_events_event_key"),
        Index("ix_events_event_time", "event_time"),
        Index("ix_events_chart", "chart_id"),
        Index("ix_events_module_channel", "module", "channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_key: Mapped[str] = mapped_column(String(64), nullable=False)
    chart_id: Mapped[int] = mapped_column(ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    ruleset_version_id: Mapped[int] = mapped_column(
        ForeignKey("ruleset_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    severity_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("severity_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)

    chart: Mapped[Chart] = relationship(back_populates="events")
    ruleset_version: Mapped[RulesetVersion] = relationship(back_populates="events")
    severity_profile: Mapped[SeverityProfile | None] = relationship(back_populates="events")
    export_jobs: Mapped[list["ExportJob"]] = relationship(back_populates="event")


class AsteroidMeta(ModuleScopeMixin, TimestampMixin, Base):
    """Metadata for indexed asteroids used in scans and exports."""

    __tablename__ = "asteroid_meta"
    __table_args__ = (
        UniqueConstraint("designation", name="uq_asteroid_designation"),
        Index("ix_asteroid_meta_module_channel", "module", "channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asteroid_id: Mapped[str] = mapped_column(String(32), nullable=False)
    designation: Mapped[str] = mapped_column(String(64), nullable=False)
    common_name: Mapped[str] = mapped_column(String(128), nullable=False)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    orbit_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_catalog: Mapped[str | None] = mapped_column(String(128), nullable=True)


class ExportJob(ModuleScopeMixin, TimestampMixin, Base):
    """Queued export jobs referencing detected events."""

    __tablename__ = "export_jobs"
    __table_args__ = (
        UniqueConstraint("job_key", name="uq_export_job_key"),
        Index("ix_export_jobs_status_requested", "status", "requested_at"),
        Index("ix_export_jobs_module_channel", "module", "channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_key: Mapped[str] = mapped_column(String(64), nullable=False)
    event_id: Mapped[int | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
    )
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="queued",
        server_default=text("'queued'"),
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    result_uri: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    event: Mapped[Event | None] = relationship(back_populates="export_jobs")


__all__ = [
    "AsteroidMeta",
    "Chart",
    "Event",
    "ExportJob",
    "ModuleScopeMixin",
    "OrbPolicy",
    "RulesetVersion",
    "SeverityProfile",
    "TimestampMixin",

]

# Backwards compatible alias retained for legacy imports
RuleSetVersion = RulesetVersion

__all__.append("RuleSetVersion")
