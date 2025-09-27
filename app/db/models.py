
"""SQLAlchemy models backing AstroEngine Plus persistence."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

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


class ChartKind(str, Enum):
    """Enumeration of supported chart archetypes."""

    natal = "natal"
    transit = "transit"
    synastry = "synastry"
    composite = "composite"


class EventType(str, Enum):
    """Enumeration of supported event types."""

    transit = "transit"
    return_ = "return"
    custom = "custom"


class ExportType(str, Enum):
    """Enumeration of supported export job types."""

    ics = "ics"
    csv = "csv"
    json = "json"



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
    """Aggregate orb policy definitions exposed via the Plus API."""

    __tablename__ = "orb_policies"
    __table_args__ = (
        UniqueConstraint("name", name="uq_orb_policy_name"),
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
        UniqueConstraint("profile_key", name="uq_severity_profile_key"),
        Index("ix_severity_profiles_module_channel", "module", "channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_key: Mapped[str] = mapped_column(String(64), nullable=False)
    weights: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    modifiers: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    events: Mapped[list["Event"]] = relationship(back_populates="severity_profile")

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401 - SQLAlchemy init shim
        """Support legacy ``name`` keyword aliasing ``profile_key``."""

        name = kwargs.pop("name", None)
        super().__init__(*args, **kwargs)
        if name is not None:
            self.profile_key = str(name)

    @property
    def name(self) -> str:
        return self.profile_key

    @name.setter
    def name(self, value: str) -> None:
        self.profile_key = value


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
    kind: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ChartKind.natal.value,
        server_default=text("'natal'"),
    )
    reference_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    events: Mapped[list["Event"]] = relationship(
        back_populates="chart", cascade="all, delete-orphan"
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401 - SQLAlchemy init shim
        """Normalize legacy keyword arguments used throughout tests."""

        dt_utc = kwargs.pop("dt_utc", None)
        kind = kwargs.pop("kind", None)
        chart_key = kwargs.pop("chart_key", None)
        profile_key = kwargs.pop("profile_key", None)
        super().__init__(*args, **kwargs)
        if dt_utc is not None:
            self.reference_time = dt_utc
        if kind is not None:
            self.kind = kind.value if isinstance(kind, ChartKind) else str(kind)
        self.chart_key = str(chart_key) if chart_key is not None else uuid4().hex
        if profile_key is not None:
            self.profile_key = str(profile_key)
        elif not getattr(self, "profile_key", None):
            self.profile_key = "default"

    @property
    def dt_utc(self) -> datetime | None:
        return self.reference_time

    @dt_utc.setter
    def dt_utc(self, value: datetime | None) -> None:
        self.reference_time = value


class RuleSetVersion(ModuleScopeMixin, TimestampMixin, Base):
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

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401 - SQLAlchemy init shim
        """Allow ``key`` to alias ``ruleset_key`` for backwards compatibility."""

        key = kwargs.pop("key", None)
        definition_json = kwargs.pop("definition_json", None)
        checksum = kwargs.pop("checksum", None)
        super().__init__(*args, **kwargs)
        if key is not None:
            self.ruleset_key = str(key)
        if definition_json is not None:
            self.definition = definition_json
        if checksum is not None:
            self.checksum = str(checksum)
        elif not getattr(self, "checksum", None):
            self.checksum = uuid4().hex

    @property
    def key(self) -> str:
        return self.ruleset_key

    @key.setter
    def key(self, value: str) -> None:
        self.ruleset_key = value


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
    ruleset_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("ruleset_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    severity_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("severity_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)

    chart: Mapped[Chart] = relationship(back_populates="events")
    ruleset_version: Mapped[RuleSetVersion | None] = relationship(back_populates="events")
    severity_profile: Mapped[SeverityProfile | None] = relationship(back_populates="events")
    export_jobs: Mapped[list["ExportJob"]] = relationship(back_populates="event")

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401 - SQLAlchemy init shim
        """Normalize legacy keyword arguments used in fixtures and tests."""

        event_key = kwargs.pop("event_key", None)
        event_type = kwargs.pop("type", None)
        start_ts = kwargs.pop("start_ts", None)
        objects = kwargs.pop("objects", None)
        super().__init__(*args, **kwargs)
        self.event_key = str(event_key or uuid4().hex)
        if event_type is not None:
            self.event_type = (
                event_type.value if isinstance(event_type, EventType) else str(event_type)
            )
        if start_ts is not None:
            self.event_time = start_ts
        if objects is not None:
            payload = dict(self.payload or {})
            payload.setdefault("objects", objects)
            self.payload = payload

    @property
    def type(self) -> EventType | str:
        try:
            return EventType(self.event_type)
        except ValueError:
            return self.event_type

    @type.setter
    def type(self, value: EventType | str) -> None:
        self.event_type = value.value if isinstance(value, EventType) else str(value)

    @property
    def start_ts(self) -> datetime:
        return self.event_time

    @start_ts.setter
    def start_ts(self, value: datetime) -> None:
        self.event_time = value


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

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401 - SQLAlchemy init shim
        """Allow legacy keyword aliases and sensible defaults."""

        name = kwargs.pop("name", None)
        designation = kwargs.get("designation")
        asteroid_id = kwargs.pop("asteroid_id", None)
        attributes = kwargs.pop("attributes", None)
        super().__init__(*args, **kwargs)
        if asteroid_id is None and designation is not None:
            self.asteroid_id = str(designation)
        elif asteroid_id is not None:
            self.asteroid_id = str(asteroid_id)
        if name is not None:
            self.common_name = str(name)
        elif not getattr(self, "common_name", None):
            self.common_name = str(designation) if designation is not None else ""
        if attributes is None and not getattr(self, "attributes", None):
            self.attributes = {}
        elif attributes is not None:
            self.attributes = dict(attributes)


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

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401 - SQLAlchemy init shim
        """Normalize legacy keyword arguments used in repositories."""

        job_type = kwargs.pop("type", None)
        params = kwargs.pop("params", None)
        job_key = kwargs.pop("job_key", None)
        super().__init__(*args, **kwargs)
        if job_type is not None:
            self.job_type = job_type.value if isinstance(job_type, ExportType) else str(job_type)
        if params is not None:
            self.payload = params
        self.job_key = str(job_key) if job_key is not None else uuid4().hex


__all__ = [
    "ChartKind",
    "EventType",
    "ExportType",
    "AsteroidMeta",
    "Chart",
    "Event",
    "ExportJob",
    "ModuleScopeMixin",
    "OrbPolicy",
    "RuleSetVersion",
    "SeverityProfile",
    "TimestampMixin",
]
