
"""SQLAlchemy models backing the AstroEngine Plus API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
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


class ChartKind(str, Enum):
    """Supported chart archetypes."""

    natal = "natal"
    transit = "transit"
    progressed = "progressed"
    solar_return = "solar_return"
    composite = "composite"


class EventType(str, Enum):
    """High level categories for scored events."""

    custom = "custom"
    transit = "transit"
    ingress = "ingress"
    progression = "progression"
    return_chart = "return_chart"


class ExportType(str, Enum):
    """Enumerates the export targets supported by Plus."""

    ics = "ics"
    json = "json"
    csv = "csv"
    api = "api"


class OrbPolicy(ModuleScopeMixin, TimestampMixin, Base):
    """Aggregate orb policy definitions exposed via the Plus API."""

    __tablename__ = "orb_policies"
    __table_args__ = (UniqueConstraint("name", name="uq_orb_policy_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    per_object: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False, default=dict)
    per_aspect: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False, default=dict)
    adaptive_rules: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class SeverityProfile(ModuleScopeMixin, TimestampMixin, Base):
    """Severity multipliers and thresholds used during scoring."""

    __tablename__ = "severity_profiles"
    __table_args__ = (
        UniqueConstraint("name", name="uq_severity_profile_name"),
        Index("ix_severity_profiles_module_channel", "module", "channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    weights: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    modifiers: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    events: Mapped[list["Event"]] = relationship(back_populates="severity_profile")


class Chart(ModuleScopeMixin, TimestampMixin, Base):
    """Natal or derived charts used to contextualize detected events."""

    __tablename__ = "charts"
    __table_args__ = (
        UniqueConstraint("chart_key", name="uq_charts_chart_key"),
        Index("ix_charts_module_channel", "module", "channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chart_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kind: Mapped[ChartKind] = mapped_column(SAEnum(ChartKind), nullable=False, default=ChartKind.natal)
    dt_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    location_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    location_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    events: Mapped[list["Event"]] = relationship(
        back_populates="chart",
        cascade="all, delete-orphan",
    )


class RuleSetVersion(ModuleScopeMixin, TimestampMixin, Base):
    """Versioned rulesets linking scans to reproducible logic bundles."""

    __tablename__ = "ruleset_versions"
    __table_args__ = (
        UniqueConstraint("key", "version", name="uq_ruleset_version"),
        Index("ix_ruleset_versions_module_channel", "module", "channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    definition_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
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
        Index("ix_events_start", "start_ts"),
        Index("ix_events_chart", "chart_id"),
        Index("ix_events_module_channel", "module", "channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chart_id: Mapped[int] = mapped_column(ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    ruleset_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("ruleset_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    severity_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("severity_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    type: Mapped[EventType] = mapped_column(SAEnum(EventType), nullable=False, default=EventType.custom)
    start_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    objects: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    chart: Mapped[Chart] = relationship(back_populates="events")
    ruleset_version: Mapped[RuleSetVersion | None] = relationship(back_populates="events")
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
    asteroid_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    designation: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    orbit_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_catalog: Mapped[str | None] = mapped_column(String(128), nullable=True)


class ExportJob(ModuleScopeMixin, TimestampMixin, Base):
    """Queued export jobs referencing detected events."""

    __tablename__ = "export_jobs"
    __table_args__ = (
        Index("ix_export_jobs_status_requested", "status", "requested_at"),
        Index("ix_export_jobs_module_channel", "module", "channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[int | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
    )
    type: Mapped[ExportType] = mapped_column(SAEnum(ExportType), nullable=False, default=ExportType.json)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="queued",
        server_default=text("'queued'"),
    )
    params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    result_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    event: Mapped[Event | None] = relationship(back_populates="export_jobs")


__all__ = [
    "AsteroidMeta",
    "Chart",
    "ChartKind",
    "Event",
    "EventType",
    "ExportJob",
    "ExportType",
    "ModuleScopeMixin",
    "OrbPolicy",
    "RuleSetVersion",
    "SeverityProfile",
    "TimestampMixin",
]
