
"""SQLAlchemy models backing the AstroEngine Plus API."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
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


def _table_args(*constraints: Any, **options: Any) -> tuple[Any, ...]:
    """Ensure table declarations survive repeated imports during tests."""

    options.setdefault("extend_existing", True)
    if options:
        return (*constraints, options)
    return tuple(constraints)


def _coerce_version_value(value: Any) -> int:
    """Normalize version identifiers provided via legacy keyword args."""

    if isinstance(value, (int, float)):
        return int(value)
    try:
        text = str(value).strip()
        if not text:
            return 1
        if "." in text:
            text = text.split(".", 1)[0]
        return int(text)
    except Exception:
        return 1


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

    __table_args__ = _table_args(
        UniqueConstraint("name", name="uq_orb_policy_name"),
        Index("ix_orb_policies_module_channel", "module", "channel"),
    )


    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    per_object: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False, default=dict)
    per_aspect: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False, default=dict)
    adaptive_rules: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    def __init__(self, **kwargs: Any) -> None:
        profile_key = kwargs.pop("profile_key", None)
        body = kwargs.pop("body", None)
        aspect = kwargs.pop("aspect", None)
        orb_degrees = kwargs.pop("orb_degrees", None)

        if profile_key is not None:
            kwargs.setdefault("module", str(profile_key))

        per_object = kwargs.pop("per_object", None)
        per_aspect = kwargs.pop("per_aspect", None)

        if body is not None and orb_degrees is not None:
            per_object = {str(body): float(orb_degrees)}
        elif per_object is None:
            per_object = {}

        if aspect is not None and orb_degrees is not None:
            per_aspect = {str(aspect).lower(): float(orb_degrees)}
        elif per_aspect is None:
            per_aspect = {}

        kwargs.setdefault("adaptive_rules", {})
        kwargs["per_object"] = per_object
        kwargs["per_aspect"] = per_aspect

        if "name" not in kwargs:
            tokens = [profile_key or "policy", body or "object", aspect or "aspect"]
            kwargs["name"] = ":".join(str(token) for token in tokens)

        super().__init__(**kwargs)

        if profile_key is not None:
            self.profile_key = profile_key
        if body is not None:
            self.body = body
        if aspect is not None:
            self.aspect = aspect
        if orb_degrees is not None:
            self.orb_degrees = float(orb_degrees)


class SeverityProfile(ModuleScopeMixin, TimestampMixin, Base):
    """Severity multipliers and thresholds used during scoring."""

    __tablename__ = "severity_profiles"
    __table_args__ = _table_args(
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


    def __init__(self, **kwargs: Any) -> None:
        profile_key = kwargs.pop("profile_key", None)
        weights = kwargs.pop("weights", None)
        modifiers = kwargs.pop("modifiers", None)

        if profile_key is not None:
            kwargs.setdefault("name", str(profile_key))

        if weights is not None:
            kwargs["weights"] = weights
        else:
            kwargs.setdefault("weights", {})

        if modifiers is not None:
            kwargs["modifiers"] = modifiers

        super().__init__(**kwargs)

        if profile_key is not None:
            self.profile_key = profile_key



class Chart(ModuleScopeMixin, TimestampMixin, Base):
    """Natal or derived charts used to contextualize detected events."""

    __tablename__ = "charts"
    __table_args__ = _table_args(
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


    def __init__(self, **kwargs: Any) -> None:
        profile_key = kwargs.get("profile_key")
        if profile_key is None:
            kwargs["profile_key"] = "default"

        dt_utc = kwargs.get("dt_utc")
        if dt_utc is None:
            kwargs["dt_utc"] = datetime.now(timezone.utc)
        elif isinstance(dt_utc, datetime) and dt_utc.tzinfo is None:
            kwargs["dt_utc"] = dt_utc.replace(tzinfo=timezone.utc)

        kwargs.setdefault("kind", ChartKind.natal)
        kwargs.setdefault("lat", 0.0)
        kwargs.setdefault("lon", 0.0)

        data = kwargs.pop("data", None)
        if data is not None:
            kwargs["data"] = data
        else:
            kwargs.setdefault("data", {})

        super().__init__(**kwargs)



class RuleSetVersion(ModuleScopeMixin, TimestampMixin, Base):
    """Versioned rulesets linking scans to reproducible logic bundles."""

    __tablename__ = "ruleset_versions"
    __table_args__ = _table_args(
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


    def __init__(self, **kwargs: Any) -> None:
        ruleset_key = kwargs.pop("ruleset_key", None)
        if ruleset_key is not None:
            kwargs.setdefault("key", str(ruleset_key))

        version_value = kwargs.pop("version", None)
        if version_value is not None:
            kwargs["version"] = _coerce_version_value(version_value)
        else:
            kwargs.setdefault("version", 1)

        definition = kwargs.pop("definition", None)
        if definition is not None:
            kwargs.setdefault("definition_json", definition)

        super().__init__(**kwargs)

        if ruleset_key is not None:
            self.ruleset_key = str(ruleset_key)


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
    __table_args__ = _table_args(
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

    objects: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    score: Mapped[float | None] = mapped_column(Float, nullable=True)
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


    def __init__(self, **kwargs: Any) -> None:
        event_time = kwargs.pop("event_time", None)
        if event_time is None:
            event_time = kwargs.pop("start_ts", None)
        if event_time is None:
            event_time = datetime.now(timezone.utc)
        elif isinstance(event_time, datetime) and event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)
        kwargs.setdefault("start_ts", event_time)

        event_type = kwargs.pop("event_type", None)
        if event_type is not None:
            if isinstance(event_type, EventType):
                kwargs.setdefault("type", event_type)
            else:
                try:
                    kwargs.setdefault("type", EventType(str(event_type)))
                except Exception:
                    kwargs.setdefault("type", EventType.custom)
        elif "type" not in kwargs:
            kwargs["type"] = EventType.custom

        payload = kwargs.pop("payload", None)
        if payload is not None:
            kwargs.setdefault("payload", payload)

        objects = kwargs.pop("objects", None)
        if objects is not None:
            kwargs.setdefault("objects", objects)

        super().__init__(**kwargs)



class AsteroidMeta(ModuleScopeMixin, TimestampMixin, Base):
    """Metadata for indexed asteroids used in scans and exports."""

    __tablename__ = "asteroid_meta"
    __table_args__ = _table_args(
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


    def __init__(self, **kwargs: Any) -> None:
        asteroid_id = kwargs.pop("asteroid_id", None)
        if "designation" not in kwargs and asteroid_id is not None:
            kwargs["designation"] = str(asteroid_id)
        common_name = kwargs.pop("common_name", None)
        if "name" not in kwargs and common_name is not None:
            kwargs["name"] = common_name
        attributes = kwargs.pop("attributes", None)
        if attributes is not None:
            kwargs.setdefault("attributes", attributes)
        else:
            kwargs.setdefault("attributes", {})
        super().__init__(**kwargs)

        if common_name is not None:
            self.common_name = common_name



class ExportJob(ModuleScopeMixin, TimestampMixin, Base):
    """Queued export jobs referencing detected events."""

    __tablename__ = "export_jobs"
    __table_args__ = _table_args(
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


    def __init__(self, **kwargs: Any) -> None:
        job_type = kwargs.pop("job_type", None)
        if job_type is not None:
            if isinstance(job_type, ExportType):
                kwargs.setdefault("type", job_type)
            else:
                try:
                    kwargs.setdefault("type", ExportType(str(job_type)))
                except Exception:
                    kwargs.setdefault("type", ExportType.json)

        payload = kwargs.pop("payload", None)
        params = kwargs.pop("params", None)
        if payload is not None and params is None:
            params = payload
        if params is not None:
            kwargs.setdefault("params", params)
        else:
            kwargs.setdefault("params", {})

        resolved_type = kwargs.get("type")

        super().__init__(**kwargs)

        if resolved_type is not None:
            if isinstance(resolved_type, ExportType):
                self.job_type = resolved_type.value
            else:
                self.job_type = str(resolved_type)



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
