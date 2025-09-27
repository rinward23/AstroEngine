"""SQLAlchemy models backing the AstroEngine Plus API test harness."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
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


def _uuid_hex() -> str:
    """Generate random hexadecimal identifiers for primary keys."""

    return uuid.uuid4().hex


class TimestampMixin:
    """Adds creation and update timestamps to persisted records."""

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
    """Record the module → channel scope associated with stored entities."""

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
    """Orb widths for aspects; supports both legacy and modern schemas."""

    __tablename__ = "orb_policies"
    __table_args__ = (
        UniqueConstraint(
            "profile_key", "body", "aspect", name="uq_orb_policy_legacy"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Legacy columns exercised directly in tests
    profile_key: Mapped[str] = mapped_column(
        String(64), nullable=False, default="default"
    )
    body: Mapped[str | None] = mapped_column(String(64), nullable=True)
    aspect: Mapped[str | None] = mapped_column(String(64), nullable=True)
    orb_degrees: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Rich policy definition used by the Plus API
    name: Mapped[str | None] = mapped_column(String(80), nullable=True, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    per_object: Mapped[dict[str, float]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    per_aspect: Mapped[dict[str, float]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    adaptive_rules: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )


class SeverityProfile(ModuleScopeMixin, TimestampMixin, Base):
    """Store severity weights used during scoring routines."""

    __tablename__ = "severity_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_key: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    weights: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    modifiers: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    events: Mapped[list["Event"]] = relationship(back_populates="severity_profile")


class Chart(ModuleScopeMixin, TimestampMixin, Base):
    """Persisted chart metadata plus arbitrary serialized payloads."""

    __tablename__ = "charts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chart_key: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, default=_uuid_hex
    )
    profile_key: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    dt_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    events: Mapped[list["Event"]] = relationship(
        back_populates="chart",
        cascade="all, delete-orphan",
    )


class RulesetVersion(ModuleScopeMixin, TimestampMixin, Base):
    """Versioned rule bundles consumed by scans and exports."""

    __tablename__ = "ruleset_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ruleset_key: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    definition: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )

    events: Mapped[list["Event"]] = relationship(back_populates="ruleset_version")


class Event(ModuleScopeMixin, TimestampMixin, Base):
    """Detected events referencing source charts and rulesets."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_key: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, default=_uuid_hex
    )
    chart_id: Mapped[int] = mapped_column(
        ForeignKey("charts.id", ondelete="CASCADE"), nullable=False
    )
    ruleset_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("ruleset_versions.id", ondelete="SET NULL"), nullable=True
    )
    severity_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("severity_profiles.id", ondelete="SET NULL"), nullable=True
    )

    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    objects: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    chart: Mapped[Chart] = relationship(back_populates="events")
    ruleset_version: Mapped[RulesetVersion | None] = relationship(
        back_populates="events"
    )
    severity_profile: Mapped[SeverityProfile | None] = relationship(
        back_populates="events"
    )
    export_jobs: Mapped[list["ExportJob"]] = relationship(back_populates="event")


class AsteroidMeta(ModuleScopeMixin, TimestampMixin, Base):
    """Auxiliary metadata for asteroid lookups."""

    __tablename__ = "asteroid_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asteroid_id: Mapped[str] = mapped_column(String(64), nullable=False)
    designation: Mapped[str] = mapped_column(String(64), nullable=False)
    common_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    orbit_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_catalog: Mapped[str | None] = mapped_column(String(128), nullable=True)


class ExportJob(ModuleScopeMixin, TimestampMixin, Base):
    """Queued exports for downstream delivery."""

    __tablename__ = "export_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_key: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, default=_uuid_hex
    )
    event_id: Mapped[int | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL"), nullable=True
    )
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="queued",
        server_default=text("'queued'"),
    )
    result_uri: Mapped[str | None] = mapped_column(String(255), nullable=True)
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
    "Event",
    "ExportJob",
    "ModuleScopeMixin",
    "OrbPolicy",
    "RulesetVersion",
    "SeverityProfile",
    "TimestampMixin",
]

# Backwards compatible alias retained for older imports
RuleSetVersion = RulesetVersion
__all__.append("RuleSetVersion")

