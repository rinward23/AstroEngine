
"""SQLAlchemy models backing the AstroEngine Plus API."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

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



def _render_orb_policy_name(profile_key: str, body: str | None, aspect: str | None) -> str:
    parts = [profile_key or "default"]
    parts.append((body or "any").lower())
    parts.append((aspect or "custom").lower())
    return ":".join(parts)


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
    profile_key: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    body: Mapped[str | None] = mapped_column(String(64), nullable=True)
    aspect: Mapped[str | None] = mapped_column(String(64), nullable=True)
    orb_degrees: Mapped[float | None] = mapped_column(Float, nullable=True)

    def __init__(self, **kwargs: Any) -> None:
        profile_key = kwargs.pop("profile_key", None)
        body = kwargs.pop("body", None)
        aspect = kwargs.pop("aspect", None)
        orb_degrees = kwargs.pop("orb_degrees", None)

        per_object: Dict[str, float] = dict(kwargs.pop("per_object", {}) or {})
        per_aspect: Dict[str, float] = dict(kwargs.pop("per_aspect", {}) or {})
        adaptive_rules: Dict[str, Any] = dict(kwargs.pop("adaptive_rules", {}) or {})

        orb_value: Optional[float] = None
        if orb_degrees is not None:
            try:
                orb_value = float(orb_degrees)
            except (TypeError, ValueError):
                orb_value = None
        if orb_value is not None:
            if body:
                per_object.setdefault(str(body), orb_value)
            if aspect:
                per_aspect.setdefault(str(aspect).lower(), orb_value)

        kwargs.setdefault("name", _render_orb_policy_name(profile_key or "default", body, aspect))
        kwargs["per_object"] = per_object
        kwargs["per_aspect"] = per_aspect
        kwargs["adaptive_rules"] = adaptive_rules
        kwargs["profile_key"] = profile_key or "default"
        kwargs["body"] = body
        kwargs["aspect"] = aspect.lower() if isinstance(aspect, str) else aspect
        kwargs["orb_degrees"] = orb_value

        super().__init__(**kwargs)


class SeverityProfile(ModuleScopeMixin, TimestampMixin, Base):
    """Severity multipliers and thresholds used during scoring."""

    __tablename__ = "severity_profiles"
    __table_args__ = (
        UniqueConstraint("name", name="uq_severity_profile_name"),
        Index("ix_severity_profiles_module_channel", "module", "channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_key: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    weights: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    modifiers: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    events: Mapped[list["Event"]] = relationship(back_populates="severity_profile")

    def __init__(self, **kwargs: Any) -> None:
        profile_key = kwargs.pop("profile_key", None)
        weights = kwargs.pop("weights", None)
        if profile_key is not None:
            kwargs["profile_key"] = profile_key
        if weights is not None:
            kwargs["weights"] = weights
        kwargs.setdefault("name", f"{kwargs.get('profile_key', 'default')}_severity")
        super().__init__(**kwargs)


class Chart(ModuleScopeMixin, TimestampMixin, Base):
    """Natal or derived charts used to contextualize detected events."""

    __tablename__ = "charts"
    __table_args__ = (
        UniqueConstraint("chart_key", name="uq_charts_chart_key"),

        Index("ix_charts_kind_module", "kind", "module", "channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chart_key: Mapped[str] = mapped_column(String(64), nullable=False, default=_uuid_hex)
    profile_key: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    kind: Mapped[ChartKind] = mapped_column(
        SAEnum(ChartKind, name="chart_kind_enum"),
        nullable=False,
    )

    dt_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    location_name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


    events: Mapped[list["Event"]] = relationship(
        back_populates="chart",
        cascade="all, delete-orphan",
    )

    def __init__(self, **kwargs: Any) -> None:
        profile_key = kwargs.pop("profile_key", None)
        if profile_key is not None:
            kwargs["profile_key"] = profile_key
        data = kwargs.pop("data", None)
        if data is not None:
            kwargs["data"] = data
            if "kind" not in kwargs and isinstance(data, dict):
                kind_value = data.get("kind")
                if isinstance(kind_value, str):
                    try:
                        kwargs["kind"] = ChartKind(kind_value)
                    except ValueError:
                        try:
                            kwargs["kind"] = ChartKind[kind_value]
                        except Exception:
                            kwargs["kind"] = ChartKind.custom
        if "kind" not in kwargs:
            kwargs["kind"] = ChartKind.custom
        if "dt_utc" not in kwargs or kwargs["dt_utc"] is None:
            kwargs["dt_utc"] = datetime.now(timezone.utc)
        kwargs.setdefault("lat", 0.0)
        kwargs.setdefault("lon", 0.0)
        super().__init__(**kwargs)


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

    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)

    definition_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )

    events: Mapped[list["Event"]] = relationship(back_populates="ruleset_version")

    def __init__(self, **kwargs: Any) -> None:
        ruleset_key = kwargs.pop("ruleset_key", None)
        definition = kwargs.pop("definition", None)
        if ruleset_key is not None and "key" not in kwargs:
            kwargs["key"] = str(ruleset_key)
        if definition is not None and "definition_json" not in kwargs:
            kwargs["definition_json"] = definition
        version_value = kwargs.get("version")
        if isinstance(version_value, str):
            try:
                kwargs["version"] = int(float(version_value))
            except ValueError:
                pass
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

    event_key: Mapped[str] = mapped_column(String(64), nullable=False, default=_uuid_hex)

    chart_id: Mapped[int] = mapped_column(ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    ruleset_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("ruleset_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    severity_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("severity_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )

    start_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    type: Mapped[EventType] = mapped_column(
        "event_type",
        SAEnum(EventType, name="event_type_enum"),
        nullable=False,
    )
    objects: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )

    source: Mapped[str | None] = mapped_column(String(128), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    chart: Mapped[Chart] = relationship(back_populates="events")
    ruleset_version: Mapped[RuleSetVersion | None] = relationship(back_populates="events")
    severity_profile: Mapped[SeverityProfile | None] = relationship(back_populates="events")
    export_jobs: Mapped[list["ExportJob"]] = relationship(back_populates="event")

    def __init__(self, **kwargs: Any) -> None:
        event_time = kwargs.pop("event_time", None)
        if event_time is not None and "start_ts" not in kwargs:
            kwargs["start_ts"] = event_time
        event_type = kwargs.pop("event_type", None)
        if event_type is not None and "type" not in kwargs:
            if isinstance(event_type, EventType):
                kwargs["type"] = event_type
            else:
                try:
                    kwargs["type"] = EventType(event_type)
                except ValueError:
                    try:
                        kwargs["type"] = EventType[event_type]
                    except Exception:
                        kwargs["type"] = EventType.custom
        if "objects" not in kwargs:
            payload = kwargs.get("payload")
            if isinstance(payload, dict) and "objects" in payload:
                kwargs["objects"] = payload["objects"]
        kwargs.setdefault("objects", {})
        super().__init__(**kwargs)


class AsteroidMeta(ModuleScopeMixin, TimestampMixin, Base):
    """Metadata for indexed asteroids used in scans and exports."""

    __tablename__ = "asteroid_meta"
    __table_args__ = (
        UniqueConstraint("designation", name="uq_asteroid_designation"),
        Index("ix_asteroid_meta_module_channel", "module", "channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)


    designation: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    orbit_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_catalog: Mapped[str | None] = mapped_column(String(128), nullable=True)

    def __init__(self, **kwargs: Any) -> None:
        asteroid_id = kwargs.pop("asteroid_id", None)
        common_name = kwargs.pop("common_name", None)
        if asteroid_id is not None and "designation" not in kwargs:
            kwargs["designation"] = str(asteroid_id)
        if common_name is not None and "name" not in kwargs:
            kwargs["name"] = str(common_name)
        super().__init__(**kwargs)

    @property
    def common_name(self) -> str | None:
        return self.name

    @common_name.setter
    def common_name(self, value: str | None) -> None:
        self.name = value if value is not None else self.name


class ExportJob(ModuleScopeMixin, TimestampMixin, Base):
    """Queued export jobs referencing detected events."""

    __tablename__ = "export_jobs"
    __table_args__ = (
        Index("ix_export_jobs_status_requested", "status", "requested_at"),
        Index("ix_export_jobs_module_channel", "module", "channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    job_key: Mapped[str] = mapped_column(String(64), nullable=False, default=_uuid_hex)

    event_id: Mapped[int | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
    )

    type: Mapped[ExportType] = mapped_column(
        "export_type",
        SAEnum(ExportType, name="export_type_enum"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="queued",
        server_default=text("'queued'"),
    )
    params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    result_uri: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    event: Mapped[Event | None] = relationship(back_populates="export_jobs")

    def __init__(self, **kwargs: Any) -> None:
        job_type = kwargs.pop("job_type", None)
        if job_type is not None and "type" not in kwargs:
            if isinstance(job_type, ExportType):
                kwargs["type"] = job_type
            else:
                try:
                    kwargs["type"] = ExportType(job_type)
                except ValueError:
                    try:
                        kwargs["type"] = ExportType[job_type]
                    except Exception:
                        kwargs["type"] = ExportType.json
        payload = kwargs.pop("payload", None)
        if payload is not None and "params" not in kwargs:
            kwargs["params"] = payload
        super().__init__(**kwargs)

    @property
    def job_type(self) -> str:
        return self.type.value

    @job_type.setter
    def job_type(self, value: str) -> None:
        self.type = ExportType(value)

    @property
    def payload(self) -> dict[str, Any]:
        return self.params

    @payload.setter
    def payload(self, value: dict[str, Any]) -> None:
        self.params = value


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
RulesetVersion = RuleSetVersion

__all__.append("RulesetVersion")
