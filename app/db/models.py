
"""SQLAlchemy models backing the AstroEngine Plus API."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

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
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym
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



def _uuid_hex() -> str:
    return uuid.uuid4().hex


class ChartKind(str, enum.Enum):
    """Kinds of charts supported by AstroEngine persistence."""

    natal = "natal"
    progressed = "progressed"
    solar_arc = "solar_arc"
    solar_return = "solar_return"
    lunar_return = "lunar_return"
    transit = "transit"
    custom = "custom"


class EventType(str, enum.Enum):
    """Classes of detected events tracked by the engine."""

    transit = "transit"
    progression = "progression"
    return_ = "return"
    solar_arc = "solar_arc"
    custom = "custom"


class ExportType(str, enum.Enum):
    """Supported export targets for queued jobs."""


    ics = "ics"
    json = "json"
    csv = "csv"

    webhook = "webhook"



class OrbPolicy(ModuleScopeMixin, TimestampMixin, Base):
    """Aggregate orb policy definitions exposed via the Plus API."""

    __tablename__ = "orb_policies"

    __table_args__ = (
        UniqueConstraint("name", name="uq_orb_policy_name"),
        Index("ix_orb_policies_module_channel", "module", "channel"),
    )


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

    name = synonym("profile_key")

    events: Mapped[list["Event"]] = relationship(back_populates="severity_profile")

    def __init__(self, **kwargs: Any) -> None:  # pragma: no cover - simple aliasing
        if "name" in kwargs and "profile_key" not in kwargs:
            kwargs["profile_key"] = kwargs.pop("name")
        super().__init__(**kwargs)


class ChartKind(str, Enum):
    """Enumerates supported chart categories."""

    natal = "natal"
    solar_return = "solar_return"
    lunar_return = "lunar_return"
    progressed = "progressed"
    relocated = "relocated"
    custom = "custom"


class Chart(ModuleScopeMixin, TimestampMixin, Base):
    """Natal or derived charts used to contextualize detected events."""

    __tablename__ = "charts"
    __table_args__ = (
        UniqueConstraint("chart_key", name="uq_charts_chart_key"),

        Index("ix_charts_kind_module", "kind", "module", "channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    chart_key: Mapped[str] = mapped_column(
        String(64), nullable=False, default=lambda: f"chart-{uuid4().hex}"
    )
    profile_key: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    kind: Mapped[ChartKind] = mapped_column(
        SAEnum(ChartKind, name="chart_kind"), nullable=False, default=ChartKind.natal
    )
    reference_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True, default="UTC")
    lat: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    lon: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    location_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    dt_utc = synonym("reference_time")

    events: Mapped[list["Event"]] = relationship(
        back_populates="chart", cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs: Any) -> None:  # pragma: no cover - simple aliasing
        if "dt_utc" in kwargs and "reference_time" not in kwargs:
            kwargs["reference_time"] = kwargs.pop("dt_utc")
        if "kind" in kwargs and not isinstance(kwargs["kind"], ChartKind):
            kwargs["kind"] = ChartKind(kwargs["kind"])
        super().__init__(**kwargs)


class EventType(str, Enum):
    """Supported event classifications emitted by detectors."""

    custom = "custom"
    transit = "transit"
    vocational = "vocational"
    return_event = "return"
    combust = "combust"
    cazimi = "cazimi"
    under_beams = "under_beams"
    voc_moon = "voc_moon"



class RuleSetVersion(ModuleScopeMixin, TimestampMixin, Base):
    """Versioned rulesets linking scans to reproducible logic bundles."""

    __tablename__ = "ruleset_versions"
    __table_args__ = (
        UniqueConstraint("key", "version", name="uq_ruleset_version"),
        Index("ix_ruleset_versions_module_channel", "module", "channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    ruleset_key: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    definition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )

    key = synonym("ruleset_key")
    definition_json = synonym("definition")

    events: Mapped[list["Event"]] = relationship(back_populates="ruleset_version")

    def __init__(self, **kwargs: Any) -> None:  # pragma: no cover - simple aliasing
        if "key" in kwargs and "ruleset_key" not in kwargs:
            kwargs["ruleset_key"] = kwargs.pop("key")
        if "definition_json" in kwargs and "definition" not in kwargs:
            kwargs["definition"] = kwargs.pop("definition_json")
        super().__init__(**kwargs)


class Event(ModuleScopeMixin, TimestampMixin, Base):
    """Detected events ready for downstream export and auditing."""

    __tablename__ = "events"
    __table_args__ = (

        UniqueConstraint("event_key", name="uq_events_event_key"),
        Index("ix_events_start_ts", "start_ts"),

        Index("ix_events_chart", "chart_id"),
        Index("ix_events_module_channel", "module", "channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    event_key: Mapped[str] = mapped_column(
        String(64), nullable=False, default=lambda: f"event-{uuid4().hex}"
    )
    chart_id: Mapped[int] = mapped_column(
        ForeignKey("charts.id", ondelete="CASCADE"), nullable=False
    )
    ruleset_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("ruleset_versions.id", ondelete="RESTRICT"), nullable=True

    )
    severity_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("severity_profiles.id", ondelete="SET NULL"), nullable=True
    )

    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[EventType] = mapped_column(
        SAEnum(EventType, name="event_type"), nullable=False, default=EventType.custom
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    objects: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", server_default=text("'pending'")
    )

    source: Mapped[str | None] = mapped_column(String(128), nullable=True)


    key = synonym("event_key")
    type = synonym("event_type")
    start_ts = synonym("event_time")


    chart: Mapped[Chart] = relationship(back_populates="events")
    ruleset_version: Mapped[RuleSetVersion | None] = relationship(back_populates="events")
    severity_profile: Mapped[SeverityProfile | None] = relationship(back_populates="events")
    export_jobs: Mapped[list["ExportJob"]] = relationship(back_populates="event")

    def __init__(self, **kwargs: Any) -> None:  # pragma: no cover - simple aliasing
        if "type" in kwargs and "event_type" not in kwargs:
            type_value = kwargs.pop("type")
            kwargs["event_type"] = (
                type_value
                if isinstance(type_value, EventType)
                else EventType(type_value)
            )
        if "start_ts" in kwargs and "event_time" not in kwargs:
            kwargs["event_time"] = kwargs.pop("start_ts")
        payload = kwargs.get("payload") or {}
        objects = kwargs.pop("objects", None)
        if objects is not None:
            payload = dict(payload)
            payload["objects"] = objects
        kwargs["payload"] = payload
        super().__init__(**kwargs)

    @property
    def objects(self) -> dict[str, Any] | None:
        """Return the object pairing payload if one was provided."""

        value = self.payload.get("objects")
        return value if isinstance(value, dict) else None

    @objects.setter
    def objects(self, value: dict[str, Any] | None) -> None:
        payload = dict(self.payload)
        if value is None:
            payload.pop("objects", None)
        else:
            payload["objects"] = value
        self.payload = payload


class ExportType(str, Enum):
    """Supported export payload formats."""

    ics = "ics"
    csv = "csv"
    json = "json"
    pdf = "pdf"


class AsteroidMeta(ModuleScopeMixin, TimestampMixin, Base):
    """Metadata for indexed asteroids used in scans and exports."""

    __tablename__ = "asteroid_meta"
    __table_args__ = (
        UniqueConstraint("designation", name="uq_asteroid_designation"),
        Index("ix_asteroid_meta_module_channel", "module", "channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    asteroid_id: Mapped[str] = mapped_column(
        String(32), nullable=False, default=lambda: f"asteroid-{uuid4().hex}"
    )
    designation: Mapped[str] = mapped_column(String(64), nullable=False)
    common_name: Mapped[str] = mapped_column(String(128), nullable=False)

    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    orbit_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_catalog: Mapped[str | None] = mapped_column(String(128), nullable=True)

    name = synonym("common_name")

    def __init__(self, **kwargs: Any) -> None:  # pragma: no cover - simple aliasing
        if "name" in kwargs and "common_name" not in kwargs:
            kwargs["common_name"] = kwargs.pop("name")
        super().__init__(**kwargs)


class ExportJob(ModuleScopeMixin, TimestampMixin, Base):
    """Queued export jobs referencing detected events."""

    __tablename__ = "export_jobs"
    __table_args__ = (
        Index("ix_export_jobs_status_requested", "status", "requested_at"),
        Index("ix_export_jobs_module_channel", "module", "channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    job_key: Mapped[str] = mapped_column(
        String(64), nullable=False, default=lambda: f"export-{uuid4().hex}"
    )

    event_id: Mapped[int | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL"), nullable=True
    )
    job_type: Mapped[ExportType] = mapped_column(
        SAEnum(ExportType, name="export_job_type"), nullable=False, default=ExportType.json
    )

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="queued", server_default=text("'queued'")
    )

    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    result_uri: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    key = synonym("job_key")
    type = synonym("job_type")
    params = synonym("payload")

    event: Mapped[Event | None] = relationship(back_populates="export_jobs")

    def __init__(self, **kwargs: Any) -> None:  # pragma: no cover - simple aliasing
        if "type" in kwargs and "job_type" not in kwargs:
            type_value = kwargs.pop("type")
            kwargs["job_type"] = (
                type_value
                if isinstance(type_value, ExportType)
                else ExportType(type_value)
            )
        if "params" in kwargs and "payload" not in kwargs:
            kwargs["payload"] = kwargs.pop("params")
        super().__init__(**kwargs)


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

# Backwards compatible alias retained for legacy imports
RuleSetVersion = RulesetVersion

__all__.append("RuleSetVersion")
